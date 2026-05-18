"""LangGraph-powered API endpoint for the EthioBio orchestration pipeline."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
import structlog

from src.graph.orchestrator import run_graph

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["Graph"])


class GraphChatRequest(BaseModel):
    question: str
    user_id: Optional[UUID] = None
    grade_level: Optional[int] = Field(None, ge=7, le=12)
    topic: Optional[str] = None
    language: str = "en"
    model: Optional[str] = None


class GraphChatResponse(BaseModel):
    answer: str
    model_used: str
    confidence: float
    sources: list[str] = []
    status: str = "approved"
    requires_teacher_review: bool = False


@router.post("/chat", response_model=GraphChatResponse)
async def graph_chat(request: GraphChatRequest):
    try:
        result = await run_graph(
            user_message=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            preferred_model=request.model,
        )

        return GraphChatResponse(
            answer=result.answer,
            model_used=result.model_used,
            confidence=result.confidence,
            sources=result.sources,
            status=result.status,
            requires_teacher_review=result.requires_teacher_review,
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
