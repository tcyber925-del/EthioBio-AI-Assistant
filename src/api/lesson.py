import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lesson_planner import LessonPlannerAgent
from src.core.lesson_planning import ClassroomIntelligenceService
from src.database.models import LessonPlan
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.lesson import (
    DiagramSuggestion,
    DifferentiationActivity,
    ExitTicketQuestion,
    LessonPlanRatingRequest,
    LessonPlanRequest,
    LessonPlanResponse,
    MisconceptionActivity,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/lesson-plan", tags=["Lesson Plan"])


@router.post("/generate", response_model=LessonPlanResponse)
async def generate_lesson_plan(
    request: LessonPlanRequest,
    session: AsyncSession = Depends(get_session),
):
    router_llm = ModelRouter(preferred_model=request.model)
    agent = LessonPlannerAgent(llm_router=router_llm)

    classroom_context = None
    if request.classroom_id:
        try:
            intelligence = ClassroomIntelligenceService(session)
            classroom_context = await intelligence.analyze(
                classroom_id=request.classroom_id,
                topic=request.topic,
            )
        except Exception:
            logger.warning("classroom_intelligence_failed", exc_info=True)

    try:
        result = await agent.generate(
            grade_level=request.grade_level,
            topic=request.topic,
            duration_minutes=request.duration_minutes,
            language=request.language,
            session=session,
            generate_exit_ticket=request.generate_exit_ticket,
            generate_differentiation=request.generate_differentiation,
            generate_diagram_suggestions=request.generate_diagram_suggestions,
            generate_misconception_activities=request.generate_misconception_activities,
            classroom_context=classroom_context,
        )

        exit_ticket_data = result.get("exit_ticket")
        diff_data = result.get("differentiation")
        diagram_data = result.get("diagram_suggestions")
        mc_activity_data = result.get("misconception_activities")

        db_plan = LessonPlan(
            teacher_id=request.teacher_id,
            classroom_id=request.classroom_id,
            grade_level=request.grade_level,
            topic=request.topic,
            objective=result["objective"],
            prior_knowledge=result.get("prior_knowledge"),
            explanation=result["explanation"],
            activities=result.get("activities", []),
            assessment=result.get("assessment", ""),
            homework=result.get("homework"),
            teacher_notes=result.get("teacher_notes"),
            model_used=result.get("model_used", ""),
        )
        session.add(db_plan)
        await session.commit()

        exit_ticket = (
            [ExitTicketQuestion(**q) for q in exit_ticket_data]
            if exit_ticket_data
            else None
        )
        differentiation = (
            [DifferentiationActivity(**d) for d in diff_data]
            if diff_data
            else None
        )
        diagram_suggestions = (
            [DiagramSuggestion(**d) for d in diagram_data]
            if diagram_data
            else None
        )
        misconception_activities = (
            [MisconceptionActivity(**a) for a in mc_activity_data]
            if mc_activity_data
            else None
        )

        return LessonPlanResponse(
            id=db_plan.id,
            objective=result["objective"],
            prior_knowledge=result.get("prior_knowledge"),
            explanation=result["explanation"],
            activities=result.get("activities", []),
            assessment=result.get("assessment", ""),
            homework=result.get("homework"),
            teacher_notes=result.get("teacher_notes"),
            model_used=result.get("model_used", ""),
            classroom_id=db_plan.classroom_id,
            rating=db_plan.rating,
            feedback=db_plan.feedback,
            used_in_class=db_plan.used_in_class,
            created_at=db_plan.created_at.isoformat() if db_plan.created_at else None,
            exit_ticket=exit_ticket,
            differentiation=differentiation,
            diagram_suggestions=diagram_suggestions,
            misconception_activities=misconception_activities,
            classroom_context=classroom_context,
        )
    except Exception as e:
        await session.rollback()
        logger.error("lesson_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{plan_id}/rate", response_model=LessonPlanResponse)
async def rate_lesson_plan(
    plan_id: uuid.UUID,
    rating_data: LessonPlanRatingRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(LessonPlan).where(LessonPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    plan.rating = rating_data.rating
    if rating_data.feedback is not None:
        plan.feedback = rating_data.feedback
    plan.used_in_class = rating_data.used_in_class
    await session.commit()

    return LessonPlanResponse(
        id=plan.id,
        objective=plan.objective,
        prior_knowledge=plan.prior_knowledge,
        explanation=plan.explanation,
        activities=plan.activities if isinstance(plan.activities, list) else [],
        assessment=plan.assessment or "",
        homework=plan.homework,
        teacher_notes=plan.teacher_notes,
        model_used=plan.model_used or "",
        classroom_id=plan.classroom_id,
        rating=plan.rating,
        feedback=plan.feedback,
        used_in_class=plan.used_in_class,
        created_at=plan.created_at.isoformat() if plan.created_at else None,
    )


@router.get("/{plan_id}", response_model=LessonPlanResponse)
async def get_lesson_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(LessonPlan).where(LessonPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Lesson plan not found")

    return LessonPlanResponse(
        id=plan.id,
        objective=plan.objective,
        prior_knowledge=plan.prior_knowledge,
        explanation=plan.explanation,
        activities=plan.activities if isinstance(plan.activities, list) else [],
        assessment=plan.assessment or "",
        homework=plan.homework,
        teacher_notes=plan.teacher_notes,
        model_used=plan.model_used or "",
        classroom_id=plan.classroom_id,
        rating=plan.rating,
        feedback=plan.feedback,
        used_in_class=plan.used_in_class,
        created_at=plan.created_at.isoformat() if plan.created_at else None,
    )


@router.get("/")
async def list_lesson_plans(
    teacher_id: uuid.UUID | None = None,
    classroom_id: uuid.UUID | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(LessonPlan).order_by(LessonPlan.created_at.desc()).limit(limit)
    if teacher_id:
        stmt = stmt.where(LessonPlan.teacher_id == teacher_id)
    if classroom_id:
        stmt = stmt.where(LessonPlan.classroom_id == classroom_id)

    result = await session.execute(stmt)
    plans = result.scalars().all()

    return [
        LessonPlanResponse(
            id=p.id,
            objective=p.objective,
            prior_knowledge=p.prior_knowledge,
            explanation=p.explanation,
            activities=p.activities if isinstance(p.activities, list) else [],
            assessment=p.assessment or "",
            homework=p.homework,
            teacher_notes=p.teacher_notes,
            model_used=p.model_used or "",
            classroom_id=p.classroom_id,
            rating=p.rating,
            feedback=p.feedback,
            used_in_class=p.used_in_class,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )
        for p in plans
    ]
