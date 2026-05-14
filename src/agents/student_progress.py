from typing import Optional
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ProgressRecord as Record
from datetime import datetime, timezone, timedelta
import structlog

logger = structlog.get_logger()

PROGRESS_SYSTEM_PROMPT = """You are EthioBio Progress Analyst. Analyze student performance data and produce insights.
Identify weak areas, track improvement or decline, and make recommendations."""


class StudentProgressAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="student_progress")

    def analyze_progress(self, records: list, profile) -> dict:
        if not records:
            return {
                "student_id": str(profile.id) if profile else "",
                "topics": {},
                "weak_areas": [],
                "overall_score": 0.0,
                "trend": "no_data",
            }

        topic_scores = {}
        for r in records:
            topic = r.topic
            if topic not in topic_scores:
                topic_scores[topic] = {"total": 0, "count": 0}
            topic_scores[topic]["total"] += float(r.score) / max(r.total, 1) * 100
            topic_scores[topic]["count"] += 1

        topics_summary = {}
        weak_areas = []
        for topic, data in topic_scores.items():
            avg = data["total"] / max(data["count"], 1)
            topics_summary[topic] = {"average_score": round(avg, 1), "attempts": data["count"]}
            if avg < 60:
                weak_areas.append(topic)

        overall = sum(d["total"] for d in topic_scores.values()) / max(
            sum(d["count"] for d in topic_scores.values()), 1
        )

        sorted_records = sorted(records, key=lambda r: r.recorded_at)
        if len(sorted_records) >= 2:
            half = len(sorted_records) // 2
            first_half = sum(
                float(r.score) / max(r.total, 1) * 100 for r in sorted_records[:half]
            ) / max(half, 1)
            second_half = sum(
                float(r.score) / max(r.total, 1) * 100 for r in sorted_records[half:]
            ) / max(len(sorted_records) - half, 1)
            trend = "improving" if second_half > first_half + 5 else "declining" if second_half < first_half - 5 else "stable"
        else:
            trend = "stable"

        return {
            "student_id": str(profile.id) if profile else "",
            "topics": topics_summary,
            "weak_areas": weak_areas,
            "overall_score": round(overall, 1),
            "trend": trend,
        }

    async def generate_insights(
        self,
        analysis: dict,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        user_message = f"""Analyze this student's performance data and provide learning recommendations:

Overall Score: {analysis['overall_score']}%
Trend: {analysis['trend']}
Weak Areas: {', '.join(analysis['weak_areas'])}
Topics: {analysis['topics']}

Provide 2-3 specific, actionable recommendations for improvement."""

        result = await self._call_llm(
            system_prompt=PROGRESS_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.5,
            max_tokens=1000,
            request_type="progress_insights",
        )

        return {
            "insights": result["content"],
            "model_used": result.get("model", ""),
        }
