from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.models import UserRole
from src.database.session import get_session
from src.main import app


@pytest.fixture
def mock_session():
    mock = AsyncMock()
    mock.scalar = AsyncMock(return_value=0)

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

    mock.execute.return_value = mock_result
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
async def test_admin_dashboard_returns_401_without_token(client):
    resp = await client.get("/admin/dashboard")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_dashboard_returns_200_with_admin_token(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_dashboard_returns_403_with_teacher_token(client, mock_session):
    from src.api.auth import _create_access_token
    mock_session._mock_user.role = UserRole.teacher
    token = _create_access_token(str(uuid4()), "teacher")
    resp = await client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_users_lists_users(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_admin_users_status_toggle(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    user_id = str(uuid4())
    mock_user_obj = AsyncMock()
    mock_user_obj.is_active = True
    mock_session.get = AsyncMock(return_value=mock_user_obj)

    resp = await client.patch(
        f"/admin/users/{user_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_admin_schools_returns_list(client, mock_session):
    from src.api.auth import _create_access_token
    token = _create_access_token(str(uuid4()), "admin")
    resp = await client.get(
        "/admin/schools",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_endpoints_reject_teacher_token(client, mock_session):
    from src.api.auth import _create_access_token
    mock_session._mock_user.role = UserRole.teacher
    token = _create_access_token(str(uuid4()), "teacher")
    for path in ["/admin/dashboard", "/admin/users", "/admin/schools", "/admin/monitoring"]:
        resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, f"{path} should return 403 for teacher"


@pytest.mark.asyncio
async def test_teacher_create_school_requires_admin(client, mock_session):
    from src.api.auth import _create_access_token
    mock_session._mock_user.role = UserRole.teacher
    token = _create_access_token(str(uuid4()), "teacher")
    resp = await client.post(
        "/teacher/schools",
        json={"name": "Test School"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
