from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agents.parent_summary import ParentSummaryAgent
from src.api.auth import get_current_user
from src.core.learning_intelligence.readiness import ReadinessService
from src.database.models import (
    ParentChild,
    ParentSummary,
    ProgressRecord,
    QuizAttempt,
    StudentMastery,
    StudentProfile,
    User,
    UserGamification,
    UserRole,
)
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.common import LanguageEnum

logger = structlog.get_logger()
router = APIRouter(prefix="/parent", tags=["Parent"])

readiness_service = ReadinessService()


class ChildSummary(BaseModel):
    student_id: UUID
    name: str
    grade_level: int | None = None
    last_active: datetime | None = None
    overall_readiness: float = 0.0


class ChildProgress(BaseModel):
    student_id: UUID
    overall_readiness: float
    mastery_heatmap: dict[str, float]
    recent_quizzes: list[dict]
    streak: int
    total_xp: int


class WeeklySummary(BaseModel):
    summary_text: str
    summary_amharic: str | None = None
    week_start: datetime
    week_end: datetime
    is_low_performance_warning: bool


def _require_parent_role(current_user: User) -> None:
    if current_user.role not in (UserRole.parent, UserRole.admin):
        raise HTTPException(status_code=403, detail="Parent access required")


async def _verify_child_ownership(
    session: AsyncSession,
    parent_id: UUID,
    student_id: UUID,
) -> User:
    result = await session.execute(
        select(ParentChild).where(
            ParentChild.parent_id == parent_id,
            ParentChild.student_id == student_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Child not found")
    child = await session.get(User, student_id)
    if not child or not child.is_active:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@router.get("/children")
async def list_children(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_parent_role(current_user)

    result = await session.execute(
        select(User)
        .join(ParentChild, ParentChild.student_id == User.id)
        .where(ParentChild.parent_id == current_user.id)
        .options(selectinload(User.student_profile))
    )
    children = list(result.scalars().all())

    summaries: list[ChildSummary] = []
    for child in children:
        overall_readiness = 0.0
        try:
            profile = await readiness_service.get_readiness(session, child.id)
            overall_readiness = profile.overall_readiness
        except Exception:
            pass

        summaries.append(
            ChildSummary(
                student_id=child.id,
                name=child.email or f"Student #{str(child.id)[:8]}",
                grade_level=child.grade_level,
                last_active=child.updated_at,
                overall_readiness=overall_readiness,
            )
        )

    return summaries


@router.get("/children/{student_id}/progress")
async def get_child_progress(
    student_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_parent_role(current_user)
    child = await _verify_child_ownership(session, current_user.id, student_id)

    readiness = await readiness_service.get_readiness(session, child.id)

    mastery_result = await session.execute(
        select(StudentMastery).where(
            StudentMastery.user_id == child.id,
        )
    )
    mastery_records = list(mastery_result.scalars().all())
    mastery_heatmap: dict[str, float] = {}
    for m in mastery_records:
        mastery_heatmap[m.topic] = m.average_score

    quiz_result = await session.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == child.id)
        .order_by(QuizAttempt.started_at.desc())
        .limit(5)
    )
    recent_quizzes = [
        {
            "quiz_id": str(q.quiz_id) if q.quiz_id else None,
            "score": q.score,
            "total": q.total,
            "created_at": (
                (q.completed_at or q.started_at).isoformat()
                if (q.completed_at or q.started_at)
                else None
            ),
        }
        for q in quiz_result.scalars().all()
    ]

    streak = 0
    total_xp = 0
    gam_result = await session.execute(
        select(UserGamification).where(UserGamification.user_id == child.id)
    )
    gam = gam_result.scalar_one_or_none()
    if gam:
        streak = gam.current_streak or 0
        total_xp = gam.total_xp or 0

    return ChildProgress(
        student_id=child.id,
        overall_readiness=readiness.overall_readiness,
        mastery_heatmap=mastery_heatmap,
        recent_quizzes=recent_quizzes,
        streak=streak,
        total_xp=total_xp,
    )


@router.get("/children/{student_id}/weekly-summary")
async def get_weekly_summary(
    student_id: UUID,
    language: LanguageEnum = LanguageEnum.EN,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_parent_role(current_user)
    child = await _verify_child_ownership(session, current_user.id, student_id)

    existing = await session.execute(
        select(ParentSummary)
        .where(
            ParentSummary.parent_id == current_user.id,
            ParentSummary.student_id == student_id,
        )
        .order_by(ParentSummary.created_at.desc())
        .limit(1)
    )
    existing_summary = existing.scalar_one_or_none()
    if existing_summary:
        week_end = existing_summary.week_end.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - week_end < timedelta(hours=24):
            return WeeklySummary(
                summary_text=existing_summary.summary_text,
                summary_amharic=existing_summary.summary_amharic,
                week_start=existing_summary.week_start,
                week_end=existing_summary.week_end,
                is_low_performance_warning=existing_summary.is_low_performance_warning,
            )

    week_end = datetime.now(timezone.utc)
    week_start = week_end - timedelta(days=7)

    profile = await session.get(StudentProfile, child.id)

    records_result = await session.execute(
        select(ProgressRecord).where(
            ProgressRecord.student_id == child.id,
            ProgressRecord.recorded_at >= week_start,
        )
    )
    record_list = list(records_result.scalars().all())

    llm_router = ModelRouter()
    agent = ParentSummaryAgent(llm_router=llm_router)

    result = await agent.generate_summary(
        student_name=child.email or f"Student #{str(child.id)[:8]}",
        grade_level=child.grade_level,
        records=record_list,
        profile=profile,
        week_start=week_start,
        week_end=week_end,
        language=language,
        session=session,
    )

    db_summary = ParentSummary(
        parent_id=current_user.id,
        student_id=child.id,
        summary_text=result["summary_text"],
        summary_amharic=result.get("summary_amharic"),
        week_start=week_start,
        week_end=week_end,
        is_low_performance_warning=result.get("is_low_performance_warning", False),
        language=language,
    )
    session.add(db_summary)
    await session.commit()

    return WeeklySummary(
        summary_text=result["summary_text"],
        summary_amharic=result.get("summary_amharic"),
        week_start=week_start,
        week_end=week_end,
        is_low_performance_warning=result.get("is_low_performance_warning", False),
    )
