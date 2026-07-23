from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.auth import (
    _create_access_token,
    _hash_password,
    _verify_password,
    decode_access_token,
)
from src.config import settings
from src.core.errors import AuthError
from src.database.models import User, UserRole
from src.database.session import get_session
from src.main import app


def test_hash_and_verify_password():
    password = "test-password-123"
    hashed = _hash_password(password)
    assert hashed != password
    assert _verify_password(password, hashed)
    assert not _verify_password("wrong-password", hashed)


def test_create_and_decode_token():
    user_id = str(uuid4())
    token = _create_access_token(user_id, "teacher")
    assert token

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "teacher"
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(AuthError):
        decode_access_token("invalid.token.here")


def test_token_expiry(monkeypatch):
    monkeypatch.setattr("src.api.auth.settings.access_token_expire_minutes", -1)
    user_id = str(uuid4())
    token = _create_access_token(user_id, "teacher")
    with pytest.raises(AuthError):
        decode_access_token(token)


def test_token_contains_role():
    user_id = str(uuid4())
    token = _create_access_token(user_id, "admin")
    payload = decode_access_token(token)
    assert payload["role"] == "admin"


def test_different_tokens_for_different_users():
    token_a = _create_access_token(str(uuid4()), "teacher")
    token_b = _create_access_token(str(uuid4()), "teacher")
    assert token_a != token_b


@pytest.mark.asyncio
async def test_otp_verify_rejects_missing_otp():
    redis_mock = _mock_redis()
    _override_session(user=None)
    transport = ASGITransport(app=app)

    # Missing telegram_id
    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/verify-otp", json={"otp": "123456"})
    app.dependency_overrides.clear()
    assert response.status_code == 422, f"Expected 422 got {response.status_code}: {response.text}"

    # Empty body
    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/verify-otp", json={})
    app.dependency_overrides.clear()
    assert response.status_code == 422, f"Expected 422 got {response.status_code}: {response.text}"


# Covered by test_request_otp_unknown_telegram_id_returns_404 (line 232)


# ---------------------------------------------------------------------------
# Integration tests for auth endpoints
# ---------------------------------------------------------------------------

_USER_ID = uuid4()


def _build_mock_session(user=None):
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.scalar = AsyncMock(return_value=None)

    def _add(instance):
        try:
            instance.id = _USER_ID
        except Exception:
            pass

    async def _refresh(instance):
        try:
            instance.id = _USER_ID
        except Exception:
            pass

    session.add.side_effect = _add
    session.refresh.side_effect = _refresh
    return session


def _build_mock_user():
    return User(
        id=_USER_ID,
        email="test@example.com",
        password_hash=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
        role=UserRole.teacher,
        is_active=True,
    )


def _mock_redis(return_val=None):
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock(return_value=return_val)
    redis_mock.delete = AsyncMock()
    redis_mock.sadd = AsyncMock()
    redis_mock.srem = AsyncMock()
    redis_mock.smembers = AsyncMock(return_value=set())
    return redis_mock


def _override_session(user=None):
    async def _mock_session():
        return _build_mock_session(user=user)
    app.dependency_overrides[get_session] = _mock_session


@pytest.mark.asyncio
async def test_register_returns_201_with_cookies():
    redis_mock = _mock_redis()
    _override_session(user=None)
    transport = ASGITransport(app=app)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/register", json={
                "email": "newuser@example.com",
                "password": "secret123",
            })
    app.dependency_overrides.clear()
    assert response.status_code == 201, f"Expected 201 got {response.status_code}: {response.text}"
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "refresh_token" in set_cookie


@pytest.mark.asyncio
async def test_login_returns_200_with_cookies():
    redis_mock = _mock_redis()
    _override_session(user=_build_mock_user())
    transport = ASGITransport(app=app)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/token", json={
                "email": "test@example.com",
                "password": "password123",
            })
    app.dependency_overrides.clear()
    assert response.status_code == 200, f"Expected 200 got {response.status_code}: {response.text}"
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "refresh_token" in set_cookie


@pytest.mark.asyncio
async def test_refresh_with_valid_cookie_returns_200():
    redis_mock = _mock_redis(return_val=str(_USER_ID))
    _override_session(user=_build_mock_user())
    transport = ASGITransport(app=app)

    from datetime import datetime, timedelta, timezone

    from jose import jwt as jose_jwt
    refresh_payload = {
        "sub": str(_USER_ID),
        "jti": "test-jti-123",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    valid_refresh = jose_jwt.encode(refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("refresh_token", valid_refresh)
            response = await client.post("/auth/refresh")
    app.dependency_overrides.clear()
    assert response.status_code == 200, f"Expected 200 got {response.status_code}: {response.text}"
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "refresh_token" in set_cookie


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401():
    redis_mock = _mock_redis()
    _override_session(user=None)
    transport = ASGITransport(app=app)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/refresh")
    app.dependency_overrides.clear()
    assert response.status_code == 401
    body = response.json()
    assert "error" in body


@pytest.mark.asyncio
async def test_logout_clears_cookies():
    redis_mock = _mock_redis()
    _override_session(user=None)
    transport = ASGITransport(app=app)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/logout")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie or "access_token=;" in set_cookie
    assert "refresh_token=" in set_cookie or "refresh_token=;" in set_cookie


@pytest.mark.asyncio
async def test_request_otp_unknown_telegram_id_returns_404():
    redis_mock = _mock_redis()
    _override_session(user=None)
    transport = ASGITransport(app=app)

    with patch("src.api.auth.get_redis", return_value=redis_mock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/request-otp", json={"telegram_id": 999999})
    app.dependency_overrides.clear()
    assert response.status_code == 404, f"Expected 404 got {response.status_code}: {response.text}"
