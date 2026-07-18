from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import RecoveryPlan, User, UserAchievement, UserGamification, XpEvent
from src.database.session import get_session
from src.schemas.gamification import (
    AchievementResponse,
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
    "diagram_completion": 10,
    "daily_streak_bonus": 20,
    "achievement_unlock": 50,
    "recovery_task_completion": 40,
    "recovery_milestone": 50,
}

RECOVERY_MILESTONE_THRESHOLDS = {3: 30, 5: 50, 10: 100, 15: 150}


STREAK_BONUS_THRESHOLDS = {7: 20, 14: 50, 21: 100, 30: 200}

ACHIEVEMENT_DEFINITIONS = {
    "first_quiz": {
        "title": "First Steps",
        "description": "Complete your first quiz",
        "icon": "🎯",
        "condition": "quiz_count >= 1",
    },
    "quiz_master": {
        "title": "Quiz Master",
        "description": "Complete 10 quizzes",
        "icon": "📚",
        "condition": "quiz_count >= 10",
    },
    "perfect_score": {
        "title": "Perfect Score",
        "description": "Get 100% on any quiz",
        "icon": "💯",
        "condition": "perfect_quiz >= 1",
    },
    "streak_3": {
        "title": "Streak Starter",
        "description": "Maintain a 3-day streak",
        "icon": "🔥",
        "condition": "streak >= 3",
    },
    "streak_7": {
        "title": "Dedicated",
        "description": "Maintain a 7-day streak",
        "icon": "🔥",
        "condition": "streak >= 7",
    },
    "streak_30": {
        "title": "Scholar",
        "description": "Maintain a 30-day streak",
        "icon": "🏅",
        "condition": "streak >= 30",
    },
    "xp_1000": {
        "title": "XP Hunter",
        "description": "Earn 1000 total XP",
        "icon": "⭐",
        "condition": "xp >= 1000",
    },
    "level_5": {
        "title": "Biology Expert",
        "description": "Reach Level 5",
        "icon": "🧬",
        "condition": "level >= 5",
    },
    "level_10": {
        "title": "Master Biologist",
        "description": "Reach Level 10",
        "icon": "👑",
        "condition": "level >= 10",
    },
}


async def update_streak(user_id, session):
    gam = await ensure_gamification(user_id, session)
    today = datetime.now(timezone.utc).date()

    if gam.last_active_date is not None:
        lad = gam.last_active_date
        last = lad.date() if hasattr(lad, "date") else lad
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
            user_id,
            "daily_streak_bonus",
            bonus_xp,
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


async def get_user_achievements(user_id, session):
    result = await session.execute(
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .order_by(UserAchievement.unlocked_at.desc())
    )
    return [
        AchievementResponse(
            id=a.achievement_id,
            title=a.title,
            description=a.description or "",
            icon=a.icon,
            unlocked_at=a.unlocked_at,
        )
        for a in result.scalars().all()
    ]


async def check_achievements(user_id, gam, session):
    unlocked = []
    result = await session.execute(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    )
    existing = {a.achievement_id for a in result.scalars().all()}

    xp_total = gam.total_xp
    streak = gam.current_streak
    level = gam.level

    condition_map = {
        "first_quiz": xp_total >= 10,
        "quiz_master": False,
        "perfect_score": False,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
        "streak_30": streak >= 30,
        "xp_1000": xp_total >= 1000,
        "level_5": level >= 5,
        "level_10": level >= 10,
    }

    for ach_id, achieved in condition_map.items():
        if ach_id not in existing and achieved:
            defn = ACHIEVEMENT_DEFINITIONS[ach_id]
            ua = UserAchievement(
                user_id=user_id,
                achievement_id=ach_id,
                title=defn["title"],
                description=defn["description"],
                icon=defn["icon"],
            )
            session.add(ua)
            await session.flush()
            gam.total_xp += 50
            gam.level = calculate_level(gam.total_xp)
            event = XpEvent(
                user_id=user_id,
                source="achievement_unlock",
                amount=50,
                event_metadata={"achievement_id": ach_id, "title": defn["title"]},
            )
            session.add(event)
            unlocked.append(ua)
    return unlocked


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
        await check_achievements(request.user_id, gam, session)
        await session.commit()

        events = await _get_recent_events(request.user_id, session)
        return await _build_profile(
            gam, request.user_id, events, level_up=level_up, session=session
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("xp_award_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}", response_model=GamificationProfileResponse)
async def get_gamification_profile(user_id, session: AsyncSession = Depends(get_session)):
    try:
        gam = await ensure_gamification(user_id, session)
        events = await _get_recent_events(user_id, session)
        return await _build_profile(gam, user_id, events, session=session)
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
        await check_achievements(request.user_id, gam, session)
        await session.commit()
        events = await _get_recent_events(request.user_id, session)
        return await _build_profile(gam, request.user_id, events, session=session)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("activity_record_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{user_id}", response_model=list[XpEventResponse])
async def get_xp_events(user_id, session: AsyncSession = Depends(get_session)):
    try:
        events = await _get_recent_events(user_id, session, limit=50)
        return events
    except Exception as e:
        logger.error("xp_events_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/achievements/{user_id}", response_model=list[AchievementResponse])
async def get_user_achievements_endpoint(user_id, session: AsyncSession = Depends(get_session)):
    try:
        return await get_user_achievements(user_id, session)
    except Exception as e:
        logger.error("achievements_error", error=str(e))
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


async def _build_profile(gam, user_id, events, level_up=False, session=None):
    from src.schemas.gamification import progress_pct, xp_for_next_level

    achievements = []
    new_achievements = []
    recovery_progress = None
    if session:
        achievements = await get_user_achievements(user_id, session)
        recovery_progress = await _get_recovery_progress(user_id, session)
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
        achievements=achievements,
        new_achievements=new_achievements,
        recovery_progress=recovery_progress,
    )


async def _get_recovery_progress(user_id, session):
    from src.schemas.gamification import RecoveryProgressResponse

    try:
        plans_result = await session.execute(
            select(RecoveryPlan)
            .where(RecoveryPlan.user_id == user_id, RecoveryPlan.status == "active")
            .options(selectinload(RecoveryPlan.tasks))
        )
        plans = plans_result.scalars().all()
        if not plans:
            return None

        total_tasks = sum(p.total_tasks for p in plans)
        completed_tasks = sum(p.completed_tasks for p in plans)
        overall_progress = round(completed_tasks / max(total_tasks, 1) * 100, 1)

        return RecoveryProgressResponse(
            active_plans=len(plans),
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            overall_progress_pct=overall_progress,
        )
    except Exception:
        return None
