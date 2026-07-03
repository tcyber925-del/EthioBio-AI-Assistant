from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEducationalSummary, MemoryEvent, SemanticFact
from src.database.session import get_session

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/memory", tags=["Memory Timeline"])


class TimelineItem(BaseModel):
    id: str
    type: str  # "event", "summary", "fact"
    timestamp: datetime
    title: str
    description: str
    metadata: dict[str, Any]


def format_event_title(event_type: str) -> str:
    parts = event_type.replace("_", " ").split()
    return " ".join(p.capitalize() for p in parts)


def format_event_description(event: MemoryEvent) -> str:
    t = event.topic or "General"
    meta = event.event_metadata or {}
    
    if event.event_type == "quiz_completed":
        score = meta.get("score", 0)
        total = meta.get("total_questions", 0)
        return f"Completed quiz on {t} with a score of {score}/{total}."
    elif event.event_type == "lesson_viewed":
        return f"Viewed lesson on {t}."
    elif event.event_type == "session_started":
        mode = meta.get("mode", "Socratic")
        return f"Started a new {mode} tutoring session on {t}."
    elif event.event_type == "recovery_task_done":
        return f"Finished adaptive recovery task on {t}."
    elif event.event_type == "misconception_detected":
        misconception = meta.get("misconception", "unknown")
        return f"Detected misconception on {t}: {misconception}."
    elif event.event_type == "xp_awarded":
        amount = meta.get("amount", 0)
        source = meta.get("source", "activity")
        return f"Awarded {amount} XP from {source}."
    elif event.event_type == "streak_updated":
        streak = meta.get("current_streak", 0)
        return f"Streak updated to {streak} days."
    elif event.event_type == "achievement_unlocked":
        title = meta.get("title", "achievement")
        return f"Unlocked achievement: {title}."
    
    return f"Logged {event.event_type} event on topic {t}."


@router.get("/timeline/{user_id}", response_model=list[TimelineItem])
async def get_memory_timeline(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    # Fetch events
    events_stmt = (
        select(MemoryEvent)
        .where(MemoryEvent.user_id == user_id)
        .order_by(MemoryEvent.created_at.desc())
        .limit(limit + offset)
    )
    events_res = await db.execute(events_stmt)
    events = events_res.scalars().all()

    # Fetch summaries
    summaries_stmt = (
        select(MemoryEducationalSummary)
        .where(MemoryEducationalSummary.user_id == user_id)
        .order_by(MemoryEducationalSummary.created_at.desc())
        .limit(limit + offset)
    )
    summaries_res = await db.execute(summaries_stmt)
    summaries = summaries_res.scalars().all()

    # Fetch semantic facts
    facts_stmt = (
        select(SemanticFact)
        .where(SemanticFact.user_id == user_id, SemanticFact.is_active == True)
        .order_by(SemanticFact.created_at.desc())
        .limit(limit + offset)
    )
    facts_res = await db.execute(facts_stmt)
    facts = facts_res.scalars().all()

    # Composite into a single timeline
    items: list[TimelineItem] = []

    for event in events:
        items.append(
            TimelineItem(
                id=str(event.id),
                type="event",
                timestamp=event.created_at,
                title=format_event_title(event.event_type),
                description=format_event_description(event),
                metadata=event.event_metadata or {},
            )
        )

    for summary in summaries:
        misconceptions_count = len(summary.key_misconceptions or [])
        desc = (
            f"Tutoring session summary on {summary.topic}. "
            f"Understanding level: {summary.understanding_level or 'Unknown'}. "
            f"Confidence: {summary.confidence:.2f}. "
        )
        if misconceptions_count > 0:
            desc += f"Detected {misconceptions_count} key misconceptions."
        
        items.append(
            TimelineItem(
                id=str(summary.id),
                type="summary",
                timestamp=summary.created_at,
                title=f"Session Summary: {summary.topic}",
                description=desc.strip(),
                metadata={
                    "topic": summary.topic,
                    "understanding_level": summary.understanding_level,
                    "key_misconceptions": summary.key_misconceptions,
                    "confidence": summary.confidence,
                    "next_learning_goal": summary.next_learning_goal,
                },
            )
        )

    for fact in facts:
        items.append(
            TimelineItem(
                id=str(fact.id),
                type="fact",
                timestamp=fact.created_at,
                title=f"Learner Profile Update",
                description=f"Identified learning pattern/preference: {fact.fact_key} = {fact.fact_value}.",
                metadata={
                    "fact_key": fact.fact_key,
                    "fact_value": fact.fact_value,
                    "category": fact.category,
                    "confidence": fact.confidence,
                },
            )
        )

    # Sort all chronologically descending
    items.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply pagination offset & limit
    paginated_items = items[offset : offset + limit]
    return paginated_items
