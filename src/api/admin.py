import asyncio
import os
import tempfile
from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.auth import get_current_user
from src.config import settings
from src.database.models import (
    AgentTrace,
    AudioRecording,
    LessonPlan,
    ModelRoutingLog,
    ParentChild,
    Question,
    Quiz,
    QuizAttempt,
    School,
    User,
    UserRole,
)
from src.database.session import get_session
from src.voice.providers import speech_registry

logger = structlog.get_logger()
router = APIRouter(prefix="/admin", tags=["Admin"])


async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/db-backup")
async def db_backup(_: User = Depends(require_admin)):
    dsn = os.environ.get("DATABASE_SYNC_URL") or settings.database_sync_url
    dump_path = os.path.join(tempfile.gettempdir(), "ethiobio_db_backup.sql")
    with open(dump_path, "wb") as out:
        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            dsn,
            "--clean",
            "--if-exists",
            "--no-owner",
            stdout=out,
            stderr=asyncio.subprocess.PIPE,
        )
        if proc.stderr is None:
            raise HTTPException(status_code=500, detail="pg_dump pipe setup failed")
        stderr = (await proc.stderr.read()).decode(errors="replace")
        returncode = await proc.wait()
        if returncode != 0:
            logger.error("db_backup_failed", returncode=returncode, stderr=stderr[-2000:])
            raise HTTPException(
                status_code=500,
                detail=f"pg_dump failed (exit {returncode}): {stderr[-2000:]}",
            )

    file_size = os.path.getsize(dump_path)

    async def stream():
        try:
            with open(dump_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk
        finally:
            try:
                os.remove(dump_path)
            except OSError:
                pass

    return StreamingResponse(
        stream(),
        media_type="application/sql",
        headers={"X-Ethiobio-Backup-Size": str(file_size)},
    )


@router.get("/dashboard")
async def admin_dashboard(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        user_count = await session.scalar(select(func.count(User.id)))
        teacher_count = await session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.teacher)
        )
        student_count = await session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.student)
        )
        quiz_count = await session.scalar(select(func.count(Quiz.id)))
        lesson_count = await session.scalar(select(func.count(LessonPlan.id)))
        attempt_count = await session.scalar(select(func.count(QuizAttempt.id)))

        latest_logs = await session.execute(
            select(ModelRoutingLog).order_by(ModelRoutingLog.created_at.desc()).limit(20)
        )
        logs = latest_logs.scalars().all()

        recent_users_result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(20)
        )
        recent_users = recent_users_result.scalars().all()

        return {
            "users": user_count or 0,
            "teachers": teacher_count or 0,
            "students": student_count or 0,
            "quizzes": quiz_count or 0,
            "lesson_plans": lesson_count or 0,
            "quiz_attempts": attempt_count or 0,
            "recent_users": [
                {
                    "id": str(u.id),
                    "telegram_id": u.telegram_id,
                    "role": u.role.value if u.role else "student",
                    "language_preference": u.language_preference or "en",
                    "grade_level": u.grade_level,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in recent_users
            ],
            "recent_logs": [
                {
                    "id": str(log.id),
                    "request_type": log.request_type,
                    "model_used": log.model_used,
                    "success": log.success,
                    "latency_ms": log.latency_ms,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }
    except Exception as e:
        logger.error("admin_dashboard_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/review")
async def review_content(
    type: str = Query("quiz", pattern="^(quiz|lesson)$"),
    content_type: str = Query(None, pattern="^(quiz|lesson)$"),
    status: str = Query("draft", pattern="^(draft|published|archived)$"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    effective_type = content_type or type
    try:
        if effective_type == "quiz":
            items = await session.execute(
                select(Quiz).where(Quiz.status == status).order_by(Quiz.created_at.desc()).limit(50)
            )
            results = [
                {
                    "id": str(q.id),
                    "title": q.title,
                    "grade_level": q.grade_level,
                    "topic": q.topic,
                    "question_count": q.question_count,
                    "status": q.status,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in items.scalars().all()
            ]
        else:
            items = await session.execute(
                select(LessonPlan)
                .where(LessonPlan.status == status)
                .order_by(LessonPlan.created_at.desc())
                .limit(50)
            )
            results = [
                {
                    "id": str(item.id),
                    "topic": item.topic,
                    "grade_level": item.grade_level,
                    "objective": item.objective[:100] if item.objective else "",
                    "status": item.status,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in items.scalars().all()
            ]
        return {"content_type": effective_type, "status": status, "items": results}
    except Exception as e:
        logger.error("admin_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring")
async def get_monitoring(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        total_requests = await session.scalar(select(func.count(ModelRoutingLog.id)))
        failed_requests = await session.scalar(
            select(func.count(ModelRoutingLog.id)).where(not ModelRoutingLog.success)
        )
        fallbacks = await session.scalar(
            select(func.count(ModelRoutingLog.id)).where(ModelRoutingLog.fallback_triggered)
        )

        return {
            "total_requests": total_requests or 0,
            "failed_requests": failed_requests or 0,
            "fallback_rate": round((fallbacks or 0) / max(total_requests or 1, 1) * 100, 2),
            "fallbacks": fallbacks or 0,
        }
    except Exception as e:
        logger.error("monitoring_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-metrics")
async def get_voice_metrics(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        total_recordings = await session.scalar(select(func.count(AudioRecording.id)))
        by_language = (
            await session.execute(
                select(AudioRecording.language, func.count(AudioRecording.id)).group_by(
                    AudioRecording.language
                )
            )
        ).all()
        by_direction = (
            await session.execute(
                select(AudioRecording.direction, func.count(AudioRecording.id)).group_by(
                    AudioRecording.direction
                )
            )
        ).all()
        by_modality = (
            await session.execute(
                select(AudioRecording.modality, func.count(AudioRecording.id)).group_by(
                    AudioRecording.modality
                )
            )
        ).all()

        return {
            "total_recordings": total_recordings or 0,
            "by_language": {row[0]: row[1] for row in by_language},
            "by_direction": {row[0]: row[1] for row in by_direction},
            "by_modality": {row[0]: row[1] for row in by_modality},
        }
    except Exception as e:
        logger.error("voice_metrics_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-providers")
async def get_voice_providers(
    _: User = Depends(require_admin),
):
    try:
        return speech_registry.get_provider_status()
    except Exception as e:
        logger.error("voice_providers_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/quiz/{item_id}")
async def get_quiz_detail(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    from uuid import UUID

    try:
        item_uuid = UUID(item_id)
        quiz = await session.get(Quiz, item_uuid)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        questions_result = await session.execute(
            select(Question).where(Question.quiz_id == item_uuid).order_by(Question.created_at)
        )
        questions = questions_result.scalars().all()

        return {
            "id": str(quiz.id),
            "title": quiz.title,
            "grade_level": quiz.grade_level,
            "topic": quiz.topic,
            "question_count": quiz.question_count,
            "status": quiz.status,
            "model_used": quiz.model_used,
            "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
            "questions": [
                {
                    "id": str(q.id),
                    "question_type": q.question_type,
                    "question_text": q.question_text,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty,
                }
                for q in questions
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("quiz_detail_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/lesson/{item_id}")
async def get_lesson_detail(
    item_id: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    from uuid import UUID

    try:
        item_uuid = UUID(item_id)
        lesson = await session.get(LessonPlan, item_uuid)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson plan not found")

        return {
            "id": str(lesson.id),
            "topic": lesson.topic,
            "grade_level": lesson.grade_level,
            "objective": lesson.objective,
            "prior_knowledge": lesson.prior_knowledge,
            "explanation": lesson.explanation,
            "activities": lesson.activities,
            "assessment": lesson.assessment,
            "homework": lesson.homework,
            "teacher_notes": lesson.teacher_notes,
            "status": lesson.status,
            "model_used": lesson.model_used,
            "periods": lesson.periods,
            "exit_ticket": lesson.exit_ticket,
            "differentiation": lesson.differentiation,
            "diagram_suggestions": lesson.diagram_suggestions,
            "misconception_activities": lesson.misconception_activities,
            "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("lesson_detail_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/content/{content_type}/{item_id}/status")
async def update_content_status(
    content_type: str,
    item_id: str,
    status: str = Query(..., pattern="^(draft|published|archived)$"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    from uuid import UUID

    try:
        item_uuid = UUID(item_id)
        model_cls = (
            Quiz if content_type == "quiz" else LessonPlan if content_type == "lesson" else None
        )
        if not model_cls:
            raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")

        item = await session.get(model_cls, item_uuid)
        if not item:
            raise HTTPException(status_code=404, detail=f"{content_type} not found")

        item.status = status
        await session.commit()
        return {"ok": True, "content_type": content_type, "id": item_id, "status": status}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("content_status_update_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


class UserListResponse(BaseModel):
    users: list[dict]
    total: int
    page: int
    per_page: int


class UpdateUserStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


@router.get("/users", response_model=UserListResponse)
async def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None, pattern="^(student|teacher|parent|admin)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    query = select(User)

    if search:
        query = query.where(
            or_(User.email.ilike(f"%{search}%"), User.telegram_id.cast(String).ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == UserRole[role])

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    users = result.scalars().all()

    result_data = []
    for u in users:
        children_list = []
        if u.role == UserRole.parent:
            pc_query = (
                select(ParentChild)
                .where(ParentChild.parent_id == u.id)
                .options(selectinload(ParentChild.student))
            )
            pc_result = await session.execute(pc_query)
            for pc in pc_result.scalars().all():
                children_list.append(
                    {
                        "id": str(pc.student.id),
                        "email": pc.student.email or f"Student #{str(pc.student.id)[:8]}",
                    }
                )

        result_data.append(
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role.value if u.role else None,
                "grade_level": u.grade_level,
                "telegram_id": u.telegram_id,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "children": children_list if children_list else None,
            }
        )

    return {
        "users": result_data,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: UpdateUserStatusRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await session.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = body.is_active
    await session.commit()
    return {"ok": True, "user_id": user_id, "is_active": user.is_active}


class UpdateUserRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = await session.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role not in ("student", "teacher", "parent", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = UserRole(body.role)
    await session.commit()
    return {"ok": True, "user_id": user_id, "role": body.role}


@router.get("/schools")
async def list_admin_schools(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    result = await session.execute(select(School).options(selectinload(School.class_groups)))
    schools = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "name": s.name,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "teacher_count": len({cg.teacher_id for cg in s.class_groups}),
            "student_count": sum(len(cg.students) for cg in s.class_groups),
            "grade_range": (
                f"{min(cg.grade_level for cg in s.class_groups)}-"
                f"{max(cg.grade_level for cg in s.class_groups)}"
            )
            if s.class_groups
            else "N/A",
        }
        for s in schools
    ]


class ReviewListResponse(BaseModel):
    traces: list[dict]
    total: int
    limit: int
    offset: int


class ReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = "resolve"
    review_notes: str = ""


class ReviewActionResponse(BaseModel):
    trace_id: str
    status: str
    reviewed_at: str


@router.get("/review", response_model=ReviewListResponse)
async def list_review_items(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        query = select(AgentTrace).where(
            AgentTrace.event_metadata["requires_teacher_review"].as_string() == "true"
        )
        count_query = select(func.count(AgentTrace.trace_id)).where(
            AgentTrace.event_metadata["requires_teacher_review"].as_string() == "true"
        )

        if status == "resolved":
            query = query.where(AgentTrace.event_metadata["reviewed"].as_string() == "true")
            count_query = count_query.where(
                AgentTrace.event_metadata["reviewed"].as_string() == "true"
            )
        else:
            query = query.where(
                (AgentTrace.event_metadata["reviewed"].as_string() == "false")
                | (AgentTrace.event_metadata["reviewed"].is_(None))
            )
            count_query = count_query.where(
                (AgentTrace.event_metadata["reviewed"].as_string() == "false")
                | (AgentTrace.event_metadata["reviewed"].is_(None))
            )

        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(AgentTrace.start_time.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        traces = result.scalars().all()

        items = []
        for t in traces:
            md = t.event_metadata or {}
            items.append(
                {
                    "trace_id": t.trace_id,
                    "user_message": t.user_message,
                    "response": t.response,
                    "intent": t.intent,
                    "grade_level": t.grade_level,
                    "language": t.language,
                    "safety_issues": md.get("safety_issues", []),
                    "safety_action": md.get("safety_action", ""),
                    "groundedness_score": md.get("groundedness_score", 0.0),
                    "hallucination_rate": md.get("hallucination_rate", 0.0),
                    "requires_teacher_review": md.get("requires_teacher_review", False),
                    "reviewed": md.get("reviewed", False),
                    "review_notes": md.get("review_notes"),
                    "reviewed_at": md.get("reviewed_at"),
                    "created_at": t.start_time.isoformat() if t.start_time else None,
                }
            )

        return ReviewListResponse(traces=items, total=total, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/review/{trace_id}", response_model=ReviewActionResponse)
async def resolve_review_item(
    trace_id: str,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        result = await session.execute(select(AgentTrace).where(AgentTrace.trace_id == trace_id))
        trace = result.scalar_one_or_none()
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        md = dict(trace.event_metadata or {})
        if not md.get("requires_teacher_review"):
            raise HTTPException(
                status_code=400,
                detail="Trace does not require teacher review",
            )

        now = datetime.now(timezone.utc).isoformat()
        md["reviewed"] = True
        md["reviewed_at"] = now
        md["review_notes"] = body.review_notes
        trace.event_metadata = md

        await session.flush()
        await session.commit()

        return ReviewActionResponse(
            trace_id=trace_id,
            status="resolved",
            reviewed_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("resolve_review_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
