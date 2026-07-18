import asyncio
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.database.models import (
    MisconceptionPattern,
    QuizAttempt,
    SpacedRepetitionSchedule,
    StudentMastery,
    User,
    UserAchievement,
    UserGamification,
    XpEvent,
)
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/student", tags=["Student"])


class DashboardResponse(BaseModel):
    user: dict
    gamification: dict
    readiness: dict
    weak_topics: list
    due_reviews: list
    recent_activity: list


@router.get("/dashboard")
async def get_student_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    async def _gamification():
        g = (
            await session.execute(
                select(UserGamification).where(UserGamification.user_id == user_id)
            )
        ).scalar_one_or_none()
        achievements = (
            (
                await session.execute(
                    select(UserAchievement).where(UserAchievement.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
        return {
            "total_xp": g.total_xp if g else 0,
            "level": g.level if g else 1,
            "current_streak": g.current_streak if g else 0,
            "longest_streak": g.longest_streak if g else 0,
            "next_level_xp": _next_level_xp(g.level if g else 1),
            "achievements": [
                {
                    "id": a.achievement_id,
                    "title": a.title,
                    "description": a.description,
                    "icon": a.icon,
                    "unlocked_at": a.unlocked_at.isoformat() if a.unlocked_at else None,
                }
                for a in achievements
            ],
        }

    async def _weak_topics():
        records = (
            (
                await session.execute(
                    select(StudentMastery)
                    .where(
                        StudentMastery.user_id == user_id,
                        StudentMastery.average_score < 70,
                    )
                    .order_by(StudentMastery.average_score.asc())
                )
            )
            .scalars()
            .all()
        )

        result = []
        for m in records:
            mc = (
                (
                    await session.execute(
                        select(MisconceptionPattern).where(
                            MisconceptionPattern.user_id == user_id,
                            MisconceptionPattern.topic == m.topic,
                            MisconceptionPattern.resolved.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )
            result.append(
                {
                    "topic": m.topic,
                    "severity": m.severity,
                    "average_score": m.average_score,
                    "attempt_count": m.attempt_count,
                    "misconceptions": [p.pattern_description for p in mc],
                }
            )
        return result

    async def _due_reviews():
        now = datetime.now(timezone.utc)
        schedules = (
            (
                await session.execute(
                    select(SpacedRepetitionSchedule)
                    .where(
                        SpacedRepetitionSchedule.user_id == user_id,
                        SpacedRepetitionSchedule.next_review_at <= now,
                    )
                    .order_by(SpacedRepetitionSchedule.next_review_at.asc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "topic": s.topic,
                "next_review_at": s.next_review_at.isoformat() if s.next_review_at else None,
                "mastery_score": s.mastery_score,
                "interval_days": s.interval_days,
            }
            for s in schedules
        ]

    async def _recent_activity():
        xp_events = (
            (
                await session.execute(
                    select(XpEvent)
                    .where(XpEvent.user_id == user_id)
                    .order_by(XpEvent.created_at.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

        attempts = (
            (
                await session.execute(
                    select(QuizAttempt)
                    .where(QuizAttempt.user_id == user_id)
                    .order_by(QuizAttempt.completed_at.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

        items = []
        for e in xp_events:
            items.append(
                {
                    "type": "xp",
                    "description": f"+{e.amount} XP — {e.source}",
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )
        for a in attempts:
            if a.completed_at:
                pct = round((a.score / a.total * 100)) if a.total > 0 else 0
                items.append(
                    {
                        "type": "quiz",
                        "description": f"Quiz: {a.score:.0f}/{a.total} ({pct}%)",
                        "created_at": a.completed_at.isoformat() if a.completed_at else None,
                    }
                )

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:15]

    weak_topics, due_reviews, recent_activity, gamification = await asyncio.gather(
        _weak_topics(),
        _due_reviews(),
        _recent_activity(),
        _gamification(),
    )

    overall_readiness = 100.0
    topic_readiness: dict[str, float] = {}
    for wt in weak_topics:
        topic_readiness[wt["topic"]] = wt["average_score"]
        overall_readiness = min(overall_readiness, wt["average_score"])

    if not weak_topics:
        readiness_band = "Excellent"
    elif overall_readiness >= 80:
        readiness_band = "Excellent"
    elif overall_readiness >= 60:
        readiness_band = "Good"
    elif overall_readiness >= 40:
        readiness_band = "Needs Work"
    else:
        readiness_band = "At Risk"

    return DashboardResponse(
        user={
            "id": str(current_user.id),
            "email": current_user.email or "",
            "grade_level": current_user.grade_level,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        gamification=gamification,
        readiness={
            "overall_readiness": round(overall_readiness, 1),
            "readiness_band": readiness_band,
            "topic_readiness": topic_readiness,
        },
        weak_topics=weak_topics,
        due_reviews=due_reviews,
        recent_activity=recent_activity,
    )


def _next_level_xp(current_level: int) -> int:
    thresholds = [0, 100, 250, 500, 1000, 1750, 2750, 4000, 5500, 7500, 10000]
    if current_level < len(thresholds):
        return thresholds[current_level]
    return thresholds[-1] + (current_level - len(thresholds) + 1) * 5000
