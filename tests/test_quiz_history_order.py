import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.quiz import list_quiz_attempts


@pytest.mark.asyncio
async def test_list_quiz_attempts_orders_by_started_at():
    attempt = SimpleNamespace(
        id=uuid.uuid4(),
        quiz_id=uuid.uuid4(),
        score=70.0,
        total=10,
        completed_at=None,
    )
    row = SimpleNamespace(
        QuizAttempt=attempt,
        title="Cell Quiz",
        topic="Cells",
        grade_level=7,
    )
    result_mock = MagicMock()
    result_mock.all.return_value = [row]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    current_user = SimpleNamespace(id=uuid.uuid4())

    await list_quiz_attempts(limit=20, session=session, current_user=current_user)

    stmt = session.execute.await_args.args[0]
    assert "started_at DESC" in str(stmt)
