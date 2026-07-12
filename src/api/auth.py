import random
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.models import User, UserRole
from src.database.session import get_session
from src.redis_client import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str
    role: str = "teacher"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


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
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _send_telegram_otp(telegram_id: int, code: str) -> None:
    if not settings.telegram_bot_token:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": telegram_id,
                    "text": f"Your dashboard login code: {code}\n\nThis code expires in 5 minutes.",
                    "parse_mode": "HTML",
                },
            )
    except Exception:
        pass


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": True, "require_exp": True},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    authorization: str = Header(None),
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

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

    token = _create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
    )


@router.post("/token", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    token = _create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserInfo(
        user_id=str(current_user.id),
        email=current_user.email or "",
        role=current_user.role.value,
    )


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
    body: OtpRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for this Telegram ID",
        )

    code = f"{random.randint(100000, 999999)}"
    redis_conn = await get_redis()
    await redis_conn.setex(f"otp:{body.telegram_id}", 300, code)

    await _send_telegram_otp(body.telegram_id, code)

    return {"success": True, "message": "OTP sent to your Telegram"}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: OtpVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    redis_conn = await get_redis()
    stored = await redis_conn.get(f"otp:{body.telegram_id}")
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP not requested or expired",
        )

    if stored != body.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP",
        )

    await redis_conn.delete(f"otp:{body.telegram_id}")

    result = await session.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    token = _create_access_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
    )
