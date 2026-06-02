"""LangGraph-powered API endpoint for the EthioBio orchestration pipeline."""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.core.learning_intelligence.tutor.tutor_context_adapter import TutorContextAdapter
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.event_logger import EventLogger
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.database.session import get_session
from src.graph.orchestrator import run_graph
from src.schemas.base import SchemaModel

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["Graph"])

session_manager = SessionManager()
socratic_manager = SocraticManager()
context_assembler = ContextAssembler()
event_logger = EventLogger()
context_adapter = TutorContextAdapter()


class GraphChatRequest(SchemaModel):
    question: str
    user_id: Optional[UUID] = None
    grade_level: Optional[int] = Field(None, ge=7, le=12)
    topic: Optional[str] = None
    language: str = "en"
    model: Optional[str] = None
    socratic_mode: bool = False
    hint_level: int = 0
    reveal_answer: bool = False
    session_id: Optional[str] = None


class GraphChatResponse(SchemaModel):
    answer: str
    model_used: str
    confidence: float
    sources: list[str] = []
    status: str = "approved"
    requires_teacher_review: bool = False
    session_id: str = ""
    socratic_mode: bool = False
    socratic_stage: str = ""
    socratic_focus: str = ""
    socratic_understanding: str = ""
    socratic_next_question: str = ""
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
    xp_awarded: int = 0
    level_up: bool = False
    new_level: int = 0


@router.post("/chat", response_model=GraphChatResponse)
async def graph_chat(request: GraphChatRequest, db: AsyncSession = Depends(get_session)):
    try:
        mem_session = None
        socratic_state_rec = None
        if request.user_id:
            mem_session = await session_manager.get_or_create_active_session(
                request.user_id, topic=request.topic, db=db,
            )
            if request.socratic_mode and request.topic:
                socratic_state_rec = await socratic_manager.get_state(
                    request.user_id, request.topic, db,
                )

        memory_context = ""
        if request.user_id and mem_session:
            memory_context = await context_assembler.assemble(
                user_id=request.user_id,
                topic=request.topic,
                db=db,
                session_state={
                    "active_topic": mem_session.active_topic,
                    "tutoring_mode": mem_session.tutoring_mode,
                    "educational_context": mem_session.educational_context,
                    "unresolved_questions": mem_session.unresolved_questions,
                } if mem_session else None,
                socratic_state={
                    "socratic_stage": socratic_state_rec.socratic_stage,
                    "current_focus": socratic_state_rec.current_focus,
                    "student_understanding": socratic_state_rec.student_understanding,
                    "conceptual_gaps": socratic_state_rec.conceptual_gaps,
                } if socratic_state_rec else None,
            )

        learner_profile_block = ""
        if request.user_id:
            try:
                package = await context_adapter.build(
                    db, request.user_id, current_topic=request.topic,
                )
                learner_profile_block = package.formatted_block
            except Exception:
                logger.warning("tutor_context_build_failed", user_id=str(request.user_id))

        result = await run_graph(
            user_message=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            preferred_model=request.model,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            session_id=str(mem_session.session_id) if mem_session else None,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
            socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
            socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
            socratic_understanding=(
                socratic_state_rec.student_understanding if socratic_state_rec else ""
            ),
            socratic_next_question=socratic_state_rec.next_question if socratic_state_rec else "",
        )

        if request.user_id and request.socratic_mode and request.topic:
            await socratic_manager.update_state(
                user_id=request.user_id,
                topic=request.topic,
                db=db,
                updates={
                    "socratic_stage": result.socratic_stage,
                    "current_focus": result.socratic_focus,
                    "student_understanding": result.socratic_understanding,
                    "next_question": result.socratic_next_question,
                },
            )

        if mem_session:
            if not isinstance(mem_session.educational_context, dict):
                mem_session.educational_context = {}
            turns = mem_session.educational_context.setdefault("recent_turns", [])
            turns.append({
                "role": "user",
                "content": request.question,
            })
            if result.answer:
                turns.append({
                    "role": "assistant",
                    "content": result.answer,
                })
            mem_session.educational_context["recent_turns"] = turns[-10:]

            mem_session.unresolved_questions = [
                getattr(result, attr, "")
                for attr in ("guiding_question",) if getattr(result, "guiding_question", "")
            ]
            await session_manager.heartbeat(mem_session.session_id, db)

        if request.user_id:
            await event_logger.log(
                request.user_id, "tutor_interaction",
                topic=request.topic, db=db,
            )

        xp_awarded = 0
        level_up = False
        new_level = 0
        if request.user_id:
            await update_streak(request.user_id, db)
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            gam, _, level_up = await award_xp(
                request.user_id, "tutor_interaction", xp_amount,
                {"question_topic": request.topic or ""}, db,
            )
            xp_awarded = xp_amount
            new_level = gam.level if level_up else 0
            await check_achievements(request.user_id, gam, db)

        await db.commit()

        return GraphChatResponse(
            answer=result.answer,
            model_used=result.model_used,
            confidence=result.confidence,
            sources=result.sources,
            status=result.status,
            requires_teacher_review=result.requires_teacher_review,
            session_id=result.session_id,
            socratic_mode=result.socratic_mode,
            socratic_stage=result.socratic_stage,
            socratic_focus=result.socratic_focus,
            socratic_understanding=result.socratic_understanding,
            socratic_next_question=result.socratic_next_question,
            hint_level=result.hint_level,
            reveal_answer=result.reveal_answer,
            misconception_detected=result.misconception_detected,
            misconception_correction=result.misconception_correction,
            xp_awarded=xp_awarded,
            level_up=level_up,
            new_level=new_level,
        )
    except Exception as e:
        await db.rollback()
        logger.error("graph_chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def graph_status():
    """Show the current graph structure and node count."""
    return {
        "version": "1.1.0",
        "nodes": ["orchestrator", "retrieve", "skip_retrieval", "tutor", "safety"],
        "edges": [
            "orchestrator → retrieve (if needs curriculum)",
            "orchestrator → skip_retrieval (if no curriculum needed)",
            "retrieve → tutor",
            "skip_retrieval → tutor",
            "tutor → safety",
            "safety → tutor (if revision needed)",
            "safety → END (if approved)",
        ],
    }
