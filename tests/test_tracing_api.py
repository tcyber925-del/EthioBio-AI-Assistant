from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.tracing import get_trace_repository
from src.main import app

MOCK_TRACE = {
    "trace_id": "trace_test",
    "start_time": datetime.now(timezone.utc).isoformat(),
    "end_time": None,
    "status": "completed",
    "error": None,
    "user_message": "hello",
    "response": "world",
    "user_id": None,
    "grade_level": 8,
    "language": "en",
    "intent": "tutor",
    "nodes_visited": ["orchestrator"],
    "node_timings": {},
    "metadata": {},
    "duration_ms": 100.0,
}


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_trace = AsyncMock(return_value=MOCK_TRACE)
    repo.list_traces = AsyncMock(return_value=([], 0))
    repo.delete_trace = AsyncMock(return_value=True)
    return repo


@pytest.fixture
async def client(mock_repo):
    app.dependency_overrides[get_trace_repository] = lambda: mock_repo
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_trace_detail(client, mock_repo):
    response = await client.get("/traces/trace_test")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace_test"
    assert data["user_message"] == "hello"
    mock_repo.get_trace.assert_awaited_once_with("trace_test")


@pytest.mark.asyncio
async def test_get_nonexistent_trace(client, mock_repo):
    mock_repo.get_trace = AsyncMock(return_value=None)
    response = await client.get("/traces/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_traces(client, mock_repo):
    mock_repo.list_traces = AsyncMock(return_value=(
        [{
            "trace_id": "t1",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "status": "completed",
            "error": None,
            "user_message": "q",
            "response": "a",
            "user_id": None,
            "grade_level": 8,
            "language": "en",
            "intent": "tutor",
            "nodes_visited": [],
            "node_timings": {},
            "metadata": {},
            "duration_ms": 50.0,
        }],
        1,
    ))
    response = await client.get("/traces?status=completed&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["traces"]) == 1
    assert data["total"] == 1
    assert data["limit"] == 10


@pytest.mark.asyncio
async def test_delete_trace(client, mock_repo):
    response = await client.delete("/traces/trace_test")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert response.json()["trace_id"] == "trace_test"
    mock_repo.delete_trace.assert_awaited_once_with("trace_test")


@pytest.mark.asyncio
async def test_delete_nonexistent_trace(client, mock_repo):
    mock_repo.delete_trace = AsyncMock(return_value=False)
    response = await client.delete("/traces/nonexistent")
    assert response.status_code == 404
