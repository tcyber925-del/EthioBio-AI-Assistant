from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import SpacedRepetitionSchedule, StudentMastery

logger = structlog.get_logger()

MIN_EASE_FACTOR = 1.3
MAX_EASE_FACTOR = 3.0

INITIAL_INTERVALS = {
    "critical": 1,
    "moderate": 2,
    "mild": 3,
    "good": 7,
}

GOOD_THRESHOLD = 80.0
ACCEPTABLE_THRESHOLD = 60.0


def calculate_next_interval(
    mastery_score: float,
    current_interval: int,
    ease_factor: float,
    review_count: int,
) -> tuple[int, float]:
    if review_count == 0:
        if mastery_score < 40:
            days = 1
        elif mastery_score < 60:
            days = 2
        elif mastery_score < 80:
            days = 3
        else:
            days = 7
        return days, ease_factor

    if mastery_score >= GOOD_THRESHOLD:
        new_ease = min(ease_factor + 0.1, MAX_EASE_FACTOR)
        new_interval = current_interval * new_ease
    elif mastery_score >= ACCEPTABLE_THRESHOLD:
        new_ease = ease_factor
        new_interval = float(current_interval)
    else:
        new_ease = max(ease_factor - 0.2, MIN_EASE_FACTOR)
        new_interval = 1.0

    return max(int(round(new_interval)), 1), round(new_ease, 2)


async def generate_schedule(
    user_id: Any,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(StudentMastery)
        .where(StudentMastery.user_id == user_id)
        .order_by(StudentMastery.average_score.asc())
    )
    masteries = result.scalars().all()
    if not masteries:
        return []

    created: list[dict[str, Any]] = []
    for mastery in masteries:
        existing = await session.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.user_id == user_id,
                SpacedRepetitionSchedule.topic == mastery.topic,
            )
        )
        schedule = existing.scalar_one_or_none()

        interval_days, ease_factor = calculate_next_interval(mastery.average_score, 0, 2.5, 0)
        next_review = datetime.now(timezone.utc) + timedelta(days=interval_days)

        if schedule:
            schedule.mastery_score = mastery.average_score
            schedule.interval_days = interval_days
            schedule.ease_factor = ease_factor
            schedule.next_review_at = next_review
            schedule.grade_level = mastery.grade_level
            schedule.unit = mastery.unit
        else:
            schedule = SpacedRepetitionSchedule(
                user_id=user_id,
                topic=mastery.topic,
                unit=mastery.unit,
                grade_level=mastery.grade_level,
                mastery_score=mastery.average_score,
                interval_days=interval_days,
                ease_factor=ease_factor,
                next_review_at=next_review,
            )
            session.add(schedule)

        created.append(
            {
                "topic": mastery.topic,
                "interval_days": interval_days,
                "next_review_at": next_review,
            }
        )

    await session.commit()
    return created


async def get_due_reviews(
    user_id: Any,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(SpacedRepetitionSchedule)
        .where(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.next_review_at <= now,
        )
        .order_by(SpacedRepetitionSchedule.next_review_at.asc())
    )
    schedules = result.scalars().all()

    return [
        {
            "id": s.id,
            "topic": s.topic,
            "unit": s.unit or "",
            "grade_level": s.grade_level,
            "mastery_score": s.mastery_score,
            "interval_days": s.interval_days,
            "ease_factor": s.ease_factor,
            "next_review_at": s.next_review_at,
            "last_reviewed_at": s.last_reviewed_at,
            "review_count": s.review_count,
            "days_overdue": (now - s.next_review_at).days if s.next_review_at < now else 0,
        }
        for s in schedules
    ]


async def get_all_schedules(
    user_id: Any,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(SpacedRepetitionSchedule)
        .where(SpacedRepetitionSchedule.user_id == user_id)
        .order_by(SpacedRepetitionSchedule.next_review_at.asc())
    )
    schedules = result.scalars().all()

    now = datetime.now(timezone.utc)
    return [
        {
            "id": s.id,
            "topic": s.topic,
            "unit": s.unit or "",
            "grade_level": s.grade_level,
            "mastery_score": s.mastery_score,
            "interval_days": s.interval_days,
            "ease_factor": s.ease_factor,
            "next_review_at": s.next_review_at,
            "last_reviewed_at": s.last_reviewed_at,
            "review_count": s.review_count,
            "is_due": s.next_review_at <= now,
            "days_overdue": (now - s.next_review_at).days if s.next_review_at < now else 0,
        }
        for s in schedules
    ]


async def update_review(
    user_id: Any,
    topic: str,
    new_score: float,
    session: AsyncSession,
) -> dict[str, Any] | None:
    result = await session.execute(
        select(SpacedRepetitionSchedule).where(
            SpacedRepetitionSchedule.user_id == user_id,
            SpacedRepetitionSchedule.topic == topic,
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return None

    schedule.review_count += 1
    schedule.last_reviewed_at = datetime.now(timezone.utc)
    schedule.mastery_score = new_score

    interval_days, ease_factor = calculate_next_interval(
        new_score,
        schedule.interval_days,
        schedule.ease_factor,
        schedule.review_count,
    )
    schedule.interval_days = interval_days
    schedule.ease_factor = ease_factor
    schedule.next_review_at = datetime.now(timezone.utc) + timedelta(days=interval_days)

    await session.commit()

    return {
        "topic": schedule.topic,
        "interval_days": interval_days,
        "ease_factor": ease_factor,
        "next_review_at": schedule.next_review_at,
        "review_count": schedule.review_count,
    }
