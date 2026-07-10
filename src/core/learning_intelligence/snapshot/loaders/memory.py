from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import EducationalMemorySummary
from src.database.models import MemoryEducationalSummary, SemanticFact


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

    semantic_result = await session.execute(
        select(SemanticFact)
        .where(SemanticFact.user_id == user_id, SemanticFact.is_active)
        .order_by(SemanticFact.updated_at.desc())
        .limit(10)
    )
    semantic_facts = semantic_result.scalars().all()
    semantic_data = [
        {"key": f.fact_key, "value": f.fact_value, "category": f.category} for f in semantic_facts
    ]

    return {
        "educational_memory": educational_memory,
        "learning_goals": all_goals.copy(),
        "semantic_facts": semantic_data,
    }
