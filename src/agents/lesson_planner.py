import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

LESSON_SYSTEM_PROMPT = """You are EthioBio Lesson Planner, creating biology lesson plans for Ethiopian teachers (Grades 7-12).

Output a JSON object following this schema:
{
  "objective": "Clear learning objective",
  "prior_knowledge": "What students should already know",
  "explanation": "Main lesson content and explanation",
  "activities": [{"name": "Activity name", "duration_minutes": 10, "description": "What to do", "type": "group|individual|pair"}],
  "assessment": "How to assess understanding",
  "homework": "Optional homework assignment",
  "teacher_notes": "Tips and preparation notes for the teacher"
}

Ensure content matches the Ethiopian biology curriculum for the specified grade level.
"""


class LessonPlannerAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="lesson_planner")

    async def generate(
        self,
        grade_level: int,
        topic: str,
        duration_minutes: int = 40,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        if language == "am":
            lang_instruction = "Generate all content in Amharic (አማርኛ). Lesson plan explanation, activities, assessment — all in Amharic."
        elif language == "both":
            lang_instruction = "Generate content in English with key terms and explanations also in Amharic."
        else:
            lang_instruction = "Generate all content in English."

        user_message = f"""Create a biology lesson plan for Grade {grade_level} on topic: {topic}.
Lesson duration: {duration_minutes} minutes.
{lang_instruction}

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=LESSON_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=4096,
            request_type="lesson_planning",
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            return {
                "objective": parsed.get("objective", ""),
                "prior_knowledge": parsed.get("prior_knowledge", ""),
                "explanation": parsed.get("explanation", ""),
                "activities": parsed.get("activities", []),
                "assessment": parsed.get("assessment", ""),
                "homework": parsed.get("homework"),
                "teacher_notes": parsed.get("teacher_notes"),
                "model_used": result.get("model", ""),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("lesson_parse_error", error=str(e), content=result["content"][:200])
            return {
                "objective": "Error parsing lesson plan",
                "prior_knowledge": "",
                "explanation": result["content"],
                "activities": [],
                "assessment": "",
                "homework": None,
                "teacher_notes": None,
                "model_used": result.get("model", ""),
            }
