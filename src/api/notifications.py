import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import NotificationPreference
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationPrefsRequest(BaseModel):
    email: str
    digest_frequency: str = "never"
    milestone_alerts: bool = True
    review_reminders: bool = True


class NotificationPrefsResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    email_verified: bool
    digest_frequency: str
    milestone_alerts: bool
    review_reminders: bool

    model_config = {"from_attributes": True}


@router.get("/preferences/{user_id}", response_model=NotificationPrefsResponse)
async def get_preferences(user_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.put("/preferences/{user_id}", response_model=NotificationPrefsResponse)
async def update_preferences(
    user_id: str, body: NotificationPrefsRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs:
        prefs.email = body.email
        prefs.digest_frequency = body.digest_frequency
        prefs.milestone_alerts = body.milestone_alerts
        prefs.review_reminders = body.review_reminders
        prefs.email_verified = False
        prefs.verification_code = None
        prefs.verification_expires = None
    else:
        prefs = NotificationPreference(
            user_id=uuid.UUID(user_id),
            email=body.email,
            email_verified=False,
            digest_frequency=body.digest_frequency,
            milestone_alerts=body.milestone_alerts,
            review_reminders=body.review_reminders,
        )
        session.add(prefs)
    await session.commit()
    return prefs


@router.post("/preferences/{user_id}/verify")
async def send_verification(user_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    code = secrets.token_hex(6)
    prefs.verification_code = code
    prefs.verification_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await session.commit()
    return {"message": "Verification code sent", "code": code}


@router.post("/preferences/{user_id}/verify/{code}")
async def confirm_verification(
    user_id: str, code: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    if prefs.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")
    if prefs.verification_expires and prefs.verification_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired")
    prefs.email_verified = True
    prefs.verification_code = None
    prefs.verification_expires = None
    await session.commit()
    return {"message": "Email verified"}
