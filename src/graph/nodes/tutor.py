"""Tutor node — generates biology answers with curriculum grounding."""

import re

from src.graph.state import AgentState
from src.llm.router import ModelRouter

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
            sentences = re.split(r'(?<=[.!?])\s+', response_text)
            for i, sentence in enumerate(sentences):
                if indicator in sentence.lower():
                    correction = sentence.strip()
                    if i + 1 < len(sentences):
                        correction += " " + sentences[i + 1].strip()
                    if len(correction) > 300:
                        correction = correction[:297] + "..."
                    return True, correction
    return False, ""

SYSTEM_PROMPT = """You are EthioBio Tutor, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is English-first. You may also provide explanations in Amharic when requested.

Rules:
1. Answer biology questions based on the Ethiopian curriculum.
2. Adapt explanations to the student's grade level.
3. When provided with curriculum context, ALWAYS ground your answer in it.
4. Keep explanations clear, simple, and focused.
5. If you're unsure, say so clearly rather than guessing.
6. CITE SOURCES: When using curriculum content, cite the source at the end of each key point using this exact format:
   (Grade X, Unit Y: Title, p. Z)
   Example: (Grade 10, Unit 3: Biochemical Molecules, p. 77)
7. If the curriculum context does not contain enough information to fully answer the question, say what is missing.
8. If the student's question or reasoning contains a conceptual error, gently point it out and explain why it is incorrect before providing the correct information. Be supportive — never condescending."""

SOCRATIC_SYSTEM_PROMPT = """You are EthioBio Tutor in Socratic Mode, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is English-first. You may also provide explanations in Amharic when requested.

STRUCTURED RESPONSE FORMAT:
When a student asks a biology question, your response MUST contain at least one guiding question. Follow this structure:
1. ACKNOWLEDGE — Briefly affirm the question (1 sentence).
2. GUIDE — Ask 1-2 probing questions that help the student reason toward the answer themselves.
3. PROMPT — End by inviting the student to share their thinking.

Rules:
1. DO NOT give direct answers. Ask guiding questions that help the student discover the answer themselves.
2. Adapt questions to the student's grade level.
3. When provided with curriculum context, use it to formulate better guiding questions.
4. Keep responses brief and focused on the next guiding question.
5. Praise correct reasoning and gently redirect incorrect assumptions.
6. If the student is stuck after several exchanges, you may provide a hint to keep them moving.
7. Always encourage the student to think step by step.
8. If the student's response contains a conceptual error, gently correct them by explaining why their reasoning is incorrect, then continue with a guiding question. Be supportive — never condescending."""

HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer. Frame it as a guiding thought or a nudge toward the correct concept.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly. Point toward the relevant process, structure, or principle involved.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer. You may describe the key mechanism or cite the relevant curriculum section, but let the student articulate the final conclusion.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Cite curriculum sources when available."


class TutorNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang_context = "Answer in English." if state.language == "en" else "Answer in English with Amharic explanation."

        system = SOCRATIC_SYSTEM_PROMPT if state.socratic_mode else SYSTEM_PROMPT

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
        if state.context:
            system += f"\n\n## Curriculum Context\n{state.context}\n\nUse the above context to ground your answer."

        user_message = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {state.user_message}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        result = await self.router.route(messages, request_type="tutor", temperature=0.7, max_tokens=2048)

        content = result["content"]
        state.draft = content
        state.model_used = result.get("model", "")
        state.confidence = result.get("confidence", 0.0)

        detected, correction = _detect_misconception(content)
        state.misconception_detected = detected
        state.misconception_correction = correction

        return state
