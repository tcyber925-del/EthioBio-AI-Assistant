# Track 1 — Auth, Rate Limiting, Error Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden authentication (cookie-based JWT, refresh tokens, API key auth), add global rate limiting, and eliminate silent error swallowing.

**Architecture:** Cookie-based JWT replaces localStorage-based auth. Refresh tokens stored in Redis with rotation. Global rate limiting middleware replaces `/chat`-only limiter. `except: pass` patterns replaced with structured logging and specific exception types.

**Tech Stack:** FastAPI, Redis, PyJWT, httpx, structlog

---

### Task 1: Add structured error base class

**Files:**
- Create: `src/core/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from src.core.errors import AppError, AuthError, RateLimitError


def test_app_error_serialization():
    err = AppError(code="test_error", detail="Something broke", status=400, context={"key": "val"})
    d = err.to_dict()
    assert d["error"]["code"] == "test_error"
    assert d["error"]["detail"] == "Something broke"
    assert err.status == 400


def test_auth_error_subclass():
    err = AuthError("token_expired", "Token expired")
    assert err.status == 401
    assert err.code == "auth_token_expired"


def test_rate_limit_error_subclass():
    err = RateLimitError("chat", 30)
    assert err.status == 429
    assert "rate_limit_exceeded" in err.code
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_errors.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/errors.py
from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        status: int = 500,
        context: dict[str, Any] | None = None,
    ):
        self.code = code
        self.detail = detail
        self.status = status
        self.context = context or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "detail": self.detail, **self.context}}


class AuthError(AppError):
    def __init__(self, subtype: str, detail: str, context: dict[str, Any] | None = None):
        super().__init__(code=f"auth_{subtype}", detail=detail, status=401, context=context)


class RateLimitError(AppError):
    def __init__(self, tier: str, retry_after: int):
        super().__init__(
            code="rate_limit_exceeded",
            detail=f"Rate limit exceeded for tier '{tier}'",
            status=429,
            context={"tier": tier, "retry_after": retry_after},
        )


class NotFoundError(AppError):
    def __init__(self, subtype: str, detail: str):
        super().__init__(code=f"not_found_{subtype}", detail=detail, status=404)


class ConflictError(AppError):
    def __init__(self, subtype: str, detail: str):
        super().__init__(code=f"conflict_{subtype}", detail=detail, status=409)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_errors.py -v`
Expected: PASS

- [ ] **Step 5: Register exception handlers in main.py**

```python
# In src/main.py, add before app.include_router calls
from src.core.errors import AppError


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status, content=exc.to_dict())


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error", path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "detail": "An unexpected error occurred"}},
    )
```

- [ ] **Step 6: Commit**

```bash
git add src/core/errors.py tests/test_errors.py src/main.py
git commit -m "feat: add structured AppError base class with exception handlers"
```

---

### Task 2: Cookie-based JWT auth

**Files:**
- Modify: `src/api/auth.py`
- Modify: `src/config.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Add refresh token fields to config**

```python
# In src/config.py, replace existing jwt fields:
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    internal_api_key: str = ""
```

- [ ] **Step 2: Add startup guard for default JWT secret**

Edit `src/guardrails/startup.py` to raise `SystemExit` instead of warning:

```python
    if settings.jwt_secret in ("change-me-jwt-secret", "dev-jwt-secret"):
        raise SystemExit(
            "FATAL: JWT_SECRET is set to a default value. "
            "Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
```

- [ ] **Step 3: Rewrite auth.py with cookie-based auth + refresh tokens + specific JWT errors**

Replace `src/api/auth.py`:

```python
import random
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import APIKeyHeader
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.errors import AuthError, ConflictError, NotFoundError
from src.database.models import KnowledgeObject, LessonPlan, QuizAttempt, User, UserRole
from src.database.session import get_session
from src.redis_client import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Auth"])

COOKIE_ACCESS = "access_token"
COOKIE_REFRESH = "refresh_token"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str
    role: str = "teacher"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class OtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    telegram_id: int


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    telegram_id: int
    otp: str


class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _create_refresh_token(user_id: str) -> tuple[str, str]:
    token_id = secrets.token_urlsafe(32)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": user_id, "jti": token_id, "exp": expire, "type": "refresh"}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, token_id


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None):
    response.set_cookie(
        key=COOKIE_ACCESS,
        value=access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key=COOKIE_REFRESH,
            value=refresh_token,
            httponly=True,
            secure=not settings.debug,
            samesite="strict",
            max_age=settings.refresh_token_expire_days * 86400,
            path="/auth/refresh",
        )


def _clear_auth_cookies(response: Response):
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/auth/refresh")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True, "require_exp": True},
        )
        if payload.get("type") != "access":
            raise AuthError("invalid_token", "Token is not an access token")
        return payload
    except ExpiredSignatureError:
        raise AuthError("token_expired", "Access token has expired")
    except JWTError:
        raise AuthError("invalid_token", "Token is malformed or invalid")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get(COOKIE_ACCESS)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise AuthError("missing_token", "Authentication required")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("invalid_payload", "Token missing subject")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("user_inactive", "User not found or inactive")
    return user


@router.post("/register")
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ConflictError("email", "Email already registered")

    role_value = body.role
    if role_value not in ("teacher", "admin", "parent", "student"):
        role_value = "teacher"

    user = User(
        email=body.email,
        password_hash=_hash_password(body.password),
        role=UserRole(role_value),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    access_token = _create_access_token(str(user.id), user.role.value)
    refresh_token, refresh_jti = _create_refresh_token(str(user.id))

    redis_conn = await get_redis()
    await redis_conn.setex(f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id))

    response = Response(status_code=201)
    _set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/token")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise AuthError("invalid_credentials", "Invalid email or password")
    if not _verify_password(body.password, user.password_hash):
        raise AuthError("invalid_credentials", "Invalid email or password")
    if not user.is_active:
        raise AuthError("user_inactive", "Account is inactive")

    access_token = _create_access_token(str(user.id), user.role.value)
    refresh_token, refresh_jti = _create_refresh_token(str(user.id))

    redis_conn = await get_redis()
    await redis_conn.setex(f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id))

    response = Response(status_code=200)
    _set_auth_cookies(response, access_token, refresh_token)
    return response


@router.post("/refresh")
async def refresh_token(request: Request, session: AsyncSession = Depends(get_session)):
    refresh_token_str = request.cookies.get(COOKIE_REFRESH)
    if not refresh_token_str:
        raise AuthError("missing_refresh", "Refresh token required")

    try:
        payload = jwt.decode(
            refresh_token_str,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True, "require_exp": True},
        )
    except ExpiredSignatureError:
        raise AuthError("refresh_expired", "Refresh token has expired, please log in again")
    except JWTError:
        raise AuthError("invalid_refresh", "Refresh token is invalid")

    if payload.get("type") != "refresh":
        raise AuthError("invalid_refresh", "Token is not a refresh token")

    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise AuthError("invalid_refresh", "Refresh token missing required claims")

    redis_conn = await get_redis()
    stored = await redis_conn.get(f"refresh:{jti}")
    if stored is None:
        # Token was already used or revoked — possible token theft
        logger.warning("refresh_token_reuse_attempt", user_id=user_id, jti=jti)
        # Revoke all refresh tokens for this user
        await _revoke_all_refresh_tokens(user_id, redis_conn)
        response = Response(status_code=401)
        _clear_auth_cookies(response)
        return response

    # Consume this refresh token
    await redis_conn.delete(f"refresh:{jti}")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("user_inactive", "User not found or inactive")

    new_access = _create_access_token(str(user.id), user.role.value)
    new_refresh, new_jti = _create_refresh_token(str(user.id))
    await redis_conn.setex(f"refresh:{new_jti}", settings.refresh_token_expire_days * 86400, str(user.id))

    response = Response(status_code=200)
    _set_auth_cookies(response, new_access, new_refresh)
    return response


async def _revoke_all_refresh_tokens(user_id: str, redis_conn) -> None:
    """Revoke all refresh tokens for a user by scanning Redis keys."""
    cursor = 0
    pattern = f"refresh:*"
    while True:
        cursor, keys = await redis_conn.scan(cursor=cursor, match=pattern, count=100)
        for key in keys:
            val = await redis_conn.get(key)
            if val and val.decode() == user_id:
                await redis_conn.delete(key)
        if cursor == 0:
            break


@router.post("/logout")
async def logout(request: Request):
    response = Response(status_code=200)
    refresh_token_str = request.cookies.get(COOKIE_REFRESH)
    if refresh_token_str:
        try:
            payload = jwt.decode(
                refresh_token_str,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            if jti:
                redis_conn = await get_redis()
                await redis_conn.delete(f"refresh:{jti}")
        except JWTError:
            pass
    _clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        user_id=str(current_user.id),
        email=current_user.email or "",
        role=current_user.role.value,
    )


async def _send_telegram_otp(telegram_id: int, code: str) -> bool:
    if not settings.telegram_bot_token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": telegram_id, "text": f"Your dashboard login code: {code}\n\nThis code expires in 5 minutes.", "parse_mode": "HTML"},
            )
            r.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error("telegram_otp_send_failed", telegram_id=telegram_id, status_code=e.response.status_code)
        return False
    except httpx.RequestError as e:
        logger.error("telegram_otp_network_error", telegram_id=telegram_id, error=str(e))
        return False


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(body: OtpRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise NotFoundError("telegram_id", "User not found for this Telegram ID")

    code = f"{random.randint(100000, 999999)}"
    redis_conn = await get_redis()
    await redis_conn.setex(f"otp:{body.telegram_id}", 300, code)

    sent = await _send_telegram_otp(body.telegram_id, code)
    if not sent:
        raise AppError("otp_send_failed", "Failed to send OTP via Telegram", status=502)

    return {"success": True, "message": "OTP sent to your Telegram"}


@router.post("/verify-otp")
async def verify_otp(body: OtpVerifyRequest, session: AsyncSession = Depends(get_session)):
    redis_conn = await get_redis()
    stored = await redis_conn.get(f"otp:{body.telegram_id}")
    if not stored:
        raise AuthError("otp_expired", "OTP not requested or expired")

    if stored != body.otp:
        raise AuthError("otp_invalid", "Invalid OTP")

    await redis_conn.delete(f"otp:{body.telegram_id}")

    result = await session.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise NotFoundError("user", "User not found")

    access_token = _create_access_token(str(user.id), user.role.value)
    refresh_token, refresh_jti = _create_refresh_token(str(user.id))
    await redis_conn.setex(f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id))

    response = Response(status_code=200)
    _set_auth_cookies(response, access_token, refresh_token)
    return response


class PublicStatsResponse(BaseModel):
    active_students: int
    quizzes_completed: int
    lesson_plans_generated: int
    knowledge_assets: int
    system_status: str


@router.get("/public-stats")
async def public_stats(session: AsyncSession = Depends(get_session), redis_conn=Depends(get_redis)):
    cached = await redis_conn.get("public_stats")
    if cached:
        from json import loads
        return loads(cached)

    from json import dumps
    student_count = await session.scalar(select(func.count(User.id)).where(User.role == UserRole.student, User.is_active.is_(True)))
    quiz_count = await session.scalar(select(func.count(QuizAttempt.id)))
    lesson_count = await session.scalar(select(func.count(LessonPlan.id)))
    asset_count = await session.scalar(select(func.count(KnowledgeObject.id)))

    result = PublicStatsResponse(
        active_students=student_count or 0,
        quizzes_completed=quiz_count or 0,
        lesson_plans_generated=lesson_count or 0,
        knowledge_assets=asset_count or 0,
        system_status="healthy",
    )
    await redis_conn.setex("public_stats", 600, dumps(result.model_dump()))
    return result
```

- [ ] **Step 4: Update `get_current_user` imports in other routers**

Search for `from src.api.auth import get_current_user` in all router files and verify they still work (the function signature now takes `request: Request` instead of `authorization: str = Header(None)`).

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_auth.py -v`
Expected: All existing auth tests pass (update test assertions for cookie-based responses)

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/api/auth.py src/guardrails/startup.py
git commit -m "feat: cookie-based JWT auth with refresh token rotation"
```

---

### Task 3: Add internal API key auth for bot/cron

**Files:**
- Create: `src/api/internal.py`
- Modify: `src/main.py`
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Write the internal router**

```python
# src/api/internal.py
from fastapi import APIRouter, Depends, Header

from src.core.errors import AuthError

router = APIRouter(prefix="/internal", tags=["Internal"])


async def verify_internal_api_key(x_api_key: str = Header(...)):
    from src.config import settings

    if not settings.internal_api_key:
        raise AuthError("internal_api_key_not_configured", "Internal API key not configured")
    if x_api_key != settings.internal_api_key:
        raise AuthError("invalid_internal_api_key", "Invalid internal API key")
    return True


@router.get("/health")
async def internal_health(_: bool = Depends(verify_internal_api_key)):
    return {"status": "ok"}
```

- [ ] **Step 2: Register in main.py**

```python
# In src/main.py
from src.api.internal import router as internal_router
# ... after other router includes
app.include_router(internal_router)
```

- [ ] **Step 3: Update bot.py to send API key**

Find all `httpx.AsyncClient` usage in `src/telegram/bot.py` that calls the local API and add the header. For example, in `_stream_and_edit` and any direct API calls:

```python
headers = {}
if settings.internal_api_key:
    headers["X-API-Key"] = settings.internal_api_key
```

- [ ] **Step 4: Commit**

```bash
git add src/api/internal.py src/main.py src/telegram/bot.py src/config.py
git commit -m "feat: add internal API key auth for bot/cron routes"
```

---

### Task 4: PII redaction mode

**Files:**
- Modify: `src/guardrails/output/pii_scanner.py`
- Test: `tests/test_guardrails/test_pii_scanner.py`

- [ ] **Step 1: Write the failing test**

```python
from src.guardrails.output.pii_scanner import PIIScanner


def test_pii_redaction_email():
    scanner = PIIScanner()
    text = "Contact me at student@school.com for help"
    result = scanner.scan(text, redact=True)
    assert result.flagged
    assert "student@school.com" not in result.redacted_text
    assert "[REDACTED email]" in result.redacted_text


def test_pii_redaction_phone():
    scanner = PIIScanner()
    text = "Call 0911-123-456 for help"
    result = scanner.scan(text, redact=True)
    assert result.flagged
    assert "[REDACTED ethiopian_phone]" in result.redacted_text


def test_pii_no_redaction_when_disabled():
    scanner = PIIScanner()
    text = "Email me at test@test.com"
    result = scanner.scan(text, redact=False)
    assert result.flagged
    assert result.redacted_text == text
```

- [ ] **Step 2: Update PIIScanner with redact mode**

```python
@dataclass
class PIIScanResult:
    flagged: bool
    findings: list[dict] = field(default_factory=list)
    redacted_text: str = ""

# In scan method, add redact parameter:
    @observe_guardrail(module="pii_scanner", guardrail_type="output")
    def scan(self, text: str, redact: bool = True) -> PIIScanResult:
        if not self._enabled:
            return PIIScanResult(flagged=False, redacted_text=text)

        findings: list[dict] = []
        redacted = text

        for pattern, pii_type, description in PII_PATTERNS:
            for match in pattern.finditer(text):
                findings.append({
                    "type": pii_type,
                    "description": description,
                    "match": match.group(),
                    "position": match.start(),
                })
                if redact:
                    redacted = redacted.replace(match.group(), f"[REDACTED {pii_type}]")

        return PIIScanResult(flagged=len(findings) > 0, findings=findings, redacted_text=redacted)
```

- [ ] **Step 3: Integrate into output guardrail chain**

Find where `PIIScanner` is called in the guardrail output chain and pass `redacted_text` forward instead of original text.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_guardrails/test_pii_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/guardrails/output/pii_scanner.py tests/test_guardrails/test_pii_scanner.py
git commit -m "feat: add PII redaction mode to output guardrails"
```

---

### Task 5: Global tiered rate limiting

**Files:**
- Modify: `src/guardrails/input/rate_limiter.py`
- Modify: `src/guardrails/input/middleware.py`
- Modify: `src/main.py`

- [ ] **Step 1: Extend RateLimiter with tiered check and headers**

```python
# Add to src/guardrails/input/rate_limiter.py

from dataclasses import dataclass

@dataclass
class RateLimitRule:
    window_seconds: int
    max_requests: int

RATE_LIMIT_TIERS: dict[str, RateLimitRule] = {
    "auth":     RateLimitRule(window_seconds=60,   max_requests=5),
    "otp":      RateLimitRule(window_seconds=300,  max_requests=3),
    "chat":     RateLimitRule(window_seconds=60,   max_requests=20),
    "write":    RateLimitRule(window_seconds=60,   max_requests=30),
    "read":     RateLimitRule(window_seconds=60,   max_requests=100),
    "internal": RateLimitRule(window_seconds=60,   max_requests=500),
}


class TieredRateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._enabled = settings.rate_limit_enabled

    def resolve_tier(self, path: str, method: str) -> str:
        if path.startswith("/internal/"):
            return "internal"
        if path in ("/auth/request-otp", "/auth/verify-otp"):
            return "otp"
        if path.startswith("/auth/"):
            return "auth"
        if path.startswith("/chat/"):
            return "chat"
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return "write"
        return "read"

    async def check_and_get_headers(
        self, key: str, path: str, method: str
    ) -> tuple[bool, dict[str, str]]:
        if not self._enabled:
            return True, {}

        tier = self.resolve_tier(path, method)
        rule = RATE_LIMIT_TIERS[tier]
        now = time.time()
        window_start = now - rule.window_seconds
        redis_key = f"ratelimit:{tier}:{key}"

        await self.redis.zremrangebyscore(redis_key, 0, window_start)
        count = await self.redis.zcard(redis_key)

        remaining = max(0, rule.max_requests - count)
        reset_time = int(now + rule.window_seconds)

        if count >= rule.max_requests:
            return False, {
                "X-RateLimit-Limit": str(rule.max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(rule.window_seconds),
            }

        await self.redis.zadd(redis_key, {str(now): now})
        await self.redis.expire(redis_key, rule.window_seconds * 2)

        return True, {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": str(remaining - 1),
            "X-RateLimit-Reset": str(reset_time),
        }
```

- [ ] **Step 2: Rewrite middleware to use TieredRateLimiter app-wide**

```python
# src/guardrails/input/middleware.py
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.guardrails.input.rate_limiter import TieredRateLimiter

logger = structlog.get_logger()


def add_rate_limit_middleware(app: FastAPI, redis_client: Redis):
    limiter = TieredRateLimiter(redis_client)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health/metrics (internal infra)
        if request.url.path in ("/health", "/liveness", "/readiness", "/metrics", "/ping"):
            return await call_next(request)

        # Determine key: user_id from cookie if auth'd, else IP
        user_id = None
        if request.cookies.get("access_token"):
            try:
                from jose import jwt
                from src.config import settings
                payload = jwt.decode(
                    request.cookies["access_token"],
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_exp": False},
                )
                user_id = payload.get("sub")
            except Exception:
                pass

        ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        key = f"{user_id}:{ip}" if user_id else ip

        allowed, headers = await limiter.check_and_get_headers(key, request.url.path, request.method)
        if not allowed:
            logger.warning("rate_limit_exceeded", path=request.url.path, tier=limiter.resolve_tier(request.url.path, request.method), key=key)
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limit_exceeded", "detail": "Too many requests", "tier": limiter.resolve_tier(request.url.path, request.method)}},
                headers=headers,
            )

        response = await call_next(request)
        for h, v in headers.items():
            response.headers[h] = v
        return response

    return limiter
```

- [ ] **Step 3: Update main.py to use new middleware (remove old)**

```python
# In src/main.py, replace:
# _redis = Redis.from_url(settings.redis_url)
# add_rate_limit_middleware(app, _redis)
# with:
from src.guardrails.input.middleware import add_rate_limit_middleware

_redis = Redis.from_url(settings.redis_url)
add_rate_limit_middleware(app, _redis)
```

- [ ] **Step 4: Commit**

```bash
git add src/guardrails/input/rate_limiter.py src/guardrails/input/middleware.py src/main.py
git commit -m "feat: global tiered rate limiting middleware"
```

---

### Task 6: Eliminate `except: pass` patterns in bot.py

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Find and fix all `except: pass` and bare `except Exception` patterns**

Search for patterns in bot.py:

1. `handle_children_back` line 498 — remove, it just calls `list_children`
2. `menu` callback — replace `except: pass` with `except Exception: logger.warning(...)`
3. `handle_tutor` — replace `except: pass` with `except Exception: logger.warning(...)`
4. `handle_tutor_grade` — replace `except: pass` with `except Exception: logger.warning(...)`
5. `end_conversation` — replace `except: pass` with `except Exception: logger.warning(...)`
6. `handle_question` line 1162 — replace `except: pass` with `except Exception: logger.warning(...)`
7. `handle_question` line 1222 — replace `except: pass` with `except Exception: logger.warning(...)`
8. `reveal_command` and `hint_command` — `except Exception as e` → `logger.exception(...)` with context

Replace each instance. Example pattern:

```python
# Before:
try:
    await query.edit_message_reply_markup(reply_markup=None)
except Exception:
    pass

# After:
try:
    await query.edit_message_reply_markup(reply_markup=None)
except Exception as e:
    logger.warning("edit_reply_markup_failed", error=str(e)[:200], chat_id=update.effective_user.id)
```

- [ ] **Step 2: Run bot tests**

Run: `pytest tests/test_telegram_bot.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/telegram/bot.py
git commit -m "fix: eliminate except:pass patterns in telegram bot"
```
