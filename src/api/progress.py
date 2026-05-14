from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from src.database.session import get_session
from src.database.models import ProgressRecord, StudentProfile, ParentSummary, User, UserRole
from src.schemas.progress import (
    ProgressRequest, ProgressResponse,
    ParentSummaryRequest, ParentSummaryResponse,
)
from src.agents.student_progress import StudentProgressAgent
from src.agents.parent_summary import ParentSummaryAgent
from src.llm.router import ModelRouter
from datetime import datetime, timezone, timedelta
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/progress", tags=["Progress"])


@router.post("/student/{student_id}", response_model=ProgressResponse)
async def get_student_progress(student_id: UUID, request: ProgressRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter()
    agent = StudentProgressAgent(llm_router=router_llm)

    try:
        profile = await session.get(StudentProfile, student_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")

        since = datetime.now(timezone.utc) - timedelta(days=request.days)
        records = await session.execute(
            select(ProgressRecord).where(
                ProgressRecord.student_id == student_id,
                ProgressRecord.recorded_at >= since,
            )
        )
        record_list = records.scalars().all()

        result = agent.analyze_progress(record_list, profile)
        return ProgressResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("progress_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parent-summary", response_model=ParentSummaryResponse)
async def generate_parent_summary(request: ParentSummaryRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter()
    agent = ParentSummaryAgent(llm_router=router_llm)

    try:
        student = await session.get(User, request.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        profile = await session.get(StudentProfile, request.student_id)

        week_end = datetime.now(timezone.utc)
        week_start = week_end - timedelta(days=7)

        records = await session.execute(
            select(ProgressRecord).where(
                ProgressRecord.student_id == request.student_id,
                ProgressRecord.recorded_at >= week_start,
            )
        )
        record_list = records.scalars().all()

        result = await agent.generate_summary(
            student_name=f"Student {student.telegram_id}",
            grade_level=student.grade_level,
            records=record_list,
            profile=profile,
            week_start=week_start,
            week_end=week_end,
            language=request.language,
            session=session,
        )

        db_summary = ParentSummary(
            parent_id=request.parent_id,
            student_id=request.student_id,
            summary_text=result["summary_text"],
            summary_amharic=result.get("summary_amharic"),
            week_start=week_start,
            week_end=week_end,
            is_low_performance_warning=result.get("is_low_performance_warning", False),
            language=request.language,
        )
        session.add(db_summary)
        await session.commit()

        return ParentSummaryResponse(
            summary_text=result["summary_text"],
            summary_amharic=result.get("summary_amharic"),
            week_start=week_start,
            week_end=week_end,
            is_low_performance_warning=result.get("is_low_performance_warning", False),
        )
    except Exception as e:
        await session.rollback()
        logger.error("parent_summary_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
