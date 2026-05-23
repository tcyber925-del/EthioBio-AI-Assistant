from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.database.models import LessonPlan, Question, Quiz
from src.database.session import get_session
from src.export.docx_exporter import export_lesson_plan_to_docx, export_quiz_to_docx
from src.export.pdf_exporter import export_lesson_plan_to_pdf, export_quiz_to_pdf

logger = structlog.get_logger()
router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/quiz/{quiz_id}")
async def export_quiz(
    quiz_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    session: AsyncSession = Depends(get_session),
):
    from uuid import UUID

    try:
        item_uuid = UUID(quiz_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid quiz ID")

    try:
        quiz = await session.get(Quiz, item_uuid)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        questions_result = await session.execute(
            select(Question).where(Question.quiz_id == item_uuid).order_by(Question.created_at)
        )
        questions = questions_result.scalars().all()

        quiz_data = {
            "title": quiz.title,
            "grade_level": quiz.grade_level,
            "topic": quiz.topic,
        }
        questions_data: list[dict[str, Any]] = [
            {
                "question_type": q.question_type,
                "question_text": q.question_text,
                "options": q.options if isinstance(q.options, list) else (q.options or []),
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
            }
            for q in questions
        ]

        if format == "docx":
            content = export_quiz_to_docx(quiz_data, questions_data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"quiz_{quiz_id}.docx"
        else:
            content = export_quiz_to_pdf(quiz_data, questions_data)
            media_type = "application/pdf"
            filename = f"quiz_{quiz_id}.pdf"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("quiz_export_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson-plan/{lesson_id}")
async def export_lesson_plan(
    lesson_id: str,
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    session: AsyncSession = Depends(get_session),
):
    from uuid import UUID

    try:
        item_uuid = UUID(lesson_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lesson plan ID")

    try:
        lesson = await session.get(LessonPlan, item_uuid)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson plan not found")

        lesson_data = {
            "grade_level": lesson.grade_level,
            "topic": lesson.topic,
            "objective": lesson.objective,
            "prior_knowledge": lesson.prior_knowledge,
            "explanation": lesson.explanation,
            "activities": lesson.activities
            if isinstance(lesson.activities, list)
            else (lesson.activities or []),
            "assessment": lesson.assessment,
            "homework": lesson.homework,
            "teacher_notes": lesson.teacher_notes,
        }

        if format == "docx":
            content = export_lesson_plan_to_docx(lesson_data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"lesson_plan_{lesson_id}.docx"
        else:
            content = export_lesson_plan_to_pdf(lesson_data)
            media_type = "application/pdf"
            filename = f"lesson_plan_{lesson_id}.pdf"

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("lesson_plan_export_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
