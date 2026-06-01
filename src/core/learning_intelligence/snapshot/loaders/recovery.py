from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import RecoverySummary
from src.database.models import RecoveryPlan


async def load_recovery(session: AsyncSession, user_id: UUID) -> dict | None:
    result = await session.execute(
        select(RecoveryPlan).where(
            RecoveryPlan.user_id == user_id,
            RecoveryPlan.status == "active",
        )
    )
    plans = result.scalars().all()
    if not plans:
        return None

    active_recovery_plans = [
        RecoverySummary(
            topic=p.topic,
            progress_pct=(p.completed_tasks / p.total_tasks * 100) if p.total_tasks > 0 else 0.0,
            completed_tasks=p.completed_tasks,
            total_tasks=p.total_tasks,
            status=p.status,
        )
        for p in plans
    ]

    return {"active_recovery_plans": active_recovery_plans}
