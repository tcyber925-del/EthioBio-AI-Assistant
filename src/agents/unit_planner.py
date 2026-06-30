import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.agents.lesson_planner import LessonPlannerAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

UNIT_OUTLINE_PROMPT = (
    "You are EthioBio Unit Planner. Given a biology topic, grade level, "
    "and number of days, create a day-by-day unit outline.\n\n"
    "Output a JSON array:\n"
    "[\n"
    "  {\n"
    '    "day": 1,\n'
    '    "subtopic": "Subtopic for day 1",\n'
    '    "objective": "Learning objective for day 1"\n'
    "  },\n"
    "  {\n"
    '    "day": 2,\n'
    '    "subtopic": "Subtopic for day 2",\n'
    '    "objective": "Learning objective for day 2"\n'
    "  }\n"
    "]\n\n"
    "Each day should build on the previous one. The first day should "
    "introduce foundational concepts, and later days should progress "
    "to more advanced or applied topics. Ensure the scope fits the "
    "specified number of days and grade level."
)


class UnitPlannerAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="unit_planner")

    async def generate_unit(
        self,
        unit_title: str,
        grade_level: int,
        topic: str,
        days: int = 5,
        duration_minutes: int = 40,
        language: str = "en",
        session: Optional[AsyncSession] = None,
        generate_exit_ticket: bool = False,
        generate_differentiation: bool = False,
        generate_diagram_suggestions: bool = False,
        generate_misconception_activities: bool = False,
        preferred_model: Optional[str] = None,
    ) -> dict:
        outline = await self._generate_outline(
            unit_title=unit_title,
            grade_level=grade_level,
            topic=topic,
            days=days,
            session=session,
            preferred_model=preferred_model,
        )

        lesson_agent = LessonPlannerAgent(llm_router=self.llm_router)

        lessons = []
        for day_entry in outline:
            day_num = day_entry.get("day", 1)
            subtopic = day_entry.get("subtopic", topic)
            day_topic = f"{topic}: {subtopic}"

            result = await lesson_agent.generate(
                grade_level=grade_level,
                topic=day_topic,
                duration_minutes=duration_minutes,
                language=language,
                session=session,
                generate_exit_ticket=generate_exit_ticket,
                generate_differentiation=generate_differentiation,
                generate_diagram_suggestions=generate_diagram_suggestions,
                generate_misconception_activities=generate_misconception_activities,
            )

            lessons.append({
                "day_index": day_num,
                "subtopic": subtopic,
                "objective": day_entry.get("objective", ""),
                "lesson": result,
            })

        return {
            "unit_title": unit_title,
            "grade_level": grade_level,
            "topic": topic,
            "days": days,
            "language": language,
            "model_used": lessons[0]["lesson"].get("model_used", "") if lessons else "",
            "lessons": lessons,
        }

    async def _generate_outline(
        self,
        unit_title: str,
        grade_level: int,
        topic: str,
        days: int,
        session: Optional[AsyncSession] = None,
        preferred_model: Optional[str] = None,
    ) -> list[dict]:
        user_message = (
            f"Create a {days}-day unit outline for Grade {grade_level} "
            f"biology on topic: {topic}.\n"
            f"Unit title: {unit_title}\n"
            duration_minutes=duration_minutes,
        duration_minutes: int,
            f"Each day should be {duration_minutes} minutes.\n\n"
            f"Respond with valid JSON only."
        )

        result = await self._call_llm(
            system_prompt=UNIT_OUTLINE_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=2048,
            request_type="unit_planning",
            preferred_model=preferred_model,
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [entry for entry in parsed if isinstance(entry, dict)]
            if isinstance(parsed, dict):
                outline = parsed.get("outline")
                if isinstance(outline, list):
                    return [entry for entry in outline if isinstance(entry, dict)]
                days_payload = parsed.get("days")
                if isinstance(days_payload, list):
                    return [entry for entry in days_payload if isinstance(entry, dict)]
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("unit_outline_parse_error", error=str(e), content=result["content"][:200])
            return [
                {"day": i + 1, "subtopic": topic, "objective": f"Day {i + 1} of {topic}"}
                for i in range(days)
            ]
