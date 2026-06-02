import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.tutor import TutorAgent
from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService
from src.core.learning_intelligence.tutor.learner_profile_builder import LearnerProfileBuilder
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.session_manager import SessionManager
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.rag.retriever import Retriever
from src.schemas.chat import TutorRequest, TutorResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])

session_manager = SessionManager()
context_assembler = ContextAssembler()
snapshot_service = SnapshotService()
profile_builder = LearnerProfileBuilder()


@router.post("", response_model=TutorResponse)
async def chat_tutor(request: TutorRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter()
    retriever = Retriever()
    agent = TutorAgent(llm_router=router_llm, retriever=retriever)

    try:
        mem_session = None
        memory_context = ""
        if request.user_id:
            mem_session = await session_manager.get_or_create_active_session(
                request.user_id, topic=request.topic, db=session,
            )
            if mem_session:
                memory_context = await context_assembler.assemble(
                    user_id=request.user_id,
                    topic=request.topic,
                    db=session,
                    session_state={
                        "active_topic": mem_session.active_topic,
                        "tutoring_mode": mem_session.tutoring_mode,
                        "educational_context": mem_session.educational_context,
                        "unresolved_questions": mem_session.unresolved_questions,
                    } if mem_session else None,
                    socratic_state=None,
                )

        learner_profile_block = ""
        if request.user_id:
            try:
                snapshot = await snapshot_service.get_snapshot(session, request.user_id)
                profile_result = profile_builder.build_profile(
                    snapshot, current_topic=request.topic,
                )
                learner_profile_block = profile_result.profile_block
            except Exception:
                logger.warning("learner_profile_build_failed", user_id=str(request.user_id))

        result = await agent.answer(
            question=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            use_rag=request.use_rag,
            session=session,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
        )

        if mem_session:
            if not isinstance(mem_session.educational_context, dict):
                mem_session.educational_context = {}
            turns = mem_session.educational_context.setdefault("recent_turns", [])
            turns.append({"role": "user", "content": request.question})
            if result["answer"]:
                turns.append({"role": "assistant", "content": result["answer"]})
            mem_session.educational_context["recent_turns"] = turns[-10:]

        xp_awarded = 0
        level_up = False
        new_level = 0
        if request.user_id:
            await update_streak(request.user_id, session)
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            gam, _, level_up = await award_xp(
                request.user_id, "tutor_interaction", xp_amount,
                {"question_topic": request.topic or ""}, session,
            )
            xp_awarded = xp_amount
            new_level = gam.level if level_up else 0
            await check_achievements(request.user_id, gam, session)
        return TutorResponse(
            answer=result["answer"],
            language=result.get("language", request.language),
            sources=result.get("sources", []),
            model_used=result.get("model_used", ""),
            confidence=result.get("confidence", 0.0),
            socratic_mode=result.get("socratic_mode", False),
            hint_level=result.get("hint_level", 0),
            reveal_answer=result.get("reveal_answer", False),
            misconception_detected=result.get("misconception_detected", False),
            misconception_correction=result.get("misconception_correction", ""),
            xp_awarded=xp_awarded,
            level_up=level_up,
            new_level=new_level,
        )
    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
