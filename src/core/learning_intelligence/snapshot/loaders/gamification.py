from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import GamificationSummary
from src.database.models import UserGamification


async def load_gamification(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(UserGamification).where(UserGamification.user_id == user_id)
    )
    gam = result.scalar_one_or_none()
    if not gam:
        return None

    days_since_active = (
        (datetime.now(timezone.utc) - gam.last_active_date).days
        if gam.last_active_date
        else 999
    )
    recency = max(0.0, 1.0 - days_since_active / 30.0)
    streak_factor = min(1.0, gam.current_streak / 14.0)
    recent_activity_score = round(0.6 * recency + 0.4 * streak_factor, 2)

    return {
        "gamification": GamificationSummary(
            current_streak=gam.current_streak,
            longest_streak=gam.longest_streak,
            total_xp=gam.total_xp,
            level=gam.level,
            recent_activity_score=recent_activity_score,
        )
    }
