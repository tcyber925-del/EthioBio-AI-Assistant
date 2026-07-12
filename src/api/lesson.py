import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.unit_planner import UnitPlannerAgent
from src.api.auth import get_current_user
from src.core.lesson_planning import ClassroomIntelligenceService
from src.database.models import LessonPlan, UnitPlan, User
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.lesson import (
    DayLesson,
    DiagramSuggestion,
    DifferentiationActivity,
    ExitTicketQuestion,
    LessonPlanRatingRequest,
    LessonPlanRequest,
    LessonPlanResponse,
    MisconceptionActivity,
    Period,
    UnitPlanGenerateRequest,
    UnitPlanResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/lesson-plan", tags=["Lesson Plan"])


@router.post("/generate", response_model=LessonPlanResponse)
async def generate_lesson_plan(
    request: LessonPlanRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    teacher_id = request.teacher_id or current_user.id
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
        periods_data = result.get("periods")

        db_plan = LessonPlan(
            teacher_id=teacher_id,
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
            periods=result.get("periods"),
            exit_ticket=exit_ticket_data,
            differentiation=diff_data,
            diagram_suggestions=diagram_data,
            misconception_activities=mc_activity_data,
        )
        session.add(db_plan)
        await session.commit()

        exit_ticket = (
            [ExitTicketQuestion(**q) for q in exit_ticket_data] if exit_ticket_data else None
        )
        differentiation = [DifferentiationActivity(**d) for d in diff_data] if diff_data else None
        diagram_suggestions = (
            [DiagramSuggestion(**d) for d in diagram_data] if diagram_data else None
        )
        misconception_activities = (
            [MisconceptionActivity(**a) for a in mc_activity_data] if mc_activity_data else None
        )

        periods = [Period(**p) for p in periods_data] if periods_data else None

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
            periods=periods,
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
    result = await session.execute(select(LessonPlan).where(LessonPlan.id == plan_id))
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
        periods=(
            [Period(**p) for p in plan.periods]
            if (plan.periods and isinstance(plan.periods, list))
            else None
        ),
        exit_ticket=(
            [ExitTicketQuestion(**q) for q in plan.exit_ticket]
            if (plan.exit_ticket and isinstance(plan.exit_ticket, list))
            else None
        ),
        differentiation=(
            [DifferentiationActivity(**d) for d in plan.differentiation]
            if (plan.differentiation and isinstance(plan.differentiation, list))
            else None
        ),
        diagram_suggestions=(
            [DiagramSuggestion(**d) for d in plan.diagram_suggestions]
            if (plan.diagram_suggestions and isinstance(plan.diagram_suggestions, list))
            else None
        ),
        misconception_activities=(
            [MisconceptionActivity(**a) for a in plan.misconception_activities]
            if (plan.misconception_activities and isinstance(plan.misconception_activities, list))
            else None
        ),
    )


@router.get("/{plan_id}", response_model=LessonPlanResponse)
async def get_lesson_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(LessonPlan).where(LessonPlan.id == plan_id))
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
        periods=(
            [Period(**p) for p in plan.periods]
            if (plan.periods and isinstance(plan.periods, list))
            else None
        ),
        exit_ticket=(
            [ExitTicketQuestion(**q) for q in plan.exit_ticket]
            if (plan.exit_ticket and isinstance(plan.exit_ticket, list))
            else None
        ),
        differentiation=(
            [DifferentiationActivity(**d) for d in plan.differentiation]
            if (plan.differentiation and isinstance(plan.differentiation, list))
            else None
        ),
        diagram_suggestions=(
            [DiagramSuggestion(**d) for d in plan.diagram_suggestions]
            if (plan.diagram_suggestions and isinstance(plan.diagram_suggestions, list))
            else None
        ),
        misconception_activities=(
            [MisconceptionActivity(**a) for a in plan.misconception_activities]
            if (plan.misconception_activities and isinstance(plan.misconception_activities, list))
            else None
        ),
    )


@router.get("/")
async def list_lesson_plans(
    teacher_id: uuid.UUID | None = None,
    classroom_id: uuid.UUID | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if teacher_id is None:
        teacher_id = current_user.id
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
            periods=(
                [Period(**p_) for p_ in p.periods]
                if (p.periods and isinstance(p.periods, list))
                else None
            ),
            exit_ticket=(
                [ExitTicketQuestion(**q) for q in p.exit_ticket]
                if (p.exit_ticket and isinstance(p.exit_ticket, list))
                else None
            ),
            differentiation=(
                [DifferentiationActivity(**d) for d in p.differentiation]
                if (p.differentiation and isinstance(p.differentiation, list))
                else None
            ),
            diagram_suggestions=(
                [DiagramSuggestion(**d) for d in p.diagram_suggestions]
                if (p.diagram_suggestions and isinstance(p.diagram_suggestions, list))
                else None
            ),
            misconception_activities=(
                [MisconceptionActivity(**a) for a in p.misconception_activities]
                if (p.misconception_activities and isinstance(p.misconception_activities, list))
                else None
            ),
        )
        for p in plans
    ]


@router.post("/unit/generate", response_model=UnitPlanResponse)
async def generate_unit_plan(
    request: UnitPlanGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    router_llm = ModelRouter(preferred_model=request.model)
    agent = UnitPlannerAgent(llm_router=router_llm)

    try:
        result = await agent.generate_unit(
            unit_title=request.unit_title,
            grade_level=request.grade_level,
            topic=request.topic,
            days=request.days,
            duration_minutes=request.duration_minutes,
            language=request.language,
            session=session,
            generate_exit_ticket=request.generate_exit_ticket,
            generate_differentiation=request.generate_differentiation,
            generate_diagram_suggestions=request.generate_diagram_suggestions,
            generate_misconception_activities=request.generate_misconception_activities,
            preferred_model=request.model,
        )

        db_unit = UnitPlan(
            teacher_id=request.teacher_id,
            unit_title=request.unit_title,
            grade_level=request.grade_level,
            topic=request.topic,
            days=request.days,
            duration_minutes=request.duration_minutes,
            language=request.language,
            model_used=result.get("model_used", ""),
        )
        session.add(db_unit)
        await session.flush()

        day_lessons = []
        for day in result.get("lessons", []):
            lesson_data = day.get("lesson", {})
            db_plan = LessonPlan(
                teacher_id=request.teacher_id,
                grade_level=request.grade_level,
                topic=day.get("subtopic", ""),
                objective=lesson_data.get("objective", ""),
                prior_knowledge=lesson_data.get("prior_knowledge"),
                explanation=lesson_data.get("explanation", ""),
                activities=lesson_data.get("activities", []),
                assessment=lesson_data.get("assessment", ""),
                homework=lesson_data.get("homework"),
                teacher_notes=lesson_data.get("teacher_notes"),
                model_used=lesson_data.get("model_used", ""),
                periods=lesson_data.get("periods"),
                exit_ticket=lesson_data.get("exit_ticket"),
                differentiation=lesson_data.get("differentiation"),
                diagram_suggestions=lesson_data.get("diagram_suggestions"),
                misconception_activities=lesson_data.get("misconception_activities"),
                unit_id=db_unit.id,
                day_index=day.get("day_index"),
            )
            session.add(db_plan)

            lesson_resp = LessonPlanResponse(
                objective=lesson_data.get("objective", ""),
                prior_knowledge=lesson_data.get("prior_knowledge"),
                explanation=lesson_data.get("explanation", ""),
                activities=lesson_data.get("activities", []),
                assessment=lesson_data.get("assessment", ""),
                homework=lesson_data.get("homework"),
                teacher_notes=lesson_data.get("teacher_notes"),
                model_used=lesson_data.get("model_used", ""),
                periods=(
                    [Period(**p) for p in lesson_data.get("periods")]
                    if lesson_data.get("periods")
                    else None
                ),
                exit_ticket=(
                    [ExitTicketQuestion(**q) for q in lesson_data.get("exit_ticket")]
                    if lesson_data.get("exit_ticket")
                    else None
                ),
                differentiation=(
                    [DifferentiationActivity(**d) for d in lesson_data.get("differentiation")]
                    if lesson_data.get("differentiation")
                    else None
                ),
                diagram_suggestions=(
                    [DiagramSuggestion(**d) for d in lesson_data.get("diagram_suggestions")]
                    if lesson_data.get("diagram_suggestions")
                    else None
                ),
                misconception_activities=(
                    [
                        MisconceptionActivity(**a)
                        for a in lesson_data.get("misconception_activities")
                    ]
                    if lesson_data.get("misconception_activities")
                    else None
                ),
            )

            day_lessons.append(
                DayLesson(
                    day_index=day.get("day_index", 0),
                    subtopic=day.get("subtopic", ""),
                    objective=day.get("objective", ""),
                    lesson=lesson_resp,
                )
            )

        await session.commit()

        return UnitPlanResponse(
            id=db_unit.id,
            unit_title=request.unit_title,
            grade_level=request.grade_level,
            topic=request.topic,
            days=request.days,
            language=request.language,
            model_used=result.get("model_used", ""),
            created_at=db_unit.created_at.isoformat() if db_unit.created_at else None,
            lessons=day_lessons,
        )
    except Exception as e:
        await session.rollback()
        logger.error("unit_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unit/list")
async def list_unit_plans(
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await session.execute(
            select(UnitPlan).order_by(UnitPlan.created_at.desc()).limit(50)
        )
        plans = result.scalars().all()
        return {
            "items": [
                {
                    "id": str(p.id),
                    "unit_title": p.unit_title,
                    "topic": p.topic,
                    "grade_level": p.grade_level,
                    "days": p.days,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in plans
            ]
        }
    except Exception as e:
        logger.error("list_unit_plans_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unit/{unit_id}", response_model=UnitPlanResponse)
async def get_unit_plan(
    unit_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        unit = await session.get(UnitPlan, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit plan not found")

        result = await session.execute(
            select(LessonPlan).where(LessonPlan.unit_id == unit_id).order_by(LessonPlan.day_index)
        )
        day_lessons_db = result.scalars().all()

        day_lessons = []
        for dl in day_lessons_db:
            day_lessons.append(
                DayLesson(
                    day_index=dl.day_index or 0,
                    subtopic=dl.topic,
                    objective=dl.objective,
                    lesson=LessonPlanResponse(
                        objective=dl.objective,
                        prior_knowledge=dl.prior_knowledge,
                        explanation=dl.explanation,
                        activities=dl.activities if isinstance(dl.activities, list) else [],
                        assessment=dl.assessment or "",
                        homework=dl.homework,
                        teacher_notes=dl.teacher_notes,
                        model_used=dl.model_used or "",
                        periods=(
                            [Period(**p) for p in dl.periods]
                            if (dl.periods and isinstance(dl.periods, list))
                            else None
                        ),
                        exit_ticket=(
                            [ExitTicketQuestion(**q) for q in dl.exit_ticket]
                            if (dl.exit_ticket and isinstance(dl.exit_ticket, list))
                            else None
                        ),
                        differentiation=(
                            [DifferentiationActivity(**d) for d in dl.differentiation]
                            if (dl.differentiation and isinstance(dl.differentiation, list))
                            else None
                        ),
                        diagram_suggestions=(
                            [DiagramSuggestion(**d) for d in dl.diagram_suggestions]
                            if (dl.diagram_suggestions and isinstance(dl.diagram_suggestions, list))
                            else None
                        ),
                        misconception_activities=(
                            [MisconceptionActivity(**a) for a in dl.misconception_activities]
                            if (
                                dl.misconception_activities
                                and isinstance(dl.misconception_activities, list)
                            )
                            else None
                        ),
                    ),
                )
            )

        return UnitPlanResponse(
            id=unit.id,
            unit_title=unit.unit_title,
            grade_level=unit.grade_level,
            topic=unit.topic,
            days=unit.days,
            language=unit.language,
            model_used=unit.model_used,
            created_at=unit.created_at.isoformat() if unit.created_at else None,
            lessons=day_lessons,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_unit_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
