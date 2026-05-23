import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lesson_planner import LessonPlannerAgent
from src.database.models import LessonPlan
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.lesson import LessonPlanRequest, LessonPlanResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/lesson-plan", tags=["Lesson Plan"])


@router.post("/generate", response_model=LessonPlanResponse)
async def generate_lesson_plan(request: LessonPlanRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter(preferred_model=request.model)
    agent = LessonPlannerAgent(llm_router=router_llm)

    try:
        result = await agent.generate(
            grade_level=request.grade_level,
            topic=request.topic,
            duration_minutes=request.duration_minutes,
            language=request.language,
            session=session,
        )

        db_plan = LessonPlan(
            teacher_id=request.teacher_id,
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

        return LessonPlanResponse(
            objective=result["objective"],
            prior_knowledge=result.get("prior_knowledge"),
            explanation=result["explanation"],
            activities=result.get("activities", []),
            assessment=result.get("assessment", ""),
            homework=result.get("homework"),
            teacher_notes=result.get("teacher_notes"),
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        await session.rollback()
        logger.error("lesson_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
