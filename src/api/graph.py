"""LangGraph pipeline monitoring and diagnostic endpoints.

The /graph/chat endpoint is now served by the unified handler in chat.py.
This module keeps only monitoring/diagnostic routes.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.chat import handle_chat_request
from src.core.monitoring import pipeline_monitor
from src.database.session import get_session
from src.schemas.chat import TutorRequest, TutorResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["Graph"])


@router.post("/chat")
async def graph_chat(request: TutorRequest, db: AsyncSession = Depends(get_session)):
    return await handle_chat_request(request, db, current_user=None)


@router.get("/status")
async def graph_status():
    """Show the current graph structure and node count."""
    return {
        "version": "1.2.0",
        "pipeline": "unified",
        "legacy_nodes": ["orchestrator", "retrieve", "skip_retrieval", "tutor", "safety"],
        "agentic_nodes": [
            "orchestrator",
            "planner",
            "plan_executor",
            "sufficient_context",
            "synthesis",
            "tutor",
            "claim_verifier",
            "safety",
        ],
        "legacy_edges": [
            "orchestrator → retrieve (if needs curriculum)",
            "orchestrator → skip_retrieval (if no curriculum needed)",
            "retrieve → tutor",
            "skip_retrieval → tutor",
            "tutor → safety",
            "safety → tutor (if revision needed)",
            "safety → END (if approved)",
        ],
        "agentic_edges": [
            "orchestrator → planner (if requires_planning=True)",
            "orchestrator → retrieve/skip_retrieval (legacy path)",
            "planner → plan_executor",
            "plan_executor → sufficient_context",
            "sufficient_context → synthesis (if sufficient)",
            "sufficient_context → plan_executor (if minor gap)",
            "sufficient_context → planner (if major gap)",
            "synthesis → tutor",
            "tutor → claim_verifier",
            "claim_verifier → safety (if grounded)",
            "claim_verifier → tutor (if needs revision)",
            "safety → END",
        ],
        "features": {
            "hybrid_routing": True,
            "iterative_retrieval": True,
            "claim_verification": True,
            "evidence_synthesis": True,
            "three_layer_stopping": True,
            "monitoring": True,
        },
    }


@router.get("/metrics")
async def pipeline_metrics():
    """Get aggregated pipeline health and quality metrics.

    Returns 5 key metrics from PRD-009:
    1. Pipeline completion rate
    2. Average iterations per query
    3. Coverage score distribution
    4. Claim groundedness rate
    5. Teacher review flag rate
    """
    metrics = pipeline_monitor.get_metrics()
    return {
        "health": {
            "total_traces": metrics.total_traces,
            "completed_traces": metrics.completed_traces,
            "failed_traces": metrics.failed_traces,
            "running_traces": metrics.running_traces,
            "completion_rate": metrics.completion_rate,
            "avg_duration_ms": metrics.avg_duration_ms,
        },
        "retrieval": {
            "avg_iterations": metrics.avg_iterations,
            "total_iterations": metrics.total_iterations,
            "avg_coverage_score": metrics.avg_coverage_score,
        },
        "verification": {
            "avg_groundedness": metrics.avg_groundedness,
            "revision_rate": metrics.revision_rate,
            "rejection_rate": metrics.rejection_rate,
        },
        "teacher_review": {
            "teacher_review_rate": metrics.teacher_review_rate,
            "total_teacher_reviews": metrics.total_teacher_reviews,
        },
        "performance": {
            "avg_node_duration_ms": metrics.avg_node_duration_ms,
        },
    }


@router.get("/traces")
async def recent_traces(limit: int = 20):
    """List recent pipeline traces for debugging."""
    return {"traces": pipeline_monitor.list_traces(limit=limit)}


@router.get("/trace/{trace_id}")
async def trace_detail(trace_id: str):
    """Get detailed trace information."""
    trace = pipeline_monitor.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace": trace.to_dict()}
