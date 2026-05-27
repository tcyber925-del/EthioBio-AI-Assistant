from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.models import NotificationPreference
from src.database.session import get_session
from src.main import app

USER_ID = str(uuid4())


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    return session


@pytest.fixture(autouse=True)
def override_deps(mock_session):
    app.dependency_overrides[get_session] = lambda: mock_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_preferences_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/notifications/preferences/{USER_ID}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_preferences(mock_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            f"/notifications/preferences/{USER_ID}",
            json={
                "email": "test@example.com",
                "digest_frequency": "daily",
                "milestone_alerts": True,
                "review_reminders": False,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == USER_ID
    assert data["email"] == "test@example.com"
    assert data["digest_frequency"] == "daily"
    assert not data["email_verified"]


@pytest.mark.asyncio
async def test_update_preferences(mock_session):
    existing = NotificationPreference(
        user_id=USER_ID,
        email="old@example.com",
        email_verified=True,
        digest_frequency="never",
        milestone_alerts=True,
        review_reminders=True,
    )
    mock_session.execute.return_value.scalar_one_or_none.return_value = existing

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            f"/notifications/preferences/{USER_ID}",
            json={
                "email": "new@example.com",
                "digest_frequency": "weekly",
                "milestone_alerts": False,
                "review_reminders": True,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == USER_ID
    assert data["email"] == "new@example.com"
    assert data["digest_frequency"] == "weekly"
    assert not data["email_verified"]


@pytest.mark.asyncio
async def test_send_verification(mock_session):
    prefs = NotificationPreference(user_id=USER_ID, email="test@example.com")
    mock_session.execute.return_value.scalar_one_or_none.return_value = prefs

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/notifications/preferences/{USER_ID}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == prefs.verification_code
    assert prefs.verification_expires is not None


@pytest.mark.asyncio
async def test_confirm_verification(mock_session):
    prefs = NotificationPreference(
        user_id=USER_ID,
        email="test@example.com",
        verification_code="abc123",
    )
    mock_session.execute.return_value.scalar_one_or_none.return_value = prefs

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/notifications/preferences/{USER_ID}/verify/abc123")
    assert resp.status_code == 200
    assert prefs.email_verified
    assert prefs.verification_code is None


@pytest.mark.asyncio
async def test_confirm_verification_invalid_code(mock_session):
    prefs = NotificationPreference(
        user_id=USER_ID,
        email="test@example.com",
        verification_code="abc123",
    )
    mock_session.execute.return_value.scalar_one_or_none.return_value = prefs

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(f"/notifications/preferences/{USER_ID}/verify/wrong")
    assert resp.status_code == 400
