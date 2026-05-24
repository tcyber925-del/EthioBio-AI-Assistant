from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, UserGamification, XpEvent
from src.database.session import get_session
from src.schemas.gamification import (
    GamificationProfileResponse,
    XpAwardRequest,
    XpEventResponse,
    calculate_level,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/gamification", tags=["Gamification"])


XP_SOURCES = {
    "quiz_completion": 10,
    "quiz_high_score_bonus": 10,
    "quiz_perfect_score_bonus": 15,
    "tutor_interaction": 5,
    "daily_streak_bonus": 20,
    "achievement_unlock": 50,
}


STREAK_BONUS_THRESHOLDS = {7: 20, 14: 50, 21: 100, 30: 200}


async def update_streak(user_id, session):
    gam = await ensure_gamification(user_id, session)
    today = datetime.now(timezone.utc).date()

    if gam.last_active_date is not None:
        lad = gam.last_active_date
        last = lad.date() if hasattr(lad, 'date') else lad
        delta = (today - last).days
        if delta == 0:
            return gam, 0
        elif delta == 1:
            gam.current_streak += 1
        else:
            gam.current_streak = 1
    else:
        gam.current_streak = 1

    if gam.current_streak > gam.longest_streak:
        gam.longest_streak = gam.current_streak

    gam.last_active_date = datetime.now(timezone.utc)
    await session.flush()

    bonus_xp = STREAK_BONUS_THRESHOLDS.get(gam.current_streak, 0)
    if bonus_xp:
        _, _, _ = await award_xp(
            user_id, "daily_streak_bonus", bonus_xp,
            {"streak": gam.current_streak, "bonus_type": f"{gam.current_streak}_day_streak"},
            session,
        )

    return gam, gam.current_streak


async def ensure_gamification(user_id, session):
    result = await session.execute(
        select(UserGamification).where(UserGamification.user_id == user_id)
    )
    gam = result.scalar_one_or_none()
    if not gam:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        gam = UserGamification(user_id=user_id)
        session.add(gam)
        await session.flush()
    return gam


async def award_xp(user_id, source, amount, event_metadata, session):
    gam = await ensure_gamification(user_id, session)
    old_level = gam.level
    gam.total_xp += amount
    new_level = calculate_level(gam.total_xp)
    gam.level = new_level
    level_up = new_level > old_level
    event = XpEvent(
        user_id=user_id,
        source=source,
        amount=amount,
        event_metadata={**event_metadata, "level_up": level_up, "new_level": new_level},
    )
    session.add(event)
    await session.flush()
    return gam, event, level_up


@router.post("/xp", response_model=GamificationProfileResponse)
async def award_xp_endpoint(
    request: XpAwardRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        gam, event, level_up = await award_xp(
            request.user_id, request.source, request.amount, request.event_metadata, session
        )
        await session.commit()

        events = await _get_recent_events(request.user_id, session)
        return _build_profile(gam, request.user_id, events, level_up=level_up)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("xp_award_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}", response_model=GamificationProfileResponse)
async def get_gamification_profile(
    user_id, session: AsyncSession = Depends(get_session)
):
    try:
        gam = await ensure_gamification(user_id, session)
        events = await _get_recent_events(user_id, session)
        return _build_profile(gam, user_id, events)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("gamification_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activity", response_model=GamificationProfileResponse)
async def record_activity(
    request: XpAwardRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        gam, streak = await update_streak(request.user_id, session)
        await session.commit()
        events = await _get_recent_events(request.user_id, session)
        return _build_profile(gam, request.user_id, events)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("activity_record_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{user_id}", response_model=list[XpEventResponse])
async def get_xp_events(
    user_id, session: AsyncSession = Depends(get_session)
):
    try:
        events = await _get_recent_events(user_id, session, limit=50)
        return events
    except Exception as e:
        logger.error("xp_events_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _get_recent_events(user_id, session, limit=10):
    result = await session.execute(
        select(XpEvent)
        .where(XpEvent.user_id == user_id)
        .order_by(XpEvent.created_at.desc())
        .limit(limit)
    )
    return [
        XpEventResponse(
            id=e.id,
            source=e.source,
            amount=e.amount,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]


def _build_profile(gam, user_id, events, level_up=False):
    from src.schemas.gamification import progress_pct, xp_for_next_level
    return GamificationProfileResponse(
        user_id=user_id,
        total_xp=gam.total_xp,
        level=gam.level,
        current_streak=gam.current_streak,
        longest_streak=gam.longest_streak,
        next_level_xp=xp_for_next_level(gam.total_xp),
        progress_pct=progress_pct(gam.total_xp),
        level_up=level_up,
        new_level=gam.level if level_up else 0,
        recent_events=events,
    )
