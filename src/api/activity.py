from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MessageThread, QuizAttempt, UserAchievement, XpEvent
from src.database.session import get_session
from src.schemas.activity import ActivityFeedResponse, ActivityItem

logger = structlog.get_logger()
router = APIRouter(prefix="/activity", tags=["Activity"])

LIMIT = 20


@router.get("/{user_id}", response_model=ActivityFeedResponse)
async def get_activity_feed(user_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        activities: list[ActivityItem] = []

        xp_result = await session.execute(
            select(XpEvent)
            .where(XpEvent.user_id == user_id)
            .order_by(XpEvent.created_at.desc())
            .limit(LIMIT)
        )
        for event in xp_result.scalars().all():
            label = event.source.replace("_", " ").title()
            activities.append(ActivityItem(
                activity_type="xp_event",
                title=f"{label}",
                description=f"{event.amount} XP earned",
                icon="Zap",
                timestamp=event.created_at,
                metadata={"source": event.source, "amount": event.amount},
            ))

        quiz_result = await session.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.started_at.desc())
            .limit(LIMIT)
        )
        for attempt in quiz_result.scalars().all():
            score_text = f"{attempt.score:.0f}%" if attempt.score is not None else "In progress"
            activities.append(ActivityItem(
                activity_type="quiz_attempt",
                title="Quiz Attempt",
                description=f"Score: {score_text} ({attempt.completed} of {attempt.total})"
                if attempt.completed else f"Completed {int(attempt.total)} questions",
                icon="FileCheck",
                timestamp=attempt.started_at,
                metadata={
                    "score": attempt.score, "total": attempt.total,
                    "completed": attempt.completed,
                },
            ))

        thread_result = await session.execute(
            select(MessageThread)
            .where(MessageThread.user_id == user_id)
            .order_by(MessageThread.created_at.desc())
            .limit(LIMIT)
        )
        for thread in thread_result.scalars().all():
            msg_count = len(thread.messages) if isinstance(thread.messages, list) else 0
            topic = thread.topic or "Biology question"
            activities.append(ActivityItem(
                activity_type="tutor_session",
                title=f"Tutor Session — {topic}",
                description=f"{msg_count} messages ({thread.channel})",
                icon="MessageSquare",
                timestamp=thread.created_at,
                metadata={
                    "channel": thread.channel, "topic": thread.topic,
                    "message_count": msg_count,
                },
            ))

        ach_result = await session.execute(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(LIMIT)
        )
        for ach in ach_result.scalars().all():
            activities.append(ActivityItem(
                activity_type="achievement",
                title=ach.title,
                description=ach.description or "Achievement unlocked",
                icon="Medal",
                timestamp=ach.unlocked_at,
                metadata={"achievement_id": ach.achievement_id},
            ))

        activities.sort(key=lambda a: a.timestamp, reverse=True)
        activities = activities[:LIMIT]

        return ActivityFeedResponse(activities=activities)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("activity_feed_error", user_id=str(user_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
