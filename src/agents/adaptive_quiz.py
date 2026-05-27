import math

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QuestionAttempt, StudentAbility

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


def estimate_ability(
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

    weight = min(total_count / max(total_count + 5, 1), 0.95)
    new_ability = (1 - weight) * prior_ability + weight * observed_ability
    new_uncertainty = prior_uncertainty / math.sqrt(max(total_count, 1) + 1)

    return new_ability, new_uncertainty


async def update_ability(
    session: AsyncSession,
    user_id,
    topic: str,
    correct_count: int,
    total_count: int,
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

    new_ability, new_uncertainty = estimate_ability(
        correct_count, total_count, prior, prior_uncertainty
    )

    if ability:
        ability.ability_score = new_ability
        ability.uncertainty = new_uncertainty
        ability.attempt_count += total_count
    else:
        ability = StudentAbility(
            user_id=user_id,
            topic=topic,
            ability_score=new_ability,
            uncertainty=new_uncertainty,
            attempt_count=total_count,
        )
        session.add(ability)

    return ability


async def get_ability(
    session: AsyncSession,
    user_id,
    topic: str,
) -> tuple[float, int]:
    result = await session.execute(
        select(StudentAbility).where(
            StudentAbility.user_id == user_id,
            StudentAbility.topic == topic,
        )
    )
    ability = result.scalar_one_or_none()
    if ability:
        return ability.ability_score, ability.attempt_count
    return 0.0, 0
