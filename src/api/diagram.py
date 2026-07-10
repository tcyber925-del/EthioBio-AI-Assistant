import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.agents.diagram import DiagramAgent, validate_labels
from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.database.models import DiagramAttempt, TextbookDiagram
from src.database.session import get_session
from src.export.diagram_exporter import export_diagram_to_docx, export_diagram_to_pdf
from src.llm.router import ModelRouter
from src.schemas.diagram import (
    AutoLabelBatchResponse,
    AutoLabelRequest,
    AutoLabelResponse,
    DiagramExportRequest,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramLabel,
    DiagramLabelResult,
    DiagramValidateRequest,
    DiagramValidateResponse,
    ImageValidationRequest,
    ImageValidationResponse,
    SketchToDiagramResponse,
    StyleTransferRequest,
    StyleTransferResponse,
    TextbookDiagramResponse,
    TextbookReference,
)
from src.schemas.icon_library import (
    IconComposeRequest,
    IconComposeResponse,
    IconListResponse,
)
from src.services.cloudflare_images import CloudflareImageGenerator
from src.services.icon_library import IconLibrary
from src.services.svg_validator import SvgImageValidator
from src.utils.svg_render import render_svg_to_png

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
    submitted = [lb.model_dump() for lb in request.submitted_labels]

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
        correct = [lb.model_dump() for lb in request.correct_labels]
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
    xp_awarded = 0
    level_up = False
    new_level = 0
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

    try:
        await update_streak(request.user_id, session)
        xp_amount = XP_SOURCES.get("diagram_completion", 10)
        gam, _, level_up = await award_xp(
            request.user_id,
            "diagram_completion",
            xp_amount,
            {"topic": request.topic, "difficulty": request.difficulty, "score": score},
            session,
        )
        xp_awarded = xp_amount
        new_level = gam.level if level_up else 0
        await check_achievements(request.user_id, gam, session)
        await session.commit()
    except Exception as e:
        logger.warning("diagram_xp_error", error=str(e))

    return DiagramValidateResponse(
        score=score,
        total_labels=total,
        correct_count=correct_count,
        results=[DiagramLabelResult(**r) for r in results],
        attempt_id=attempt.id,
        source=source,
        xp_awarded=xp_awarded,
        level_up=level_up,
        new_level=new_level,
    )


@router.post("/validate-image", response_model=ImageValidationResponse)
async def validate_diagram_image(request: ImageValidationRequest):
    import base64

    try:
        reference_bytes = base64.b64decode(request.reference_image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 reference image")

    validator = SvgImageValidator()
    result = validator.validate(svg=request.svg, reference_bytes=reference_bytes)
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])
    return ImageValidationResponse(
        score=result["score"],
        mse=result["mse"],
        histogram_similarity=result["histogram_similarity"],
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


@router.post("/textbook/auto-label", response_model=AutoLabelResponse)
async def auto_label_textbook_diagram(
    request: AutoLabelRequest,
    session: AsyncSession = Depends(get_session),
):
    diagram = await session.get(TextbookDiagram, UUID(request.diagram_id))
    if not diagram:
        raise HTTPException(status_code=404, detail="Textbook diagram not found")

    router_llm = ModelRouter()
    agent = DiagramAgent(llm_router=router_llm)
    try:
        result = await agent.generate(
            prompt=diagram.caption or diagram.topic,
            topic=diagram.topic or "biology",
            difficulty="intermediate",
            grade=diagram.grade_level,
            session=session,
        )
    except Exception as e:
        logger.error("auto_label_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Label generation failed: {e}")
    finally:
        await router_llm.close()

    labels = result.get("labels", [])
    diagram.ground_truth_labels = {"labels": labels}
    await session.commit()

    return AutoLabelResponse(
        diagram_id=str(diagram.id),
        caption=diagram.caption or "",
        labels_count=len(labels),
        labels=[DiagramLabel(**lb) for lb in labels],
    )


@router.post("/textbook/auto-label-batch", response_model=AutoLabelBatchResponse)
async def auto_label_batch(
    grade: Optional[int] = Query(None, ge=7, le=12),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(TextbookDiagram).where(TextbookDiagram.ground_truth_labels.is_(None))
    if grade:
        stmt = stmt.where(TextbookDiagram.grade_level == grade)
    stmt = stmt.limit(50)
    result = await session.execute(stmt)
    diagrams = result.scalars().all()

    processed = 0
    skipped = 0
    results_list: list[AutoLabelResponse] = []

    router_llm = ModelRouter()
    agent = DiagramAgent(llm_router=router_llm)
    try:
        for diagram in diagrams:
            try:
                gen_result = await agent.generate(
                    prompt=diagram.caption or diagram.topic,
                    topic=diagram.topic or "biology",
                    difficulty="intermediate",
                    grade=diagram.grade_level,
                    session=session,
                )
                labels = gen_result.get("labels", [])
                diagram.ground_truth_labels = {"labels": labels}
                results_list.append(
                    AutoLabelResponse(
                        diagram_id=str(diagram.id),
                        caption=diagram.caption or "",
                        labels_count=len(labels),
                        labels=[DiagramLabel(**lb) for lb in labels],
                    )
                )
                processed += 1
            except Exception as e:
                logger.warning("auto_label_item_error", diagram_id=str(diagram.id), error=str(e))
                skipped += 1
        await session.commit()
    finally:
        await router_llm.close()

    return AutoLabelBatchResponse(processed=processed, skipped=skipped, results=results_list)


_icon_library: IconLibrary | None = None


def _get_icon_library() -> IconLibrary:
    global _icon_library
    if _icon_library is None:
        _icon_library = IconLibrary()
    return _icon_library


@router.get("/icons", response_model=IconListResponse)
async def list_icons(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    lib = _get_icon_library()
    icons, total = lib.get_icons(category=category, search=search, limit=limit, offset=offset)
    return IconListResponse(
        total=total,
        icons=icons,
        categories=lib.get_categories(),
    )


@router.get("/icons/{icon_id}")
async def get_icon_svg(icon_id: str):
    lib = _get_icon_library()
    svg = lib.get_icon_svg(icon_id)
    if svg is None:
        raise HTTPException(status_code=404, detail=f"Icon '{icon_id}' not found")
    return PlainTextResponse(svg, media_type="image/svg+xml")


@router.post("/compose", response_model=IconComposeResponse)
async def compose_diagram(request: IconComposeRequest):
    lib = _get_icon_library()
    title = request.title or f"{request.topic} Diagram"
    svg = lib.compose_from_topic(
        topic=request.topic,
        icon_ids=request.icon_ids,
        title=title,
    )
    return IconComposeResponse(
        diagram_svg=svg,
        title=title,
        topic=request.topic,
        placed_icons=len(request.icon_ids),
    )


@router.post("/export")
async def export_diagram(request: DiagramExportRequest):
    labels_data = [label.model_dump() for label in request.labels]
    try:
        if request.format == "docx":
            content = export_diagram_to_docx(
                svg=request.svg,
                title=request.title,
                topic=request.topic,
                grade=request.grade,
                labels=labels_data,
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"diagram_{request.topic.replace(' ', '_')}.docx"
        else:
            content = export_diagram_to_pdf(
                svg=request.svg,
                title=request.title,
                topic=request.topic,
                grade=request.grade,
                labels=labels_data,
            )
            media_type = "application/pdf"
            filename = f"diagram_{request.topic.replace(' ', '_')}.pdf"
    except Exception as e:
        logger.error("diagram_export_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/sketch", response_model=SketchToDiagramResponse)
async def sketch_to_diagram(
    file: UploadFile = File(...),
    topic: str = Form("biology"),
    prompt: str = Form("Transform this biology sketch into a clean educational diagram"),
):
    from src.config import Settings

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="No image uploaded")

    settings = Settings()
    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=501,
            detail="Cloudflare image generation not configured",
        )

    generator = CloudflareImageGenerator.from_settings(settings)
    try:
        enhanced = await generator.image_to_image(
            prompt=prompt,
            input_image=image_bytes,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    encoded = base64.b64encode(enhanced).decode("utf-8")
    return SketchToDiagramResponse(
        image_base64=encoded,
        topic=topic,
        prompt=prompt,
        model_used=generator.default_model,
    )


@router.post("/style-transfer", response_model=StyleTransferResponse)
async def style_transfer(request: StyleTransferRequest):
    try:
        png_bytes = render_svg_to_png(request.svg)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"SVG rendering failed: {e}")

    from src.config import Settings

    settings = Settings()
    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=501,
            detail="Cloudflare image generation not configured",
        )

    generator = CloudflareImageGenerator.from_settings(settings)
    try:
        result = await generator.image_to_image(
            prompt=request.prompt,
            input_image=png_bytes,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    encoded = base64.b64encode(result).decode("utf-8")
    return StyleTransferResponse(
        image_base64=encoded,
        prompt=request.prompt,
    )
