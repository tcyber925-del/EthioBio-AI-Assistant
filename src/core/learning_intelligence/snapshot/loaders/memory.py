from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import EducationalMemorySummary
from src.database.models import MemoryEducationalSummary


async def load_memory(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(MemoryEducationalSummary)
        .where(MemoryEducationalSummary.user_id == user_id)
        .order_by(MemoryEducationalSummary.created_at.desc())
        .limit(5)
    )
    summaries = result.scalars().all()
    if not summaries:
        return None

    latest = summaries[0]
    understanding_level = latest.understanding_level
    confidence = latest.confidence

    all_goals: list[str] = []
    recent_topics: list[str] = []
    seen_topics: set[str] = set()

    for s in summaries:
        if s.next_learning_goal and s.next_learning_goal not in all_goals:
            all_goals.append(s.next_learning_goal)
        if s.topic and s.topic not in seen_topics:
            seen_topics.add(s.topic)
            recent_topics.append(s.topic)

    educational_memory = EducationalMemorySummary(
        understanding_level=understanding_level,
        confidence=confidence,
        active_learning_goals=all_goals,
        recent_topics=recent_topics,
    )

    return {
        "educational_memory": educational_memory,
        "learning_goals": all_goals.copy(),
    }
