import re
from datetime import date, datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.clerk import verify_clerk_token
from src.auth.signup_intent import (
    COOKIE_NAME,
    SELF_SERVE_ROLES,
    age_on,
    create_intent_cookie,
    verify_intent_cookie,
)
from src.config import settings
from src.core.errors import AppError, AuthError
from src.database.models import KnowledgeObject, LessonPlan, QuizAttempt, User, UserRole
from src.database.session import get_session
from src.redis_client import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["Auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str
    role_claimed: bool = False
    grade_level: int | None = None
    subject: str | None = None
    date_of_birth: str | None = None
    onboarding_completed: bool = False
    is_active: bool = True


class RoleClaimRequest(BaseModel):
    role: str


class SignupIntentRequest(BaseModel):
    """Pre-auth intent captured by the role-first signup wizard (ADR-0013)."""

    role: str
    dob: date | None = None
    tos_accepted: bool = False
    parent_email: str | None = None

    @field_validator("parent_email")
    @classmethod
    def _valid_parent_email(cls, v: str | None) -> str | None:
        if v is not None and not _EMAIL_RE.match(v):
            raise ValueError("invalid parent_email")
        return v


class OnboardingRequest(BaseModel):
    grade_level: int | None = None
    subject: str | None = None


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        user_id=str(user.id),
        email=user.email or "",
        role=user.role.value,
        role_claimed=user.role_claimed,
        grade_level=user.grade_level,
        subject=user.subject,
        date_of_birth=user.date_of_birth.isoformat() if user.date_of_birth else None,
        onboarding_completed=user.onboarding_completed_at is not None,
        is_active=user.is_active,
    )


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
    return _user_info(current_user)


@router.post("/signup-intent")
async def signup_intent(body: SignupIntentRequest, response: Response):
    """Validate the wizard's pre-auth choices and store them in a signed cookie.

    The cookie survives the OAuth redirect (same-origin) and is consumed once by
    /auth/complete-signup after the Clerk session exists.
    """
    if body.role not in SELF_SERVE_ROLES:
        raise AppError("invalid_role", "Role must be student, teacher or parent", status=400)
    if not body.tos_accepted:
        raise AppError("tos_required", "Terms of Service must be accepted", status=400)

    requires_consent = False
    if body.role == "student":
        if body.dob is None:
            raise AppError("dob_required", "Date of birth is required for learners", status=400)
        today = datetime.now(timezone.utc).date()
        if body.dob > today:
            raise AppError("dob_invalid", "Date of birth cannot be in the future", status=400)
        if age_on(body.dob, today) > 100:
            raise AppError("dob_invalid", "Date of birth is not plausible", status=400)
        if age_on(body.dob, today) < settings.min_self_consent_age:
            requires_consent = True
            if not body.parent_email:
                raise AppError(
                    "parent_email_required",
                    "A parent email is required for learners under "
                    f"{settings.min_self_consent_age}",
                    status=400,
                )
        dob = body.dob
    else:
        dob = None  # DOB is collected for learners only

    cookie = create_intent_cookie(
        role=body.role,
        dob=dob,
        tos_accepted=True,
        parent_email=body.parent_email if requires_consent else None,
    )
    response.set_cookie(
        COOKIE_NAME,
        cookie,
        max_age=settings.signup_intent_ttl_seconds,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        path="/",
    )
    return {"ok": True, "role": body.role, "requires_parental_consent": requires_consent}


@router.post("/complete-signup", response_model=UserInfo)
async def complete_signup(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Consume the signed signup-intent cookie: claim role, store DOB/ToS.

    Under-13 learners are provisioned inactive until a parent consents
    (delivery of the consent notice is a follow-up; logged here).
    """
    payload = verify_intent_cookie(request.cookies.get(COOKIE_NAME))
    if payload is None:
        raise AppError(
            "missing_signup_intent",
            "Signup session missing or expired — please restart signup",
            status=400,
        )
    user = await session.get(User, current_user.id)
    if user is None:
        raise AppError("user_not_found", "User not found", status=404)
    if user.role_claimed:
        raise AppError("role_already_claimed", "Role has already been claimed", status=409)

    user.role = UserRole(payload["role"])
    user.role_claimed = True
    if payload.get("tos"):
        user.tos_accepted_at = datetime.now(timezone.utc)
    if payload.get("dob"):
        user.date_of_birth = date.fromisoformat(payload["dob"])
    if payload.get("parent_email"):
        user.parent_email = payload["parent_email"]

    if user.date_of_birth:
        today = datetime.now(timezone.utc).date()
        if age_on(user.date_of_birth, today) < settings.min_self_consent_age:
            user.is_active = False
            logger.info(
                "parental_consent_required",
                user_id=str(user.id),
                parent_email=user.parent_email,
            )

    await session.commit()
    await session.refresh(user)
    response.delete_cookie(COOKIE_NAME, path="/")
    return _user_info(user)


@router.post("/onboarding", response_model=UserInfo)
async def onboarding(
    body: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Complete per-role onboarding; the first writer of User.grade_level."""
    user = await session.get(User, current_user.id)
    if user is None:
        raise AppError("user_not_found", "User not found", status=404)

    if user.role == UserRole.student:
        if body.grade_level is None or not (7 <= body.grade_level <= 12):
            raise AppError(
                "invalid_grade_level", "Grade level must be between 7 and 12", status=400
            )
        user.grade_level = body.grade_level
    if body.subject:
        user.subject = body.subject

    user.onboarding_completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return _user_info(user)


@router.post("/claim-role")
async def claim_role(
    body: RoleClaimRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """One-time self-declared role for Clerk-created accounts (teacher/parent/student).

    Only allowed while `role_claimed` is false, so the choice cannot be abused
    for later privilege escalation; admins are never self-assignable.
    """
    if body.role not in ("teacher", "parent", "student"):
        raise AppError("invalid_role", "Role must be teacher, parent or student", status=400)
    user = await session.get(User, current_user.id)
    if user is None:
        raise AppError("user_not_found", "User not found", status=404)
    if user.role_claimed:
        raise AppError("role_already_claimed", "Role has already been claimed", status=409)
    user.role = UserRole(body.role)
    user.role_claimed = True
    await session.commit()
    await session.refresh(user)
    return UserInfo(
        user_id=str(user.id),
        email=user.email or "",
        role=user.role.value,
        role_claimed=True,
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
