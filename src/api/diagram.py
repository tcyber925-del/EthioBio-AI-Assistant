from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagram import DiagramAgent, validate_labels
from src.database.models import DiagramAttempt, TextbookDiagram
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.diagram import (
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramLabelResult,
    DiagramValidateRequest,
    DiagramValidateResponse,
    TextbookDiagramResponse,
    TextbookReference,
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
            preferred_model=request.model,
            grade=request.grade,
        )

        return DiagramGenerateResponse(
            diagram_svg=result["diagram_svg"],
            labels=result["labels"],
            title=result["title"],
            topic=result["topic"],
            difficulty=result["difficulty"],
            model_used=result.get("model_used", ""),
            textbook_references=[
                TextbookReference(**ref) for ref in result.get("textbook_references", [])
            ],
        )
    except Exception as e:
        logger.error("diagram_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=DiagramValidateResponse)
async def validate_diagram(
    request: DiagramValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    submitted = [l.model_dump() for l in request.submitted_labels]

    if request.textbook_diagram_id:
        diagram = await session.get(TextbookDiagram, request.textbook_diagram_id)
        if not diagram:
            raise HTTPException(status_code=404, detail="Textbook diagram not found")
        if not diagram.ground_truth_labels or not diagram.ground_truth_labels.get("labels"):
            raise HTTPException(
                status_code=400,
                detail="Textbook diagram has no ground truth labels",
            )
        correct = diagram.ground_truth_labels["labels"]
        source = "textbook"
    else:
        correct = [l.model_dump() for l in request.correct_labels]
        source = "ai_generated"

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
    try:
        await session.commit()
        await session.refresh(attempt)
    except IntegrityError as e:
        await session.rollback()
        logger.warning("diagram_validate_integrity_error", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Invalid user_id or database constraint violation",
        )

    return DiagramValidateResponse(
        score=score,
        total_labels=total,
        correct_count=correct_count,
        results=[DiagramLabelResult(**r) for r in results],
        attempt_id=attempt.id,
        source=source,
    )


@router.get("/textbook", response_model=list[TextbookDiagramResponse])
async def get_textbook_diagrams(
    grade: int = Query(..., ge=7, le=12, description="Grade level"),
    topic: Optional[str] = Query(None, description="Topic filter (case-insensitive)"),
    session: AsyncSession = Depends(get_session),
):
    """Retrieve extracted textbook diagrams filtered by grade and optional topic."""
    stmt = select(TextbookDiagram).where(TextbookDiagram.grade_level == grade)

    if topic:
        stmt = stmt.where(TextbookDiagram.topic.ilike(f"%{topic}%"))

    stmt = stmt.order_by(TextbookDiagram.figure_number)
    result = await session.execute(stmt)
    diagrams = result.scalars().all()

    return [
        TextbookDiagramResponse(
            id=d.id,
            image_url=f"/diagrams/static/{grade}/{Path(d.image_path).name}",
            caption=d.caption,
            grade_level=d.grade_level,
            unit=d.unit,
            topic=d.topic,
            figure_number=d.figure_number,
            page_number=d.page_number,
            source_file=d.source_file,
        )
        for d in diagrams
    ]
