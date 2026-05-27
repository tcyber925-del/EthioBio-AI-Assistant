import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QuestionAttempt

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
