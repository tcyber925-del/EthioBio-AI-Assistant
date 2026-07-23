import asyncio
from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

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
        token_queue: asyncio.Queue[TokenChunk | None] | None = None,
    ) -> dict:
        total_attempts = len(records)
        if total_attempts > 0:
            avg_score = (
                sum(float(r.score) / max(r.total, 1) * 100 for r in records) / total_attempts
            )
        else:
            avg_score = 0

        topics = {r.topic for r in records} if records else set()
        is_low = avg_score < 60

        if language == "am":
            lang_instruction = (
                "Write the summary in Amharic (አማርኛ) only. Use polite, encouraging tone."
            )
        elif language == "both":
            lang_instruction = "Write the summary in English. Include key points also in Amharic."
        else:
            lang_instruction = "Write the summary in English."

        user_message = f"""Generate a weekly progress report (in {language}):

Student: {student_name}
Grade: {grade_level or "N/A"}
Week: {week_start.date()} to {week_end.date()}
Topics covered: {", ".join(topics) if topics else "None"}
Total quiz attempts: {total_attempts}
Average score: {avg_score:.1f}%
Performance warning: {"Yes" if is_low else "No"}
Weak areas: {", ".join(profile.weak_areas) if profile and profile.weak_areas else "None identified"}

{lang_instruction}"""

        content: str
        model_used: str = ""

        if token_queue is not None:
            buf: list[str] = []
            async for token in self._call_llm_stream(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.5,
                max_tokens=1024,
                request_type="parent_summary",
            ):
                buf.append(token)
                token_queue.put_nowait(TokenChunk(delta=token, node="summary"))
            content = "".join(buf)
        else:
            result = await self._call_llm(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                user_message=user_message,
                session=session,
                temperature=0.5,
                max_tokens=1024,
                request_type="parent_summary",
            )
            content = result["content"]
            model_used = result.get("model", "")

        amharic_content = None
        if language in ("en", "both"):
            if token_queue is not None:
                token_queue.put_nowait(TokenChunk(delta="", node="summary", status=True))
                trans_buf: list[str] = []
                async for token in self._call_llm_stream(
                    system_prompt="Translate the following summary to Amharic. Keep the tone positive and constructive.",
                    user_message=content,
                    temperature=0.3,
                    max_tokens=1024,
                    request_type="summary_translation",
                ):
                    trans_buf.append(token)
                    token_queue.put_nowait(TokenChunk(delta=token, node="summary"))
                amharic_content = "".join(trans_buf)
            else:
                bilingual = await self._call_llm(
                    system_prompt="Translate the following summary to Amharic. Keep the tone positive and constructive.",
                    user_message=content,
                    session=session,
                    temperature=0.3,
                    max_tokens=1024,
                    request_type="summary_translation",
                )
                amharic_content = bilingual["content"]

        if token_queue is not None:
            token_queue.put_nowait(TokenChunk(delta="", node="summary", done=True))

        return {
            "summary_text": content,
            "summary_amharic": amharic_content,
            "is_low_performance_warning": is_low,
            "model_used": model_used,
        }
