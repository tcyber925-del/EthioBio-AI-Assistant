from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService
from src.database.models import User
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

snapshot_service = SnapshotService()


@router.get("/snapshot/{user_id}")
async def get_learner_snapshot(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    snapshot = await snapshot_service.get_snapshot(session, user_id)
    return snapshot
