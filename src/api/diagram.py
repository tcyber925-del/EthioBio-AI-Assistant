from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagram import DiagramAgent, validate_labels
from src.database.models import DiagramAttempt
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.diagram import (
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramLabelResult,
    DiagramValidateRequest,
    DiagramValidateResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/diagram", tags=["Diagram"])


@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_diagram(
    request: DiagramGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    router_llm = ModelRouter()
    agent = DiagramAgent(llm_router=router_llm)

    try:
        result = await agent.generate(
            prompt=request.prompt,
            topic=request.topic,
            difficulty=request.difficulty,
            session=session,
        )

        return DiagramGenerateResponse(
            diagram_svg=result["diagram_svg"],
            labels=result["labels"],
            title=result["title"],
            topic=result["topic"],
            difficulty=result["difficulty"],
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        logger.error("diagram_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=DiagramValidateResponse)
async def validate_diagram(
    request: DiagramValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    correct = [l.model_dump() for l in request.correct_labels]
    submitted = [l.model_dump() for l in request.submitted_labels]

    results = validate_labels(correct, submitted)
    correct_count = sum(1 for r in results if r["is_correct"])
    total = len(results)
    score = round((correct_count / total * 100) if total > 0 else 0.0, 1)

    attempt = DiagramAttempt(
        user_id=request.user_id,
        topic=request.topic,
        difficulty=request.difficulty,
        score=score,
        labels={"submitted": submitted, "results": results},
        completed=True,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)

    return DiagramValidateResponse(
        score=score,
        total_labels=total,
        correct_count=correct_count,
        results=[DiagramLabelResult(**r) for r in results],
        attempt_id=attempt.id,
    )
