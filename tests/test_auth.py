import base64
from datetime import date
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


# --- Role-first signup wizard (ADR-0013) ---

_HEADERS = {"Authorization": "Bearer clerk-session-token"}


def _dob_for_age(age: int) -> str:
    today = date.today()
    return date(today.year - age, today.month, today.day).isoformat()


@pytest.mark.asyncio
async def test_signup_intent_teacher_sets_cookie(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/signup-intent", json={"role": "teacher", "tos_accepted": True}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"ok": True, "role": "teacher", "requires_parental_consent": False}
        cookie = resp.cookies.get("pending_signup")
        assert cookie is not None
        assert "." in cookie


@pytest.mark.asyncio
async def test_signup_intent_requires_tos(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/auth/signup-intent", json={"role": "teacher"})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_signup_intent_learner_requires_dob(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/signup-intent", json={"role": "student", "tos_accepted": True}
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_signup_intent_under13_requires_parent_email(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.post(
            "/auth/signup-intent",
            json={"role": "student", "tos_accepted": True, "dob": _dob_for_age(10)},
        )
        assert missing.status_code == 400

        ok = await client.post(
            "/auth/signup-intent",
            json={
                "role": "student",
                "tos_accepted": True,
                "dob": _dob_for_age(10),
                "parent_email": "parent@example.com",
            },
        )
        assert ok.status_code == 200
        assert ok.json()["requires_parental_consent"] is True


@pytest.mark.asyncio
async def test_complete_signup_consumes_intent(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_wizard_1", "email": "wizard@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/auth/me", headers=_HEADERS)

            intent = await client.post(
                "/auth/signup-intent",
                json={"role": "student", "tos_accepted": True, "dob": _dob_for_age(15)},
            )
            cookie = intent.cookies.get("pending_signup")

            done = await client.post(
                "/auth/complete-signup", headers=_HEADERS, cookies={"pending_signup": cookie}
            )
            assert done.status_code == 200
            body = done.json()
            assert body["role"] == "student"
            assert body["role_claimed"] is True
            assert body["date_of_birth"] == _dob_for_age(15)
            # cookie is single-use: response clears it
            assert "pending_signup" in done.headers.get("set-cookie", "")

            # replaying the consumed flow without a fresh intent fails
            again = await client.post("/auth/complete-signup", headers=_HEADERS)
            assert again.status_code == 400  # intent cookie is gone (single-use)

            from sqlalchemy import select

            result = await db_session.execute(
                select(User).where(User.email == "wizard@example.com")
            )
            user = result.scalar_one()
            assert user.tos_accepted_at is not None
            assert user.role_claimed is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_complete_signup_missing_or_tampered_intent(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_wizard_2", "email": "wizard2@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            missing = await client.post("/auth/complete-signup", headers=_HEADERS)
            assert missing.status_code == 400

            intent = await client.post(
                "/auth/signup-intent", json={"role": "parent", "tos_accepted": True}
            )
            cookie = intent.cookies.get("pending_signup")
            tampered = cookie[:-4] + ("AAAA" if not cookie.endswith("AAAA") else "BBBB")
            resp = await client.post(
                "/auth/complete-signup", headers=_HEADERS, cookies={"pending_signup": tampered}
            )
            assert resp.status_code == 400

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_complete_signup_under13_inactive(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_wizard_3", "email": "kid@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/auth/me", headers=_HEADERS)
            intent = await client.post(
                "/auth/signup-intent",
                json={
                    "role": "student",
                    "tos_accepted": True,
                    "dob": _dob_for_age(11),
                    "parent_email": "parent@example.com",
                },
            )
            done = await client.post(
                "/auth/complete-signup",
                headers=_HEADERS,
                cookies={"pending_signup": intent.cookies.get("pending_signup")},
            )
            assert done.status_code == 200

            from sqlalchemy import select

            result = await db_session.execute(
                select(User).where(User.email == "kid@example.com")
            )
            user = result.scalar_one()
            assert user.is_active is False
            assert user.parent_email == "parent@example.com"

            # account locked until consent: subsequent calls are rejected
            locked = await client.get("/auth/me", headers=_HEADERS)
            assert locked.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_onboarding_student_sets_grade_and_completion(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    transport = ASGITransport(app=app)

    async def fake_verify(token: str) -> dict:
        return {"sub": "user_onb_1", "email": "onb@example.com"}

    with patch("src.api.auth.verify_clerk_token", side_effect=fake_verify):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/auth/me", headers=_HEADERS)

            bad = await client.post("/auth/onboarding", json={"grade_level": 6}, headers=_HEADERS)
            assert bad.status_code == 400

            ok = await client.post(
                "/auth/onboarding",
                json={"grade_level": 9, "subject": "biology"},
                headers=_HEADERS,
            )
            assert ok.status_code == 200
            body = ok.json()
            assert body["grade_level"] == 9
            assert body["subject"] == "biology"
            assert body["onboarding_completed"] is True

            me = await client.get("/auth/me", headers=_HEADERS)
            assert me.json()["grade_level"] == 9
            assert me.json()["onboarding_completed"] is True

    app.dependency_overrides.clear()
