from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database.session import get_session
from src.database.models import (
    User, Quiz, Question, LessonPlan, ModelRoutingLog,
    FeedbackEvent, QuizAttempt, UserRole,
)
from typing import Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def admin_dashboard(session: AsyncSession = Depends(get_session)):
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

        return {
            "users": user_count or 0,
            "teachers": teacher_count or 0,
            "students": student_count or 0,
            "quizzes": quiz_count or 0,
            "lesson_plans": lesson_count or 0,
            "quiz_attempts": attempt_count or 0,
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
                select(LessonPlan).where(LessonPlan.status == status).order_by(LessonPlan.created_at.desc()).limit(50)
            )
            results = [
                {
                    "id": str(l.id),
                    "topic": l.topic,
                    "grade_level": l.grade_level,
                    "objective": l.objective[:100] if l.objective else "",
                    "status": l.status,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in items.scalars().all()
            ]
        return {"content_type": effective_type, "status": status, "items": results}
    except Exception as e:
        logger.error("admin_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring")
async def get_monitoring(session: AsyncSession = Depends(get_session)):
    try:
        total_requests = await session.scalar(select(func.count(ModelRoutingLog.id)))
        failed_requests = await session.scalar(
            select(func.count(ModelRoutingLog.id)).where(ModelRoutingLog.success == False)
        )
        fallbacks = await session.scalar(
            select(func.count(ModelRoutingLog.id)).where(ModelRoutingLog.fallback_triggered == True)
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


@router.get("/content/quiz/{item_id}")
async def get_quiz_detail(item_id: str, session: AsyncSession = Depends(get_session)):
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
async def get_lesson_detail(item_id: str, session: AsyncSession = Depends(get_session)):
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
):
    from uuid import UUID
    try:
        item_uuid = UUID(item_id)
        model_cls = Quiz if content_type == "quiz" else LessonPlan if content_type == "lesson" else None
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
