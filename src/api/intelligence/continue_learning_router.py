from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.continue_learning import ContinueLearningService
from src.core.learning_intelligence.readiness import ReadinessService
from src.database.models import User
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

continue_learning_service = ContinueLearningService()
readiness_service = ReadinessService()


async def _check_user_exists(session: AsyncSession, user_id: UUID) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/continue-learning/{user_id}")
async def get_continue_learning_feed(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await _check_user_exists(session, user_id)
    readiness_profile = await readiness_service.get_readiness(session, user_id)
    feed = await continue_learning_service.get_feed(
        session, user_id, readiness_profile=readiness_profile
    )
    return feed
