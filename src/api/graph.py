"""LangGraph-powered API endpoint for the EthioBio orchestration pipeline."""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.database.session import get_session
from src.graph.orchestrator import run_graph
from src.schemas.base import SchemaModel

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["Graph"])


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


class GraphChatResponse(SchemaModel):
    answer: str
    model_used: str
    confidence: float
    sources: list[str] = []
    status: str = "approved"
    requires_teacher_review: bool = False
    socratic_mode: bool = False
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
    xp_awarded: int = 0
    level_up: bool = False
    new_level: int = 0


@router.post("/chat", response_model=GraphChatResponse)
async def graph_chat(request: GraphChatRequest, session: AsyncSession = Depends(get_session)):
    try:
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
        )

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

        return GraphChatResponse(
            answer=result.answer,
            model_used=result.model_used,
            confidence=result.confidence,
            sources=result.sources,
            status=result.status,
            requires_teacher_review=result.requires_teacher_review,
            socratic_mode=result.socratic_mode,
            hint_level=result.hint_level,
            reveal_answer=result.reveal_answer,
            misconception_detected=result.misconception_detected,
            misconception_correction=result.misconception_correction,
            xp_awarded=xp_awarded,
            level_up=level_up,
            new_level=new_level,
        )
    except Exception as e:
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
