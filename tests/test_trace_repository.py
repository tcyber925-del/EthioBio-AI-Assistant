from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.tracing import TraceRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return TraceRepository(lambda: mock_session)


@pytest.mark.asyncio
async def test_save_and_get_trace(repo, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(
        trace_id="trace_test",
        start_time=datetime.now(timezone.utc),
        end_time=None,
        status="running",
        error=None,
        user_message="test query",
        response=None,
        user_id=None,
        grade_level=8,
        language="en",
        intent="tutor",
        nodes_visited=["orchestrator"],
        node_timings={},
        event_metadata={},
        duration_ms=0.0,
    )
    mock_session.execute.return_value = mock_result

    trace = await repo.get_trace("trace_test")
    assert trace is not None
    assert trace["trace_id"] == "trace_test"
    assert trace["status"] == "running"


@pytest.mark.asyncio
async def test_save_trace(repo, mock_session):
    from datetime import datetime, timezone

    await repo.save_trace(
        trace_id="trace_new",
        start_time=datetime.now(timezone.utc),
        status="completed",
        user_message="hello",
        response="world",
        grade_level=10,
        language="en",
        intent="quiz",
        nodes_visited=["orchestrator", "tutor"],
        node_timings={"orchestrator": 100.0, "tutor": 500.0},
        metadata={"hallucination_rate": 0.0},
        duration_ms=600.0,
    )
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_traces_with_filters(repo, mock_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(
            trace_id="t1", start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc), status="completed",
            error=None, user_message="q1", response="a1",
            user_id=None, grade_level=8, language="en", intent="tutor",
            nodes_visited=[], node_timings={}, event_metadata={}, duration_ms=100.0,
        ),
    ]
    mock_session.execute.return_value = mock_result

    results, total = await repo.list_traces(status="completed", limit=10)
    assert len(results) == 1
    assert results[0]["trace_id"] == "t1"


@pytest.mark.asyncio
async def test_delete_trace(repo, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(trace_id="t_del")
    mock_session.execute.return_value = mock_result

    deleted = await repo.delete_trace("t_del")
    assert deleted is True
    mock_session.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_nonexistent_trace(repo, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    deleted = await repo.delete_trace("nonexistent")
    assert deleted is False
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_old_traces(repo, mock_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(trace_id="old1"),
        MagicMock(trace_id="old2"),
    ]
    mock_session.execute.return_value = mock_result

    count = await repo.cleanup_old(max_age_days=1)
    assert count == 2
    assert mock_session.delete.await_count == 2
    mock_session.flush.assert_awaited()
