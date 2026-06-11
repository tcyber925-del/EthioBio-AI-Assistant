from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.api.auth import _create_access_token
from src.database.models import AgentTrace, UserRole
from src.database.session import get_session
from src.main import app


def _make_trace_metadata(**overrides) -> dict:
    base = {
        "requires_teacher_review": True,
        "safety_issues": ["profanity"],
        "safety_action": "revise",
        "user_message": "test query",
        "response": "test response",
        "intent": "tutor",
        "grade_level": 8,
        "language": "en",
        "groundedness_score": 0.3,
        "hallucination_rate": 0.15,
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_session():
    mock = AsyncMock()
    mock.scalar = AsyncMock(return_value=0)
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()

    mock_user = AsyncMock()
    mock_user.role = UserRole.admin
    mock_user.is_active = True
    mock_user.id = uuid4()
    mock_user.telegram_id = None
    mock_user.language_preference = "en"
    mock_user.grade_level = None
    mock_user.created_at = None
    mock_user.email = "admin@test.com"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0

    mock.execute = AsyncMock(return_value=mock_result)
    mock.get = AsyncMock(return_value=None)
    mock._mock_user = mock_user
    return mock


@pytest.fixture
def client(mock_session):
    app.dependency_overrides[get_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_pending_reviews_returns_200(client, mock_session):
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/review",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_resolved_reviews_returns_200(client, mock_session):
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/review?status=resolved",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resolve_trace_returns_200(client, mock_session):
    mock_trace = AsyncMock()
    mock_trace.trace_id = "test_trace_123"
    mock_trace.event_metadata = _make_trace_metadata(reviewed=False)
    mock_trace.start_time = None

    trace_result = MagicMock()
    trace_result.scalar_one_or_none.return_value = mock_trace

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = mock_session._mock_user
    auth_result.scalars.return_value.all.return_value = []
    auth_result.scalar.return_value = 0

    call_count = 0

    async def execute_side(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_result
        return trace_result

    mock_session.execute = AsyncMock(side_effect=execute_side)

    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.patch(
        "/admin/review/test_trace_123",
        json={"action": "resolve", "review_notes": "Approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "test_trace_123"
    assert data["status"] == "resolved"


@pytest.mark.asyncio
async def test_resolve_nonexistent_trace_returns_404(client, mock_session):
    trace_result = MagicMock()
    trace_result.scalar_one_or_none.return_value = None

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = mock_session._mock_user
    auth_result.scalars.return_value.all.return_value = []
    auth_result.scalar.return_value = 0

    call_count = 0

    async def execute_side(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_result
        return trace_result

    mock_session.execute = AsyncMock(side_effect=execute_side)

    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.patch(
        "/admin/review/nonexistent",
        json={"action": "resolve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_wrong_trace_returns_400(client, mock_session):
    mock_trace = AsyncMock()
    mock_trace.trace_id = "test_trace_456"
    mock_trace.event_metadata = {"requires_teacher_review": False}

    trace_result = MagicMock()
    trace_result.scalar_one_or_none.return_value = mock_trace

    auth_result = MagicMock()
    auth_result.scalar_one_or_none.return_value = mock_session._mock_user
    auth_result.scalars.return_value.all.return_value = []
    auth_result.scalar.return_value = 0

    call_count = 0

    async def execute_side(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return auth_result
        return trace_result

    mock_session.execute = AsyncMock(side_effect=execute_side)

    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.patch(
        "/admin/review/test_trace_456",
        json={"action": "resolve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_review_rejects_non_admin(client, mock_session):
    mock_session._mock_user.role = UserRole.teacher
    token = _create_access_token(str(uuid4()), "teacher")
    resp = await client.get(
        "/admin/review",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
