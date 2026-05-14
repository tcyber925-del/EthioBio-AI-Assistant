from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter, RetrievalFilter
import json
import structlog

logger = structlog.get_logger()

QUIZ_SYSTEM_PROMPT = """You are EthioBio Quiz Generator, creating assessments for Ethiopian biology students (Grades 7-12).

CRITICAL RULE: Generate questions BASED STRICTLY on the Ethiopian biology curriculum content provided below. Do NOT use your general biology knowledge. Every question and correct answer must be directly derivable from the curriculum context.

Curriculum Context:
{context}

For each question, follow this JSON schema:
{
  "question_type": "multiple_choice" | "true_false" | "short_answer" | "matching" | "diagram_label",
  "question_text": "the question",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."]  // only for multiple_choice
  "correct_answer": "the correct answer",
  "explanation": "brief explanation",
  "difficulty": "easy" | "medium" | "hard"
}

Output a JSON object with:
{
  "title": "Quiz title",
  "questions": [ ... question objects ... ],
  "answer_key": "Concise answer key string"
}
"""


class QuizAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter, adapter: Optional[VectorStoreAdapter] = None):
        super().__init__(llm_router, name="quiz")
        self.adapter = adapter or VectorStoreAdapter()

    async def generate(
        self,
        grade_level: int,
        topic: str,
        question_count: int = 5,
        types: list[str] = None,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        types_str = ", ".join(types or ["multiple_choice", "true_false"])
        lang_instruction = "Generate all content in English." if language == "en" else "Generate questions in English with Amharic answer explanations."

        # Retrieve curriculum context to ground questions
        filter_obj = RetrievalFilter(grade_level=grade_level)
        results = await self.adapter.search(query=topic, n_results=5, filter_obj=filter_obj)
        context = self.adapter.format_context(results) if results else f"Grade {grade_level} biology curriculum - {topic}"
        system_prompt = QUIZ_SYSTEM_PROMPT.replace("{context}", context)

        user_message = f"""Generate a biology quiz for Grade {grade_level} on topic: {topic}.
- Question count: {question_count}
- Question types: {types_str}
- {lang_instruction}

IMPORTANT: Base ALL questions on the curriculum context provided above. Do NOT use external knowledge.

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            session=session,
            temperature=0.8,
            max_tokens=4096,
            request_type="quiz_generation",
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            if isinstance(parsed, list):
                parsed = {"title": f"Grade {grade_level} - {topic}", "questions": parsed}
            return {
                "title": parsed.get("title", f"Grade {grade_level} - {topic}"),
                "questions": parsed.get("questions", []),
                "answer_key": parsed.get("answer_key", ""),
                "model_used": result.get("model", ""),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("quiz_parse_error", error=str(e), content=result["content"][:200])
            return {
                "title": f"Grade {grade_level} - {topic}",
                "questions": [],
                "answer_key": "Error parsing generated quiz",
                "model_used": result.get("model", ""),
            }
