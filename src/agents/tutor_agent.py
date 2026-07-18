import re
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.rag.retriever import Retriever

logger = structlog.get_logger()

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

TUTOR_SYSTEM_PROMPT = """You are EthioBio Tutor, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is in English. Follow language instructions provided in the user message.

Rules:
1. Answer biology questions based on the Ethiopian curriculum.
2. Adapt explanations to the student's grade level.
3. When provided with curriculum context, ALWAYS ground your answer in it.
4. Keep explanations clear, simple, and focused.
5. Follow the language instruction in the user message when responding.
6. Never provide medical advice or encourage harmful activities.
7. If you're unsure, say so clearly rather than guessing.
8. CITE SOURCES: When using curriculum content, cite the source at the end of each key point using this exact format:
   (Grade X, Unit Y: Title, p. Z)
   Example: (Grade 10, Unit 3: Biochemical Molecules, p. 77)
9. If the curriculum context does not contain enough information to fully answer the question, say what is missing.
10. If the student's question or reasoning contains a conceptual error, gently point it out and explain why it is incorrect before providing the correct information. Be supportive — never condescending."""

SOCRATIC_SYSTEM_PROMPT = """You are EthioBio Tutor (Socratic Mode), an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is in English. Follow language instructions provided in the user message.
You use the Socratic method — instead of giving direct answers, you guide students through reasoning.

STRUCTURED RESPONSE FORMAT:
When a student asks a biology question, your response MUST contain at least one guiding question. Follow this structure:
1. ACKNOWLEDGE — Briefly affirm the question (1 sentence).
2. GUIDE — Ask 1-2 probing questions that help the student reason toward the answer themselves.
3. PROMPT — End by inviting the student to share their thinking.

Rules:
1. DO NOT give the student a direct answer to their biology question. Guide them.
2. Ask at least one guiding question in every response.
3. Relate your guiding questions to the Ethiopian curriculum context when provided.
4. Adapt your questions to the student's grade level — simpler for Grade 7, more advanced for Grade 12.
5. If the student's answer shows they are on the right track, affirm and ask a deeper question.
6. If the student is stuck or uncertain, provide a hint or break the problem into smaller steps.
7. When provided with curriculum context, use it to frame your guiding questions.
8. If you're unsure about the biology content, say so rather than misleading.
9. After several back-and-forth exchanges or if the student explicitly asks for the answer, you may provide a complete explanation with source citations.
10. If the student's response contains a conceptual error, gently correct them by explaining why their reasoning is incorrect, then continue with a guiding question. Be supportive — never condescending."""


HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer. Frame it as a guiding thought or a nudge toward the correct concept.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly. Point toward the relevant process, structure, or principle involved.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer. You may describe the key mechanism or cite the relevant curriculum section, but let the student articulate the final conclusion.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Cite curriculum sources when available."


def detect_misconception(text: str) -> tuple[bool, str]:
    """Scan response text for misconception correction indicators.

    Returns (detected: bool, correction_sentence: str) where correction_sentence
    is the sentence(s) containing the detected indicator, or an empty string.
    """
    lower = text.lower()
    for indicator in MISCONCEPTION_INDICATORS:
        if indicator in lower:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for i, sentence in enumerate(sentences):
                if indicator in sentence.lower():
                    correction = sentence.strip()
                    if i + 1 < len(sentences):
                        correction += " " + sentences[i + 1].strip()
                    if len(correction) > 300:
                        correction = correction[:297] + "..."
                    return True, correction
    return False, ""


class TutorAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter, retriever: Optional[Retriever] = None):
        super().__init__(llm_router, name="tutor")
        self.retriever = retriever or Retriever()

    async def answer(
        self,
        question: str,
        user_id: UUID,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
        language: str = "en",
        use_rag: bool = True,
        session: Optional[AsyncSession] = None,
        socratic_mode: bool = False,
        hint_level: int = 0,
        reveal_answer: bool = False,
        memory_context: str = "",
        learner_profile_block: str = "",
        messages: list[dict] | None = None,
    ) -> dict:
        context = ""
        sources = []

        if use_rag and self.retriever:
            retrieved = await self.retriever.retrieve(
                query=question,
                n_results=3,
                grade_level=grade_level,
                topic=topic,
            )
            if retrieved:
                context = self.retriever.format_context(retrieved)
                sources = []
                for d in retrieved:
                    if not d.get("metadata"):
                        continue
                    meta = d["metadata"]
                    grade = meta.get("grade_level", "")
                    unit = meta.get("unit", "")
                    topic = meta.get("topic", "")
                    page = meta.get("page_number", "")
                    parts = []
                    if grade:
                        parts.append(f"Grade {grade}")
                    if unit:
                        parts.append(unit)
                    if topic:
                        parts.append(topic)
                    if page:
                        parts.append(f"p.{page}")
                    if parts:
                        sources.append(", ".join(parts))

        grade_context = f" (Grade {grade_level})" if grade_level else ""
        if language == "am":
            lang_context = (
                "Respond entirely in Amharic (አማርኛ). "
                "Use Amharic biology terminology. "
                "Never mix English unless quoting a technical term or scientific name. "
                "Always provide the Amharic equivalent of key terms."
            )
        elif language == "both":
            lang_context = (
                "Answer in English with Amharic explanation. "
                "Provide key terms in both English and Amharic."
            )
        else:
            lang_context = "Answer in English."

        prompt = SOCRATIC_SYSTEM_PROMPT if socratic_mode else TUTOR_SYSTEM_PROMPT
        system_prompt = prompt
        if learner_profile_block:
            system_prompt += "\n\n" + learner_profile_block
        if context:
            system_prompt += f"\n\n## Curriculum Context\n{context}\n\nUse the above context to ground your answer."
        if memory_context:
            system_prompt += f"\n\n{memory_context}"
        if reveal_answer:
            system_prompt += REVEAL_PROMPT
        elif hint_level > 0 and hint_level in HINT_PROMPTS:
            system_prompt += HINT_PROMPTS[hint_level]

        from src.core.memory.truncation import truncate_messages

        user_message = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {question}"

        history = truncate_messages(messages or [], budget=3000)
        llm_messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        result = await self.llm_router.route(
            messages=llm_messages,
            request_type="tutor",
            session=session,
            temperature=0.7,
            max_tokens=2048,
        )

        content = result["content"]
        misconception_detected, misconception_correction = detect_misconception(content)

        return {
            "answer": content,
            "sources": sources,
            "model_used": result.get("model", ""),
            "confidence": result.get("confidence", 0.0),
            "language": language,
            "socratic_mode": socratic_mode,
            "hint_level": hint_level,
            "reveal_answer": reveal_answer,
            "misconception_detected": misconception_detected,
            "misconception_correction": misconception_correction,
        }
