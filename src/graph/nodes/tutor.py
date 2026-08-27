"""Tutor node — generates science answers with curriculum grounding."""

# ruff: noqa: E501

import re

from src.agents.tutor.tutor import TutorSynthesisAgent
from src.core.memory.truncation import truncate_messages
from src.graph.state import AgentState
from src.llm.router import ModelRouter
from src.schemas.common import SUBJECT_LABELS, SUBJECT_LABELS_AM
from src.schemas.streaming import TokenChunk


def _graceful_no_content_message(state: AgentState) -> str:
    """Friendly message shown when a subject has no curriculum content yet.

    Used for Chemistry/Physics/Mathematics (not yet ingested) and for Grades
    7-8 where the biology PDFs don't exist, so the tutor never silently
    falls back to another subject or hallucinates.
    """
    subject = state.subject or ""
    if subject:
        if state.language == "am":
            subject_label = SUBJECT_LABELS_AM.get(subject, subject.capitalize())
        else:
            subject_label = SUBJECT_LABELS.get(subject, subject.capitalize())
    else:
        subject_label = "ይህ ምድብ" if state.language == "am" else "this subject"
    grade = state.grade_level or ""
    grade_label = f" Grade {grade}" if grade else ""

    if state.language == "am":
        return (
            f"የ{subject_label}{grade_label} ይዘት አሁን እያዘጋጃለን ነው። ለአሁኑ ጊዜ ባዮሎጂን ይሞክሩ — ከሁሉም የበለጠ እቃዎች ያሉት ነው። "
            "ከጥያቄዎ ላይ በመስራት የመርገጫ አይነት ከኋላ ማለያው ላይ በመቀየር ሌላ አማራጭ መምረጥ ይችላሉ።"
        )
    if state.language == "both":
        subject_label_am = (
            SUBJECT_LABELS_AM.get(subject, subject.capitalize()) if subject else "ይህ ምድብ"
        )
        return (
            f"We're still adding {subject_label}{grade_label} content. የ{subject_label_am} ይዘት "
            "አሁን እያዘጋጃለን ነው። In the meantime, try Biology — it has the most material available. "
            "You can switch subjects using the subject selector above."
        )
    return (
        f"We're still adding {subject_label}{grade_label} content. In the meantime, try "
        "Biology — it has the most material available. You can switch subjects using the "
        "subject selector above."
    )


MISCONCEPTION_INDICATORS = [
    "that's not quite right",
    "that's not correct",
    "that is incorrect",
    "i see a misconception",
    "common misconception",
    "you're confusing",
    "you are confusing",
    "that's a misunderstanding",
    "there's a misunderstanding",
    "this is a common error",
    "a common mistake",
    "this is incorrect",
    "that is wrong",
    "that's wrong",
    "not accurate",
    "this isn't correct",
    "that isn't correct",
    "i think there's a misunderstanding",
    "i think there is a misunderstanding",
]


def _detect_misconception(response_text: str) -> tuple[bool, str]:
    response_lower = response_text.lower()
    for indicator in MISCONCEPTION_INDICATORS:
        if indicator in response_lower:
            sentences = re.split(r"(?<=[.!?])\s+", response_text)
            for i, sentence in enumerate(sentences):
                if indicator in sentence.lower():
                    correction = sentence.strip()
                    if i + 1 < len(sentences):
                        correction += " " + sentences[i + 1].strip()
                    if len(correction) > 300:
                        correction = correction[:297] + "..."
                    return True, correction
    return False, ""


SYSTEM_PROMPT = """You are EthioSci Tutor, an AI science tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is in English. Follow language instructions provided in the user message.

Rules:
1. Use the curriculum context provided below as your PRIMARY source. If it contains
   the information, ground EVERY claim in it.
2. Adapt explanations to the student's grade level.
3. Ground EVERY claim in the provided context. If no supporting context exists for a claim, do NOT make it.
4. Keep explanations clear, simple, and focused.
5. If you're unsure, say so clearly rather than guessing.
6. VERBATIM QUOTES: For EVERY key claim, include a DIRECT QUOTE from the curriculum
   context that supports it. Format:
   → "verbatim quote from textbook" (Grade X, Unit Y: Title, Section N.N: Name, p. Z)
   Example: "Carbohydrates are made of carbon, hydrogen, and oxygen" (Grade 10,
   Unit 3: Biochemical Molecules, Section 3.1: Carbohydrates, p. 77)
7. NEGATIVE RULE: Never invent quotes or citations. If you cannot find a direct quote
   supporting a claim in the curriculum context, do NOT present the claim as
   curriculum material — answer from general science knowledge instead, and clearly
   mark such content with "General knowledge:".
8. If the curriculum context does not contain enough information to fully answer the
   question, answer from general science knowledge marked "General knowledge:" —
   never refuse to answer, never invent citations. You may add one short line noting
   that the topic is not in the provided curriculum.
9. If the student's question or reasoning contains a conceptual error, gently point it
   out and explain why it is incorrect before providing the correct information.
   Be supportive — never condescending."""

SOCRATIC_SYSTEM_PROMPT = """You are EthioSci Tutor in Socratic Mode, an AI science tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is in English. Follow language instructions provided in the user message.

STRUCTURED RESPONSE FORMAT:
When a student asks a science question, your response MUST contain at least one guiding question. Follow this structure:
1. ACKNOWLEDGE — Briefly affirm the question (1 sentence).
2. GUIDE — Ask 1-2 probing questions that help the student reason toward the answer themselves.
3. PROMPT — End by inviting the student to share their thinking.

Rules:
1. DO NOT give direct answers. Ask guiding questions that help the student discover the answer themselves.
2. Adapt questions to the student's grade level.
3. Use the curriculum context as your primary source; if it lacks the information,
   guide the student using general science knowledge (do not present it as
   curriculum material).
4. Keep responses brief and focused on the next guiding question.
5. Praise correct reasoning and gently redirect incorrect assumptions.
6. If you must state a factual claim in your guiding question, support it with a
   DIRECT QUOTE from the curriculum. Format:
   "verbatim quote" (Grade X, Unit Y: Title, Section N.N: Name, p. Z)
7. NEGATIVE RULE: If you cannot find a direct quote supporting a claim, do NOT present
   it as curriculum material — rephrase as a question or label it "General knowledge:".
8. If the student is stuck after several exchanges, you may provide a hint to keep them moving.
9. Always encourage the student to think step by step.
10. If the student's response contains a conceptual error, gently correct them by explaining why their reasoning is incorrect, then continue with a guiding question. Be supportive — never condescending."""

HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer. Frame it as a guiding thought or a nudge toward the correct concept.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly. Point toward the relevant process, structure, or principle involved.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer. You may describe the key mechanism or cite the relevant curriculum section, but let the student articulate the final conclusion.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Include verbatim quotes from the [Source X] blocks. Only cite sources from the [Source X] blocks provided above — NEVER invent citations."


class TutorNode:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.agent = TutorSynthesisAgent(router)

    async def __call__(self, state: AgentState) -> AgentState:
        if state.no_content_for_subject:
            state.draft = _graceful_no_content_message(state)
            state.confidence = 1.0
            return state
        if state.evidence_items and state.token_queue is None:
            return await self._agentic_call(state)
        return await self._legacy_call(state)

    async def _legacy_call(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang = state.language
        if lang == "am":
            lang_context = (
                "Respond entirely in Amharic (አማርኛ). "
                "Use Amharic science terminology. "
                "Never mix English unless quoting a technical term or scientific name. "
                "Always provide the Amharic equivalent of key terms."
            )
        elif lang == "both":
            lang_context = "Answer in English with Amharic explanation. Provide key terms in both English and Amharic."
        else:
            lang_context = "Answer in English."

        if state.reveal_answer:
            system = SYSTEM_PROMPT
        elif state.socratic_mode:
            system = SOCRATIC_SYSTEM_PROMPT
        else:
            system = SYSTEM_PROMPT

        if state.learner_profile_block and state.use_learner_awareness:
            system += "\n\n" + state.learner_profile_block

        memory_block = ""
        if state.memory_context:
            memory_block = "\n\n" + state.memory_context
        elif state.socratic_mode and state.socratic_stage:
            memory_block = "\n\n## Learner Context\n"
            memory_block += f"- Socratic Stage: {state.socratic_stage}\n"
            if state.socratic_focus:
                memory_block += f"- Current Focus: {state.socratic_focus}\n"
            if state.socratic_understanding:
                memory_block += f"- Student Understanding: {state.socratic_understanding}\n"
            if state.socratic_next_question:
                memory_block += f"- Previous Guiding Question: {state.socratic_next_question}\n"

        if memory_block:
            system += memory_block

        if state.reveal_answer:
            system += REVEAL_PROMPT
        elif state.hint_level > 0 and state.hint_level in HINT_PROMPTS:
            system += HINT_PROMPTS[state.hint_level]
        if state.evidence_synthesis:
            system += f"\n\n## Evidence Synthesis\n{state.evidence_synthesis}\n\nUse the above evidence synthesis to ground your answer. "
            system += "Include verbatim quotes from the [Source X] headers. Cite as (Grade X, Unit Y: Title, Section N.N: Name, p. Z)."
        if state.context:
            system += f"\n\n## Curriculum Context\n{state.context}\n\nUse the above context to ground your answer. "
            system += "Include verbatim quotes from the [Source X] blocks. Cite as (Grade X, Unit Y: Title, Section N.N: Name, p. Z)."
        elif state.retrieved_chunks:
            ctx_lines = []
            for i, chunk in enumerate(state.retrieved_chunks):
                meta = chunk.get("metadata", {})
                grade = meta.get("grade_level", "")
                unit = meta.get("unit", "")
                section = meta.get("section", "")
                subtopic = meta.get("subtopic", "")
                page = meta.get("page_number", 0)
                hdr = f"[Source {i}]"
                if grade:
                    subject_label = meta.get("subject", "")
                    hdr += (
                        f" Grade {grade} {subject_label.title()}"
                        if subject_label
                        else f" Grade {grade}"
                    )
                if unit:
                    hdr += f" | {unit}"
                if section:
                    hdr += f" | {section}"
                if subtopic:
                    hdr += f" | {subtopic}"
                if page:
                    hdr += f" | p.{page}"
                ctx_lines.append(f"{hdr}\n{chunk.get('content', '')}")
            ctx_str = "\n\n".join(ctx_lines)
            system += f"\n\n## Curriculum Context\n{ctx_str}\n\nUse the above context to ground your answer. "
            system += "Include verbatim quotes from the [Source N] blocks. Cite as (Grade X, Unit Y: Title, Section N.N: Name, p. Z)."

        if state.ungrounded_claims:
            system += "\n\n## Revision Feedback\n"
            system += "Your previous response contained claims that could not be verified against the provided evidence. "
            system += "Please revise the response to fix the following ungrounded claims:\n"
            for i, claim in enumerate(state.ungrounded_claims, 1):
                system += f'\n{i}. "{claim}"'
            system += "\n\nEnsure EVERY claim in your response is directly supported by the provided evidence. "
            system += "Remove or rephrase any claim you cannot support with a verbatim quote from the curriculum context."

        user_message = (
            f"[Grade{grade_context}] {lang_context}\n\nStudent question: {state.user_message}"
        )

        history = truncate_messages(state.messages, budget=3000)
        messages = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": user_message},
        ]

        if state.token_queue is not None:
            content = ""
            queue = state.token_queue
            async for token in self.router.route_stream(
                messages,
                request_type="tutor",
                temperature=0.7,
                max_tokens=2048,
            ):
                queue.put_nowait(TokenChunk(delta=token, node="tutor"))
                content += token
            queue.put_nowait(TokenChunk(delta="", node="tutor", done=True))
        else:
            result = await self.router.route(
                messages, request_type="tutor", temperature=0.7, max_tokens=2048
            )
            content = result["content"]
            state.model_used = result.get("model", "")
            state.confidence = result.get("confidence", 0.0)

        state.draft = content
        if not state.model_used:
            state.model_used = f"stream/{state.model_used or 'tutor'}"

        detected, correction = _detect_misconception(content)
        state.misconception_detected = detected
        state.misconception_correction = correction

        return state

    async def _agentic_call(self, state: AgentState) -> AgentState:
        student_misconceptions = []
        if state.misconception_correction:
            student_misconceptions = [state.misconception_correction]

        response = await self.agent.generate(
            user_message=state.user_message,
            evidence_items=state.evidence_items,
            evidence_synthesis=state.evidence_synthesis,
            grade_level=state.grade_level,
            language=state.language,
            socratic_mode=state.socratic_mode,
            hint_level=state.hint_level,
            reveal_answer=state.reveal_answer,
            learner_profile_block=state.learner_profile_block or "",
            messages=state.messages,
            intent=state.intent,
            misconception_detected=state.misconception_detected,
            student_misconceptions=student_misconceptions,
            ungrounded_claims=state.ungrounded_claims,
        )

        state.draft = response.content
        state.grounded_response = response.content
        state.confidence = response.confidence
        state.teaching_strategy = response.teaching_strategy.value
        state.citation_map = [e.model_dump() for e in response.citation_map]
        state.recommendations = response.recommendations
        state.misconception_correction = (
            ", ".join(response.misconceptions_addressed)
            if response.misconceptions_addressed
            else state.misconception_correction
        )

        return state
