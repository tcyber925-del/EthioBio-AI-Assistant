from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.recommendation.services import (
    RecommendationService,
)
from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService
from src.database.models import User
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

snapshot_service = SnapshotService()
recommendation_service = RecommendationService()


async def _check_user_exists(session: AsyncSession, user_id: UUID) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/snapshot/{user_id}")
async def get_learner_snapshot(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await _check_user_exists(session, user_id)
    snapshot = await snapshot_service.get_snapshot(session, user_id)
    return snapshot


@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await _check_user_exists(session, user_id)
    recommendations = await recommendation_service.get_recommendations(session, user_id)
    return recommendations


@router.get("/next-action/{user_id}")
async def get_next_action(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await _check_user_exists(session, user_id)
    recommendations = await recommendation_service.get_recommendations(session, user_id)
    if not recommendations:
        return {}
    return recommendations[0]
