"""Tests for OAuth (Google) login flow.

Covers: start flow (state+PKCE), open-redirect rejection, callback validation,
token exchange failure, user lookup/creation, account-linking conflicts,
session creation via claim, and id_token verification (real RSA/JWK).
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt
from sqlalchemy import func, select

from src.config import settings
from src.database.models import OAuthAccount, User, UserRole
from src.database.session import get_session
from src.main import app

PROVIDER = "google"
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
LOGIN_ROUTE = f"/auth/oauth/{PROVIDER}/login"
CALLBACK_ROUTE = f"/auth/oauth/{PROVIDER}/callback"
STATE = "state-abc"


class FakeRedis:
    """In-memory fake of the subset of Redis used by the OAuth flow."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.touched: list[str] = []

    async def setex(self, key: str, ttl: int, value: str):
        self.touched.append(key)
        self.store[key] = value

    async def get(self, key: str):
        return self.store.get(key)

    async def delete(self, key: str):
        self.store.pop(key, None)

    async def sadd(self, key: str, value: str):
        self.store[key] = value

    async def srem(self, key: str, value: str):
        self.store.pop(key, None)

    async def smembers(self, key: str) -> set:
        return set()


@pytest_asyncio.fixture
async def db(db_session):
    """Real sqlite session wired into the app via dependency override."""
    app.dependency_overrides[get_session] = lambda: db_session
    yield db_session
    app.dependency_overrides.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_state(redis: FakeRedis, link: bool = False) -> dict:
    record = {
        "provider": PROVIDER,
        "verifier": "aG9wZWxlc3NseS1sb25nLXJhbmRvbS12ZXJpZmllci12YWx1ZQ",
        "redirect": "/classroom",
        "link": link,
    }
    redis.store[f"oauth_state:{PROVIDER}:{STATE}"] = json.dumps(record)
    return record


def _claims(sub="google-user-123", email="learner@example.com", email_verified=True):
    return {"sub": sub, "email": email, "email_verified": email_verified}


def _tokens():
    return {"id_token": "idtok", "access_token": "acctok"}


_EXCHANGE_DEFAULT = object()


async def _callback(redis, params: dict | None = None, claims=None, exchange=_EXCHANGE_DEFAULT):
    """Drive the callback endpoint. By default patches provider calls so the
    flow reaches user resolution; pass exchange=None to simulate an exchange
    failure."""
    from contextlib import ExitStack

    if exchange is _EXCHANGE_DEFAULT:
        exchange = _tokens()
    merged = {"code": "google-code", "state": STATE}
    merged.update(params or {})
    managers = [
        patch("src.api.oauth.get_redis", return_value=redis),
        patch("src.api.oauth._exchange_code_for_tokens", new=AsyncMock(return_value=exchange)),
    ]
    if claims is not None:
        managers.append(patch("src.api.oauth._verify_google_id_token", return_value=claims))
    with ExitStack() as stack:
        for manager in managers:
            stack.enter_context(manager)
        async with _client() as client:
            return await client.get(CALLBACK_ROUTE, params=merged)


# ---------------------------------------------------------------------------
# /auth/oauth/<provider>/login — starts the authorization flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_redirects_to_provider_with_state_and_pkce(db, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("src.config.settings.oauth_google_client_id", "google-id-123")

    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.get(LOGIN_ROUTE, params={"redirect": "/classroom"})

    assert response.status_code in (302, 307), response.text
    parts = urlparse(response.headers["location"])
    assert parts.scheme == "https"
    assert parts.netloc == "accounts.google.com"
    query = parse_qs(parts.query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["google-id-123"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"][0].split()[:2] == ["openid", "email"]
    assert query["redirect_uri"][0] == (
        f"{settings.api_base_url.rstrip('/')}/auth/oauth/google/callback"
    )
    assert query["state"], "state must be present"
    assert any(k.startswith(f"oauth_state:{PROVIDER}:") for k in redis.touched)


@pytest.mark.asyncio
async def test_login_code_challenge_matches_stored_verifier(db, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("src.config.settings.oauth_google_client_id", "id")

    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.get(LOGIN_ROUTE)

    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query["state"][0]
    record = json.loads(redis.store[f"oauth_state:{PROVIDER}:{state}"])
    import hashlib

    challenge = hashlib.sha256(record["verifier"].encode()).digest()
    expected = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()
    assert query["code_challenge"][0] == expected


@pytest.mark.asyncio
async def test_login_rejects_open_redirect_targets(db, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("src.config.settings.oauth_google_client_id", "id")

    for bad in [
        "https://evil.example.com/",
        "//evil.example.com/path",
        "/\\evil.example.com",
    ]:
        with patch("src.api.oauth.get_redis", return_value=redis):
            async with _client() as client:
                response = await client.get(LOGIN_ROUTE, params={"redirect": bad})
        assert response.status_code == 400, f"redirect={bad!r} accepted"
        assert f"oauth_state:{PROVIDER}:" not in "".join(redis.touched)


@pytest.mark.asyncio
async def test_login_unknown_provider_returns_404(db):
    redis = FakeRedis()
    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.get("/auth/oauth/github/login")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_login_unconfigured_provider_returns_400(db, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("src.config.settings.oauth_google_client_id", "")
    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.get(LOGIN_ROUTE)
    assert response.status_code == 400
    assert "not_configured" in response.text


# ---------------------------------------------------------------------------
# Callback — state validation and provider errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_with_invalid_state_redirects_to_error(db):
    redis = FakeRedis()
    response = await _callback(redis, {"state": "forged-state", "code": "abc"})
    assert response.status_code in (302, 307)
    assert "oauth_error=invalid_state" in response.headers["location"]
    assert response.headers["location"].startswith("http://localhost:3000")


@pytest.mark.asyncio
async def test_callback_denied_authorization_redirects_to_login(db):
    redis = FakeRedis()
    _seed_state(redis)
    response = await _callback(redis, {"error": "access_denied"})
    assert response.status_code in (302, 307)
    assert "oauth_error=access_denied" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_state_is_single_use(db):
    redis = FakeRedis()
    _seed_state(redis)
    first = await _callback(redis, claims=_claims(email="u1@example.com"))
    second = await _callback(redis, claims=_claims(email="u1@example.com"))
    assert first.status_code in (302, 307)
    assert "ticket=" in first.headers["location"]
    assert second.status_code in (302, 307)
    assert "error=invalid_state" in second.headers["location"] or (
        "ticket=" not in second.headers["location"]
    )


# ---------------------------------------------------------------------------
# Callback — token exchange and profile claims
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_exchange_failure_redirects(db):
    redis = FakeRedis()
    _seed_state(redis)
    response = await _callback(redis, {"code": "bad-code"}, exchange=None)
    assert "error=token_exchange" in response.headers["location"]


@pytest.mark.asyncio
async def test_callback_unverified_email_redirects(db):
    redis = FakeRedis()
    _seed_state(redis)
    response = await _callback(redis, claims=_claims(email_verified=False))
    assert "error=unverified_email" in response.headers["location"]


# ---------------------------------------------------------------------------
# Callback — user lookup / creation / linking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_new_user_creates_user_and_oauth_account(db):
    redis = FakeRedis()
    _seed_state(redis)
    response = await _callback(redis, claims=_claims(email="new@example.com"))

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "ticket=" in location
    assert "error=" not in location

    ticket_id = parse_qs(urlparse(location).query)["ticket"][0]
    ticket = json.loads(redis.store[f"oauth_ticket:{ticket_id}"])
    assert ticket["user_id"]

    user = await db.scalar(select(User).where(User.email == "new@example.com"))
    assert user is not None
    assert user.role == UserRole.teacher
    oauth_row = await db.scalar(select(OAuthAccount).where(OAuthAccount.provider == PROVIDER))
    assert oauth_row.user_id == user.id
    assert oauth_row.provider_user_id == "google-user-123"


@pytest.mark.asyncio
async def test_callback_existing_oauth_identity_reuses_user(db):
    redis = FakeRedis()
    _seed_state(redis)
    existing = User(email="same@example.com", role=UserRole.teacher, is_active=True)
    db.add(existing)
    await db.flush()
    db.add(OAuthAccount(user_id=existing.id, provider=PROVIDER, provider_user_id="google-user-123"))
    await db.commit()

    response = await _callback(redis, claims=_claims(email="same@example.com"))

    assert "ticket=" in response.headers["location"]
    ticket_id = urlparse(response.headers["location"]).query.split("ticket=")[1].split("&")[0]
    ticket = json.loads(redis.store[f"oauth_ticket:{ticket_id}"])
    assert ticket["user_id"] == str(existing.id)
    assert await db.scalar(select(func.count(User.id))) == 1


@pytest.mark.asyncio
async def test_callback_email_conflict_without_link_redirects(db):
    redis = FakeRedis()
    _seed_state(redis)
    existing = User(email="taken@example.com", role=UserRole.teacher, is_active=True)
    db.add(existing)
    await db.commit()

    response = await _callback(
        redis, claims=_claims(sub="brand-new-provider-id", email="taken@example.com")
    )

    assert "error=email_conflict" in response.headers["location"]
    assert (
        await db.scalar(select(OAuthAccount).where(OAuthAccount.user_id == existing.id))
    ) is None


@pytest.mark.asyncio
async def test_callback_link_mode_attaches_to_current_user(db):
    from src.api.oauth import _optional_current_user

    redis = FakeRedis()
    _seed_state(redis, link=True)
    me = User(email="me@example.com", role=UserRole.teacher, is_active=True)
    db.add(me)
    await db.commit()
    app.dependency_overrides[_optional_current_user] = lambda: me

    response = await _callback(redis, claims=_claims(email="me@example.com"))

    app.dependency_overrides.pop(_optional_current_user, None)
    assert "ticket=" in response.headers["location"]
    row = await db.scalar(select(OAuthAccount).where(OAuthAccount.user_id == me.id))
    assert row is not None
    assert row.provider_user_id == "google-user-123"


# ---------------------------------------------------------------------------
# Claim — create the application session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_creates_session_and_returns_token(db):
    redis = FakeRedis()
    user = User(email="claim@example.com", role=UserRole.teacher, is_active=True)
    db.add(user)
    await db.commit()
    redis.store["oauth_ticket:tt-123"] = json.dumps(
        {"user_id": str(user.id), "redirect": "/classroom"}
    )

    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.post("/auth/oauth/claim", json={"ticket": "tt-123"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["redirect"] == "/classroom"
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "refresh_token" in set_cookie


@pytest.mark.asyncio
async def test_claim_rejects_unknown_ticket(db):
    redis = FakeRedis()
    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            response = await client.post("/auth/oauth/claim", json={"ticket": "ghost"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_ticket_is_single_use(db):
    redis = FakeRedis()
    user = User(email="once@example.com", role=UserRole.teacher, is_active=True)
    db.add(user)
    await db.commit()
    redis.store["oauth_ticket:tt-single"] = json.dumps({"user_id": str(user.id)})

    with patch("src.api.oauth.get_redis", return_value=redis):
        async with _client() as client:
            first = await client.post("/auth/oauth/claim", json={"ticket": "tt-single"})
            second = await client.post("/auth/oauth/claim", json={"ticket": "tt-single"})

    assert first.status_code == 200
    assert second.status_code == 401


# ---------------------------------------------------------------------------
# id_token verification — real RSA/JWK, no mocks
# ---------------------------------------------------------------------------


def _make_rsa_jwks(kid: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub = key.public_key().public_numbers()
    n = pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")
    e = pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kid,
                "n": base64.urlsafe_b64encode(n).rstrip(b"=").decode(),
                "e": base64.urlsafe_b64encode(e).rstrip(b"=").decode(),
            }
        ]
    }
    return pem, jwks


def _signed_token(pem, kid, iss="https://accounts.google.com", aud="google-id", ttl_hours=1, sub="g"):
    claims = {
        "iss": iss,
        "aud": aud,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).timestamp()),
        "sub": sub,
        "email": "ok@example.com",
        "email_verified": True,
    }
    return jose_jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def test_verify_id_token_accepts_valid_google_token():
    from src.api.oauth import _verify_google_id_token

    pem, jwks = _make_rsa_jwks("kid1")
    token = _signed_token(pem, "kid1", sub="g-user-1")
    result = _verify_google_id_token(token, "google-id", jwks=jwks)
    assert result["sub"] == "g-user-1"


def test_verify_id_token_rejects_wrong_audience():
    from src.api.oauth import _verify_google_id_token

    pem, jwks = _make_rsa_jwks("kid2")
    token = _signed_token(pem, "kid2", aud="other-client")
    with pytest.raises(ValueError, match="id_token"):
        _verify_google_id_token(token, "google-id", jwks=jwks)


def test_verify_id_token_rejects_expired():
    from src.api.oauth import _verify_google_id_token

    pem, jwks = _make_rsa_jwks("kid3")
    token = _signed_token(pem, "kid3", ttl_hours=-1)
    with pytest.raises(ValueError, match="id_token"):
        _verify_google_id_token(token, "google-id", jwks=jwks)


def test_verify_id_token_rejects_wrong_issuer():
    from src.api.oauth import _verify_google_id_token

    pem, jwks = _make_rsa_jwks("kid4")
    token = _signed_token(pem, "kid4", iss="https://evil.example.com")
    with pytest.raises(ValueError, match="id_token"):
        _verify_google_id_token(token, "google-id", jwks=jwks)
