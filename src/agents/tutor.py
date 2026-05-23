from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import BaseAgent
from src.rag.retriever import Retriever
from src.llm.router import ModelRouter
from uuid import UUID
import structlog

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

Rules:
1. DO NOT give the student a direct answer to their biology question right away.
2. Instead, ask one or two probing questions that help them think through the problem themselves.
3. Relate your guiding questions to the Ethiopian curriculum context when provided.
4. Adapt your questions to the student's grade level — simpler for Grade 7, more advanced for Grade 12.
5. If the student's answer shows they are on the right track, affirm and ask a deeper question.
6. If the student is stuck or uncertain, provide a hint or break the problem into smaller steps.
7. When provided with curriculum context, use it to frame your guiding questions.
8. If you're unsure about the biology content, say so rather than misleading.
9. After several back-and-forth exchanges or if the student explicitly asks for the answer, you may provide a complete explanation with source citations."""


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
        }
