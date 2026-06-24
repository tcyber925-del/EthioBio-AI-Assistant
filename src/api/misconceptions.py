from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.misconception_intelligence import (
    HeuristicDetector,
    KnowledgeBaseService,
    MisconceptionGraphIntegrator,
    MisconceptionProfiler,
    SemanticDetector,
)
from src.database.models import MisconceptionKnowledgeEntry, MisconceptionPattern
from src.database.session import get_session
from src.schemas.misconception_classroom import (
    ClassroomMisconceptionHeatmap,
    ClassroomMisconceptionTopic,
)
from src.schemas.misconception_graph import (
    MisconceptionCascadeNode,
    PrerequisiteGap,
    TopicMisconceptionWeight,
)
from src.schemas.misconception_kb import (
    ClassifyMisconceptionRequest,
    MisconceptionClassificationResult,
    MisconceptionKBEntry,
    MisconceptionKBEntryCreate,
    SeverityDefinition,
)
from src.schemas.misconception_semantic import (
    SemanticAnalysisRequest,
    SemanticAnalysisResult,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/misconceptions", tags=["Misconceptions"])

profiler = MisconceptionProfiler()
detector = HeuristicDetector()
kb_service = KnowledgeBaseService()
semantic_detector = SemanticDetector()
graph_integrator = MisconceptionGraphIntegrator()


class MisconceptionDetail(BaseModel):
    id: UUID
    topic: str
    pattern_type: str
    description: str
    severity: str = "misunderstanding"
    frequency: int
    confidence: float = 0.0
    common_wrong_answer: str | None = None
    last_detected_at: str | None = None
    resolved: bool = False


class MisconceptionListResponse(BaseModel):
    misconceptions: list[MisconceptionDetail]
    total: int = 0


class MisconceptionTopicSummary(BaseModel):
    topic: str
    count: int
    patterns: list[MisconceptionDetail] = []


class MisconceptionProfileResponse(BaseModel):
    total_patterns: int
    unresolved_count: int
    by_topic: list[MisconceptionTopicSummary]
    frequent_patterns: list[MisconceptionDetail]
    improvement_trend: str


class AnalyzeTextRequest(BaseModel):
    text: str


class AnalyzeTextResponse(BaseModel):
    has_misconception: bool
    correction_text: str = ""


class ResolveResponse(BaseModel):
    resolved: bool


@router.get("/{user_id}", response_model=MisconceptionListResponse)
async def list_misconceptions(
    user_id: UUID,
    resolved: bool | None = False,
    topic: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        stmt = select(MisconceptionPattern).where(
            MisconceptionPattern.user_id == user_id,
        )
        if resolved is not None:
            stmt = stmt.where(MisconceptionPattern.resolved.is_(resolved))
        if topic:
            stmt = stmt.where(MisconceptionPattern.topic == topic)
        stmt = stmt.order_by(MisconceptionPattern.last_detected_at.desc())

        result = await db.execute(stmt)
        patterns = list(result.scalars().all())

        return MisconceptionListResponse(
            misconceptions=[
                MisconceptionDetail(
                    id=p.id,
                    topic=p.topic,
                    pattern_type=p.pattern_type,
                    description=p.pattern_description,
                    severity=p.severity,
                    frequency=p.frequency,
                    confidence=p.confidence,
                    common_wrong_answer=p.common_wrong_answer,
                    last_detected_at=str(p.last_detected_at),
                    resolved=p.resolved,
                )
                for p in patterns
            ],
            total=len(patterns),
        )
    except Exception as e:
        logger.error("misconceptions_list_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/profile", response_model=MisconceptionProfileResponse)
async def get_misconception_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        profile = await profiler.get_student_profile(user_id=user_id, db=db)
        return MisconceptionProfileResponse(
            total_patterns=profile.total_patterns,
            unresolved_count=profile.unresolved_count,
            by_topic=[
                MisconceptionTopicSummary(
                    topic=t["topic"],
                    count=t["count"],
                    patterns=[
                        MisconceptionDetail(
                            id=UUID(p["id"]),
                            topic=t["topic"],
                            pattern_type=p["pattern_type"],
                            description=p["description"],
                            severity=p.get("severity", "misunderstanding"),
                            frequency=p["frequency"],
                            confidence=p.get("confidence", 0.0),
                            common_wrong_answer=p.get("common_wrong_answer"),
                            last_detected_at=p.get("last_detected_at"),
                        )
                        for p in t["patterns"]
                    ],
                )
                for t in profile.by_topic
            ],
            frequent_patterns=[
                MisconceptionDetail(
                    id=UUID(p["id"]),
                    topic=p["topic"],
                    pattern_type="",
                    description=p["description"],
                    severity=p.get("severity", "misunderstanding"),
                    frequency=p["frequency"],
                    confidence=p.get("confidence", 0.0),
                )
                for p in profile.frequent_patterns
            ],
            improvement_trend=profile.improvement_trend,
        )
    except Exception as e:
        logger.error("misconception_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(body: AnalyzeTextRequest):
    has_misconception, correction = detector.detect_in_text(body.text)
    return AnalyzeTextResponse(
        has_misconception=has_misconception,
        correction_text=correction,
    )


@router.post("/{pattern_id}/resolve", response_model=ResolveResponse)
async def resolve_misconception(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        success = await profiler.resolve_pattern(pattern_id=pattern_id, db=db)
        await db.commit()
        if not success:
            raise HTTPException(status_code=404, detail="Misconception pattern not found")
        return ResolveResponse(resolved=True)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("misconception_resolve_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-topic/{user_id}/{topic}", response_model=ResolveResponse)
async def resolve_topic_misconceptions(
    user_id: UUID,
    topic: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        count = await profiler.resolve_by_topic(user_id=user_id, topic=topic, db=db)
        await db.commit()
        return ResolveResponse(resolved=count > 0)
    except Exception as e:
        await db.rollback()
        logger.error("misconception_resolve_topic_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic-analyze", response_model=SemanticAnalysisResult)
async def semantic_analysis(body: SemanticAnalysisRequest):
    try:
        result = await semantic_detector.analyze(
            topic=body.topic,
            wrong_answer=body.wrong_answer,
            correct_answer=body.correct_answer,
            question_text=body.question_text,
        )
        return SemanticAnalysisResult(
            has_misconception=result["has_misconception"],
            misconception=result.get("misconception"),
            misconception_type=result.get("misconception_type"),
            explanation=result.get("explanation", ""),
            confidence=result.get("confidence", 0.0),
            related_patterns=result.get("related_patterns", []),
        )
    except Exception as e:
        logger.error("semantic_analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/prerequisite-gaps/{topic}", response_model=list[PrerequisiteGap])
async def get_prerequisite_misconception_gaps(
    user_id: UUID,
    topic: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        return await graph_integrator.get_prerequisite_gaps(
            user_id=user_id, topic=topic, db=db,
        )
    except Exception as e:
        logger.error("prerequisite_gaps_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/cascade", response_model=list[MisconceptionCascadeNode])
async def get_misconception_cascade(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        return await graph_integrator.get_misconception_cascade(
            user_id=user_id, db=db,
        )
    except Exception as e:
        logger.error("misconception_cascade_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topic-weights", response_model=list[TopicMisconceptionWeight])
async def get_topic_misconception_weights(
    grade_level: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        return await graph_integrator.get_topic_misconception_weight(
            db=db, grade_level=grade_level,
        )
    except Exception as e:
        logger.error("topic_weights_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/seed", response_model=dict)
async def seed_knowledge_base(db: AsyncSession = Depends(get_session)):
    count = await kb_service.ensure_seeded(db)
    await db.commit()
    return {"seeded": count}


@router.get("/kb/entries", response_model=list[MisconceptionKBEntry])
async def list_kb_entries(
    topic: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    await kb_service.ensure_seeded(db)
    await db.commit()
    entries = await kb_service.list_by_topic(db, topic=topic)
    return [
        MisconceptionKBEntry(
            id=e.id,
            topic=e.topic,
            misconception=e.misconception,
            explanation=e.explanation,
            severity=e.severity,
            related_objectives=list(e.related_objectives or []),
            recommended_strategies=list(e.recommended_strategies or []),
            detection_patterns=list(e.detection_patterns or []),
            grade_level=e.grade_level,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in entries
    ]


@router.get("/kb/topics", response_model=list[str])
async def list_kb_topics(db: AsyncSession = Depends(get_session)):
    await kb_service.ensure_seeded(db)
    await db.commit()
    return await kb_service.get_topics(db)


@router.get("/kb/severities", response_model=list[SeverityDefinition])
async def list_severities():
    sevs = kb_service.get_severities()
    return [
        SeverityDefinition(key=k, label=v["label"], rank=v["rank"], description=v["description"])
        for k, v in sevs.items()
    ]


@router.post("/kb/classify", response_model=MisconceptionClassificationResult)
async def classify_misconception(
    body: ClassifyMisconceptionRequest,
    db: AsyncSession = Depends(get_session),
):
    result = await kb_service.classify(db, topic=body.topic, wrong_answer=body.wrong_answer)
    if result:
        return MisconceptionClassificationResult(
            entry_id=result["entry_id"],
            misconception=result["misconception"],
            explanation=result["explanation"],
            severity=result["severity"],
            recommended_strategies=result["recommended_strategies"],
            match_confidence=result["match_confidence"],
            matched=True,
        )
    return MisconceptionClassificationResult(matched=False)


@router.post("/kb/entries", response_model=MisconceptionKBEntry, status_code=201)
async def create_kb_entry(
    body: MisconceptionKBEntryCreate,
    db: AsyncSession = Depends(get_session),
):
    entry = MisconceptionKnowledgeEntry(**body.model_dump())
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return MisconceptionKBEntry(
        id=entry.id,
        topic=entry.topic,
        misconception=entry.misconception,
        explanation=entry.explanation,
        severity=entry.severity,
        related_objectives=list(entry.related_objectives or []),
        recommended_strategies=list(entry.recommended_strategies or []),
        detection_patterns=list(entry.detection_patterns or []),
        grade_level=entry.grade_level,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/classroom/{classroom_id}/heatmap", response_model=ClassroomMisconceptionHeatmap)
async def get_classroom_misconception_heatmap(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    data = await profiler.get_classroom_heatmap(classroom_id=classroom_id, db=db)
    return ClassroomMisconceptionHeatmap(
        classroom_id=UUID(data["classroom_id"]),
        total_students=data["total_students"],
        students_with_misconceptions=data["students_with_misconceptions"],
        total_unresolved_patterns=data["total_unresolved_patterns"],
        by_topic=[
            ClassroomMisconceptionTopic(**t) for t in data["by_topic"]
        ],
        improvement_trend=data["improvement_trend"],
        generated_at=data["generated_at"],
    )
