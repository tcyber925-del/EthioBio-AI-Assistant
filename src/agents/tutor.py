from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.rag.retriever import Retriever

logger = structlog.get_logger()

TUTOR_SYSTEM_PROMPT = """You are EthioBio Tutor, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is English-first. You may also provide explanations in Amharic when requested.

Rules:
1. Answer biology questions based on the Ethiopian curriculum.
2. Adapt explanations to the student's grade level.
3. When provided with curriculum context, ALWAYS ground your answer in it.
4. Keep explanations clear, simple, and focused.
5. If the student asks in Amharic, respond bilingually.
6. Never provide medical advice or encourage harmful activities.
7. If you're unsure, say so clearly rather than guessing.
8. CITE SOURCES: When using curriculum content, cite the source at the end of each key point using this exact format:
   (Grade X, Unit Y: Title, p. Z)
   Example: (Grade 10, Unit 3: Biochemical Molecules, p. 77)
9. If the curriculum context does not contain enough information to fully answer the question, say what is missing."""

SOCRATIC_SYSTEM_PROMPT = """You are EthioBio Tutor (Socratic Mode), an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
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
9. After several back-and-forth exchanges or if the student explicitly asks for the answer, you may provide a complete explanation with source citations."""


HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer. Frame it as a guiding thought or a nudge toward the correct concept.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly. Point toward the relevant process, structure, or principle involved.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer. You may describe the key mechanism or cite the relevant curriculum section, but let the student articulate the final conclusion.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Cite curriculum sources when available."


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
                    if not d.get('metadata'):
                        continue
                    meta = d['metadata']
                    grade = meta.get('grade_level', '')
                    unit = meta.get('unit', '')
                    topic = meta.get('topic', '')
                    page = meta.get('page_number', '')
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
        lang_context = "Answer in English." if language == "en" else "Answer in English with Amharic explanation."

        prompt = SOCRATIC_SYSTEM_PROMPT if socratic_mode else TUTOR_SYSTEM_PROMPT
        system_prompt = prompt
        if reveal_answer:
            system_prompt += REVEAL_PROMPT
        elif hint_level > 0 and hint_level in HINT_PROMPTS:
            system_prompt += HINT_PROMPTS[hint_level]
        if context:
            system_prompt += f"\n\n## Curriculum Context\n{context}\n\nUse the above context to ground your answer."

        user_message = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {question}"

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            session=session,
            request_type="tutor",
        )

        return {
            "answer": result["content"],
            "sources": sources,
            "model_used": result.get("model", ""),
            "confidence": result.get("confidence", 0.0),
            "language": language,
            "socratic_mode": socratic_mode,
            "hint_level": hint_level,
            "reveal_answer": reveal_answer,
        }
