from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.database.models import ProgressRecord as Record
from datetime import datetime
import structlog

logger = structlog.get_logger()

SUMMARY_SYSTEM_PROMPT = """You are EthioBio Parent Summary Agent. Create short, readable weekly progress reports for parents.
Focus on:
1. Topics studied this week
2. Performance (scores, trends)
3. Areas needing attention
4. General observations

Keep reports positive and constructive. Offer suggestions for how parents can help.
If performance is low (below 60%), include a gentle warning and specific recommendations.

For Amharic requests, provide the full summary in Amharic.
"""


class ParentSummaryAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="parent_summary")

    async def generate_summary(
        self,
        student_name: str,
        grade_level: Optional[int],
        records: list,
        profile,
        week_start: datetime,
        week_end: datetime,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        total_attempts = len(records)
        if total_attempts > 0:
            avg_score = sum(float(r.score) / max(r.total, 1) * 100 for r in records) / total_attempts
        else:
            avg_score = 0

        topics = set(r.topic for r in records) if records else set()
        is_low = avg_score < 60

        lang_instruction = "Write the summary in English." if language == "en" else \
            "Write the summary in Amharic."

        user_message = f"""Generate a weekly progress report (in {language}):

Student: {student_name}
Grade: {grade_level or 'N/A'}
Week: {week_start.date()} to {week_end.date()}
Topics covered: {', '.join(topics) if topics else 'None'}
Total quiz attempts: {total_attempts}
Average score: {avg_score:.1f}%
Performance warning: {'Yes' if is_low else 'No'}
Weak areas: {', '.join(profile.weak_areas) if profile and profile.weak_areas else 'None identified'}

{lang_instruction}"""

        result = await self._call_llm(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.5,
            max_tokens=1024,
            request_type="parent_summary",
        )

        amharic_content = None
        if language == "en":
            bilingual = await self._call_llm(
                system_prompt="Translate the following summary to Amharic. Keep the tone positive and constructive.",
                user_message=result["content"],
                session=session,
                temperature=0.3,
                max_tokens=1024,
                request_type="summary_translation",
            )
            amharic_content = bilingual["content"]

        return {
            "summary_text": result["content"],
            "summary_amharic": amharic_content,
            "is_low_performance_warning": is_low,
            "model_used": result.get("model", ""),
        }
