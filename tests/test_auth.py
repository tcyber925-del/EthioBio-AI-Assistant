import base64
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt

from src.auth.clerk import verify_clerk_token
from src.core.errors import AuthError
from src.database.models import User, UserRole
from src.database.session import get_session
from src.main import app

_RSA_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_RSA_PEM = _RSA_PRIVATE.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
KID = "test-kid"


def _public_jwk() -> dict:
    pub = _RSA_PRIVATE.public_key().public_numbers()
    n_bytes = pub.n.to_bytes((pub.n.bit_length() + 7) // 8, "big")
    e_bytes = pub.e.to_bytes((pub.e.bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "kid": KID,
        "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
        "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
    }


def make_token(sub: str, issuer: str | None = None, **claims) -> str:
    payload = {"sub": sub, "iss": issuer or "https://test.clerk.accounts.dev", **claims}
    return jose_jwt.encode(payload, _RSA_PEM, algorithm="RS256", headers={"kid": KID})


def _patch_jwks(monkeypatch, key=None):
    jwks = {"keys": [key or _public_jwk()]}

    async def fake_get_jwks() -> dict:
        return jwks

    monkeypatch.setattr("src.auth.clerk._get_jwks", fake_get_jwks)


@pytest.fixture(autouse=True)
def _clerk_env(monkeypatch):
    monkeypatch.setattr("src.config.settings.clerk_frontend_api", "https://test.clerk.accounts.dev")
    _patch_jwks(monkeypatch)


@pytest.mark.asyncio
async def test_verify_valid_token():
    claims = await verify_clerk_token(make_token("user_123"))
    assert claims["sub"] == "user_123"
    assert claims["iss"] == "https://test.clerk.accounts.dev"


@pytest.mark.asyncio
async def test_verify_wrong_issuer_rejected():
    token = make_token("user_123", issuer="https://evil.example.com")
    with pytest.raises(AuthError):
        await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_verify_expired_token_rejected():
    import time

    token = make_token("user_123", exp=int(time.time()) - 60)
    with pytest.raises(AuthError):
        await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_verify_unknown_kid_rejected(monkeypatch):
    _patch_jwks(monkeypatch, key={**_public_jwk(), "kid": "other-kid"})
    with pytest.raises(AuthError):
        await verify_clerk_token(make_token("user_123"))


@pytest.mark.asyncio
async def test_verify_malformed_token_rejected():
    with pytest.raises(AuthError):
        await verify_clerk_token("not.a.jwt")


@pytest.mark.asyncio
async def test_verify_missing_sub_rejected(monkeypatch):
    with pytest.raises(AuthError):
        await verify_clerk_token(make_token(""))


@pytest.mark.asyncio
async def test_me_requires_token(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/me")
        assert resp.status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_creates_user_on_first_clerk_signin(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_new_1", "email": "new@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/auth/me", headers={"Authorization": "Bearer clerk-session-token"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["role"] == "student"
            assert body["email"] == "new@example.com"

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/auth/me", headers={"Authorization": "Bearer clerk-session-token"}
            )
            assert resp.status_code == 200
            assert resp.json()["user_id"] == body["user_id"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_me_matches_existing_user_by_email(db_session):
    db_session.add(User(email="old@example.com", role=UserRole.teacher, is_active=True))
    await db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_clerk_99", "email": "old@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/auth/me", headers={"Authorization": "Bearer clerk-session-token"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["role"] == "teacher"
            assert body["email"] == "old@example.com"

        from sqlalchemy import select

        result = await db_session.execute(select(User).where(User.email == "old@example.com"))
        user = result.scalar_one()
        assert user.clerk_id == "user_clerk_99"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_new_user_can_claim_role_once(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_claim_1", "email": "claim@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": "Bearer clerk-session-token"}

            me = await client.get("/auth/me", headers=headers)
            assert me.status_code == 200
            assert me.json()["role"] == "student"
            assert me.json()["role_claimed"] is False

            claimed = await client.post(
                "/auth/claim-role", json={"role": "teacher"}, headers=headers
            )
            assert claimed.status_code == 200
            assert claimed.json()["role"] == "teacher"
            assert claimed.json()["role_claimed"] is True

            me2 = await client.get("/auth/me", headers=headers)
            assert me2.json()["role"] == "teacher"

            again = await client.post(
                "/auth/claim-role", json={"role": "parent"}, headers=headers
            )
            assert again.status_code == 409

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_claim_role_rejects_admin(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_claim_2", "email": "claim2@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/auth/claim-role",
                json={"role": "admin"},
                headers={"Authorization": "Bearer clerk-session-token"},
            )
            assert resp.status_code == 400

    app.dependency_overrides.clear()