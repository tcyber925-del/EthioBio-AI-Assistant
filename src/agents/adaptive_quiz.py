import math

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Question, QuestionAttempt, StudentAbility

logger = structlog.get_logger()


async def record_attempt(
    session: AsyncSession,
    user_id,
    question_id,
    quiz_id,
    correct: bool,
    time_spent: float | None = None,
    hints_used: int = 0,
) -> QuestionAttempt:
    prev_result = await session.execute(
        select(QuestionAttempt)
        .where(QuestionAttempt.user_id == user_id, QuestionAttempt.question_id == question_id)
        .order_by(QuestionAttempt.attempt_number.desc())
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    attempt_num = (prev.attempt_number + 1) if prev else 1

    attempt = QuestionAttempt(
        user_id=user_id,
        question_id=question_id,
        quiz_id=quiz_id,
        correct=correct,
        time_spent=time_spent,
        hints_used=hints_used,
        attempt_number=attempt_num,
    )
    session.add(attempt)
    logger.info(
        "attempt_recorded",
        user_id=user_id,
        question_id=question_id,
        correct=correct,
        attempt=attempt_num,
    )
    return attempt


def estimate_bayesian_ability(
    correct_count: int,
    total_count: int,
    prior_ability: float = 0.0,
    prior_uncertainty: float = 3.0,
) -> tuple[float, float]:
    if total_count == 0:
        return prior_ability, prior_uncertainty

    p = correct_count / total_count
    p = max(0.01, min(0.99, p))

    observed_ability = math.log(p / (1 - p))

    weight = min(total_count / (total_count + 5), 0.95)
    new_ability = (1 - weight) * prior_ability + weight * observed_ability
    new_uncertainty = prior_uncertainty / math.sqrt(total_count + 1)

    return new_ability, new_uncertainty


async def update_ability(
    session: AsyncSession,
    user_id,
    topic: str,
    correct_count: int,
    total_count: int,
    subject: str | None = None,
) -> StudentAbility:
    result = await session.execute(
        select(StudentAbility).where(
            StudentAbility.user_id == user_id,
            StudentAbility.topic == topic,
        )
    )
    ability = result.scalar_one_or_none()

    prior = ability.ability_score if ability else 0.0
    prior_uncertainty = ability.uncertainty if ability else 3.0

    new_ability, new_uncertainty = estimate_bayesian_ability(
        correct_count, total_count, prior, prior_uncertainty
    )

    if ability:
        ability.ability_score = new_ability
        ability.uncertainty = new_uncertainty
        ability.attempt_count += total_count
        if subject:
            ability.subject = subject
    else:
        ability = StudentAbility(
            user_id=user_id,
            topic=topic,
            ability_score=new_ability,
            uncertainty=new_uncertainty,
            attempt_count=total_count,
            subject=subject,
        )
        session.add(ability)

    return ability


async def get_ability(
    session: AsyncSession,
    user_id,
    topic: str,
    subject: str | None = None,
) -> tuple[float, float, int]:
    filters = [
        StudentAbility.user_id == user_id,
        StudentAbility.topic == topic,
    ]
    if subject:
        filters.append(
            (StudentAbility.subject == subject) | (StudentAbility.subject.is_(None))
        )
    result = await session.execute(select(StudentAbility).where(*filters))
    ability = result.scalar_one_or_none()
    if ability:
        return ability.ability_score, ability.uncertainty, ability.attempt_count
    return 0.0, 3.0, 0


async def migrate_difficulty_scores(session: AsyncSession):
    """One-time migration: convert string difficulties to numeric scores."""
    result = await session.execute(
        select(Question).where(Question.difficulty_score == 0.0, Question.difficulty != "medium")
    )
    questions = list(result.scalars().all())
    mapping = {"easy": -1.0, "medium": 0.0, "hard": 1.0}
    for q in questions:
        q.difficulty_score = mapping.get(q.difficulty, 0.0)
    if questions:
        await session.commit()


async def select_adaptive_questions(
    session: AsyncSession,
    user_id,
    topic: str,
    count: int = 5,
    exclude_ids: list | None = None,
    subject: str | None = None,
) -> list[Question]:
    ability, uncertainty, attempt_count = await get_ability(session, user_id, topic, subject)

    query = select(Question).where(Question.topic == topic)
    if exclude_ids:
        query = query.where(Question.id.notin_(exclude_ids))
    result = await session.execute(query)
    available = list(result.scalars().all())

    if not available:
        return []

    if attempt_count < 5:
        return available[:count]

    target = ability + 0.5
    available.sort(key=lambda q: abs(q.difficulty_score - target))
    return available[:count]
