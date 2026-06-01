from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import StudentMastery


async def load_mastery(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(StudentMastery).where(StudentMastery.user_id == user_id)
    )
    masteries = result.scalars().all()
    if not masteries:
        return None

    mastery_by_topic: dict[str, dict] = {}
    weak_topics: list[str] = []
    strong_topics: list[str] = []

    for m in masteries:
        mastery_by_topic[m.topic] = {
            "average_score": m.average_score,
            "confidence": m.confidence,
            "severity": m.severity,
            "attempt_count": m.attempt_count,
        }
        if m.severity in ("critical", "moderate"):
            weak_topics.append(m.topic)
        elif m.severity == "good":
            strong_topics.append(m.topic)

    return {
        "mastery_by_topic": mastery_by_topic,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }
