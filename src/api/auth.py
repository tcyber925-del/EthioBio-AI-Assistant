import asyncio
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import structlog
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.errors import AppError, AuthError, ConflictError, NotFoundError
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
    await redis_conn.setex(
        f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id)
    )
    await redis_conn.sadd(f"refresh_tokens:{str(user.id)}", refresh_jti)

    response = JSONResponse(  # noqa: E501
        status_code=201, content={"access_token": access_token, "token_type": "bearer"}
    )
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
    await redis_conn.setex(
        f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id)
    )
    await redis_conn.sadd(f"refresh_tokens:{str(user.id)}", refresh_jti)

    response = JSONResponse(  # noqa: E501
        status_code=200, content={"access_token": access_token, "token_type": "bearer"}
    )
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
        logger.warning("refresh_token_reuse_attempt", user_id=user_id, jti=jti)
        await _revoke_all_refresh_tokens(user_id, redis_conn)
        msg = "Refresh token has been revoked — all sessions invalidated"
        raise AuthError("refresh_reused", msg)

    await redis_conn.delete(f"refresh:{jti}")
    await redis_conn.srem(f"refresh_tokens:{user_id}", jti)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("user_inactive", "User not found or inactive")

    new_access = _create_access_token(str(user.id), user.role.value)
    new_refresh, new_jti = _create_refresh_token(str(user.id))
    await redis_conn.setex(
        f"refresh:{new_jti}", settings.refresh_token_expire_days * 86400, str(user.id)
    )

    response = Response(status_code=200)
    _set_auth_cookies(response, new_access, new_refresh)
    return response


async def _revoke_all_refresh_tokens(user_id: str, redis_conn) -> None:
    key = f"refresh_tokens:{user_id}"
    jtis = await redis_conn.smembers(key)
    if jtis:
        await asyncio.gather(*[redis_conn.delete(f"refresh:{jti}") for jti in jtis])
        await redis_conn.delete(key)


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
            user_id = payload.get("sub")
            if jti and user_id:
                redis_conn = await get_redis()
                await redis_conn.delete(f"refresh:{jti}")
                await redis_conn.srem(f"refresh_tokens:{user_id}", jti)
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
                json={
                    "chat_id": telegram_id,
                    "text": f"Your dashboard login code: {code}\n\nThis code expires in 5 minutes.",
                    "parse_mode": "HTML",
                },
            )
            r.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error(
            "telegram_otp_send_failed",
            telegram_id=telegram_id,
            status_code=e.response.status_code,
        )
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

    code = f"{secrets.randbelow(900000) + 100000}"
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
    await redis_conn.setex(
        f"refresh:{refresh_jti}", settings.refresh_token_expire_days * 86400, str(user.id)
    )
    await redis_conn.sadd(f"refresh_tokens:{str(user.id)}", refresh_jti)

    response = JSONResponse(  # noqa: E501
        status_code=200, content={"access_token": access_token, "token_type": "bearer"}
    )
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
    student_count = await session.scalar(
        select(func.count(User.id)).where(User.role == UserRole.student, User.is_active.is_(True))
    )
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
