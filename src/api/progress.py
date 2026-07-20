import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.parent_summary import ParentSummaryAgent
from src.agents.student_progress import StudentProgressAgent
from src.database.models import (
    ParentSummary,
    ProgressRecord,
    Question,
    QuizAttempt,
    StudentProfile,
    User,
)
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.progress import (
    ParentSummaryRequest,
    ParentSummaryResponse,
    ProgressRequest,
    ProgressResponse,
)
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()

router = APIRouter(prefix="/progress", tags=["Progress"])


async def _stream_events(
    queue: asyncio.Queue[TokenChunk | None],
    task: asyncio.Task,
) -> AsyncGenerator[str, None]:
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if chunk.error:
                yield f"data: {chunk.model_dump_json()}\n\n"
                break
            yield f"data: {chunk.model_dump_json()}\n\n"
            if chunk.done:
                break
        if task.done() and (exc := task.exception()):
            yield f"data: {TokenChunk(delta='', done=True, error=str(exc)).model_dump_json()}\n\n"
    except Exception as e:
        yield f"data: {TokenChunk(delta='', done=True, error=str(e)).model_dump_json()}\n\n"


@router.get("/student/{student_id}")
async def get_student_profile(student_id: UUID, session: AsyncSession = Depends(get_session)):
    try:
        user = await session.get(User, student_id)
        if not user:
            raise HTTPException(status_code=404, detail="Student not found")

        attempt_count = await session.scalar(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == student_id)
        )

        avg_score_result = await session.execute(
            select(func.avg(QuizAttempt.score)).where(QuizAttempt.user_id == student_id)
        )
        avg_score = avg_score_result.scalar()

        weak_topics = []
        wrong_attempts = await session.execute(
            select(Question.topic)
            .join(QuizAttempt, QuizAttempt.quiz_id == Question.quiz_id)
            .where(QuizAttempt.user_id == student_id, QuizAttempt.completed)
        )
        wrong_topics = wrong_attempts.scalars().all()
        if wrong_topics:
            from collections import Counter

            weak_topics = [topic for topic, _ in Counter(wrong_topics).most_common(5)]

        return {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "role": user.role.value if user.role else "student",
            "language_preference": user.language_preference or "en",
            "grade_level": user.grade_level,
            "quiz_attempts": attempt_count or 0,
            "avg_score": round(float(avg_score), 1) if avg_score else None,
            "weak_areas": weak_topics,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("student_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/student/{student_id}")
async def get_student_progress(
    student_id: UUID, request: ProgressRequest, session: AsyncSession = Depends(get_session)
):
    if request.stream:
        return await _handle_progress_stream(student_id, request, session)

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

        result = await agent.analyze_progress(record_list, profile)
        return ProgressResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("progress_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_progress_stream(
    student_id: UUID,
    request: ProgressRequest,
    session: AsyncSession,
) -> StreamingResponse:
    router_llm = ModelRouter()
    agent = StudentProgressAgent(llm_router=router_llm)

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    task = asyncio.create_task(_compute_progress_data(agent, student_id, request, session, queue))

    return StreamingResponse(
        _stream_events(queue, task),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _compute_progress_data(
    agent: StudentProgressAgent,
    student_id: UUID,
    request: ProgressRequest,
    session: AsyncSession,
    queue: asyncio.Queue[TokenChunk | None],
):
    try:
        profile = await session.get(StudentProfile, student_id)
        if not profile:
            queue.put_nowait(TokenChunk(delta="", done=True, error="Student profile not found"))
            return

        since = datetime.now(timezone.utc) - timedelta(days=request.days)
        records = await session.execute(
            select(ProgressRecord).where(
                ProgressRecord.student_id == student_id,
                ProgressRecord.recorded_at >= since,
            )
        )
        record_list = records.scalars().all()

        result = await agent.analyze_progress(record_list, profile)
        queue.put_nowait(TokenChunk(delta=json.dumps(result), node="progress", done=True))
    except Exception as e:
        logger.error("progress_stream_error", error=str(e))
        queue.put_nowait(TokenChunk(delta="", done=True, error=str(e)))


@router.post("/parent-summary")
async def generate_parent_summary(
    request: ParentSummaryRequest, session: AsyncSession = Depends(get_session)
):
    if request.stream:
        return await _handle_parent_summary_stream(request, session)

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


async def _handle_parent_summary_stream(
    request: ParentSummaryRequest,
    session: AsyncSession,
) -> StreamingResponse:
    router_llm = ModelRouter()
    agent = ParentSummaryAgent(llm_router=router_llm)

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    task = asyncio.create_task(
        _compute_parent_summary(agent, request, session, queue)
    )

    return StreamingResponse(
        _stream_events(queue, task),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _compute_parent_summary(
    agent: ParentSummaryAgent,
    request: ParentSummaryRequest,
    session: AsyncSession,
    queue: asyncio.Queue[TokenChunk | None],
):
    try:
        student = await session.get(User, request.student_id)
        if not student:
            queue.put_nowait(TokenChunk(delta="", done=True, error="Student not found"))
            return

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
            token_queue=queue,
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
    except Exception as e:
        logger.error("parent_summary_stream_error", error=str(e))
        queue.put_nowait(TokenChunk(delta="", done=True, error=str(e)))
