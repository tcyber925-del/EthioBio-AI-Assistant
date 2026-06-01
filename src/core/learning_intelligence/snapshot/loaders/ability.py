from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import StudentAbility


async def load_ability(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(StudentAbility).where(StudentAbility.user_id == user_id)
    )
    abilities = result.scalars().all()
    if not abilities:
        return None

    ability_by_topic: dict[str, dict] = {
        a.topic: {
            "ability_score": a.ability_score,
            "uncertainty": a.uncertainty,
            "attempt_count": a.attempt_count,
        }
        for a in abilities
    }

    return {"ability_by_topic": ability_by_topic}
