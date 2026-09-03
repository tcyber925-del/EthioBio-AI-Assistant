import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.clerk import verify_clerk_token
from src.core.errors import AuthError
from src.database.models import KnowledgeObject, LessonPlan, QuizAttempt, User, UserRole
from src.database.session import get_session
from src.redis_client import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Auth"])


class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str


class PublicStatsResponse(BaseModel):
    active_students: int
    quizzes_completed: int
    lesson_plans_generated: int
    knowledge_assets: int
    system_status: str


def _bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def _resolve_user(clerk_id: str, claims: dict, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    email = claims.get("email") or ""
    if email:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.clerk_id = clerk_id
            await session.commit()
            return user

    user = User(clerk_id=clerk_id, email=email or None, role=UserRole.student, is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = _bearer_token(request)
    if not token:
        raise AuthError("missing_token", "Authentication required")

    claims = await verify_clerk_token(token)
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise AuthError("invalid_payload", "Token missing subject")

    user = await _resolve_user(clerk_id, claims, session)
    if not user.is_active:
        raise AuthError("user_inactive", "User not found or inactive")
    return user


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        user_id=str(current_user.id),
        email=current_user.email or "",
        role=current_user.role.value,
    )


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
