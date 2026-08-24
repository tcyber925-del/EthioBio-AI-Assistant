import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api import parent as parent_api
from src.database.models import UserRole


def _db_result(scalar=None, scalars=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    inner = MagicMock()
    inner.all.return_value = scalars or []
    r.scalars.return_value = inner
    return r


@pytest.mark.asyncio
async def test_get_child_progress_uses_real_quiz_columns(monkeypatch):
    student_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child = SimpleNamespace(id=student_id, is_active=True)
    current_user = SimpleNamespace(id=parent_id, role=UserRole.parent)
    quiz = SimpleNamespace(
        quiz_id=None,
        score=70.0,
        total=10,
        completed_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
        started_at=datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc),
    )
    gam = SimpleNamespace(current_streak=3, total_xp=420)

    session = AsyncMock()
    session.get = AsyncMock(return_value=child)
    session.execute = AsyncMock(
        side_effect=[
            _db_result(scalar=MagicMock()),
            _db_result(scalars=[SimpleNamespace(topic="Genetics", average_score=64.0)]),
            _db_result(scalars=[quiz]),
            _db_result(scalar=gam),
        ]
    )
    monkeypatch.setattr(
        parent_api.readiness_service,
        "get_readiness",
        AsyncMock(return_value=SimpleNamespace(overall_readiness=55.0)),
    )

    result = await parent_api.get_child_progress(
        student_id, session=session, current_user=current_user
    )

    assert result.student_id == student_id
    assert result.overall_readiness == 55.0
    assert result.mastery_heatmap == {"Genetics": 64.0}
    assert result.recent_quizzes[0]["score"] == 70.0
    assert result.recent_quizzes[0]["total"] == 10
    assert result.recent_quizzes[0]["created_at"] == "2026-08-21T00:00:00+00:00"
    assert result.streak == 3
    assert result.total_xp == 420
