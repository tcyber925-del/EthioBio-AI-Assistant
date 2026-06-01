from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import MisconceptionSummary
from src.database.models import MisconceptionPattern


async def load_misconceptions(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(MisconceptionPattern).where(
            MisconceptionPattern.user_id == user_id,
            MisconceptionPattern.frequency > 0,
        )
    )
    patterns = result.scalars().all()
    if not patterns:
        return None

    misconceptions = [
        MisconceptionSummary(
            topic=p.topic,
            pattern_type=p.pattern_type,
            frequency=p.frequency,
        )
        for p in patterns
    ]

    return {"misconceptions": misconceptions}
