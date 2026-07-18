from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import ReviewSummary
from src.database.models import SpacedRepetitionSchedule


async def load_reviews(session: AsyncSession, user_id: UUID) -> dict | None:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(SpacedRepetitionSchedule).where(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.next_review_at <= now,
        )
    )
    schedules = result.scalars().all()
    if not schedules:
        return None

    due_reviews = [
        ReviewSummary(
            topic=s.topic,
            next_review_at=s.next_review_at,
            days_overdue=max(0, (now - s.next_review_at).days),
        )
        for s in schedules
    ]

    return {"due_reviews": due_reviews}
