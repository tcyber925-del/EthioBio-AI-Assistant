from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.intervention.knowledge_base import InterventionKnowledgeBase
from src.core.intervention.learning_engine import InterventionLearningEngine
from src.core.intervention.service import InterventionService
from src.core.learning_intelligence.readiness import ReadinessService
from src.database.models import InterventionAssignment, InterventionKnowledgeEntry
from src.database.session import get_session
from src.schemas.intervention import (
    EffectivenessComponents,
    EffectivenessResponse,
    InterventionAnalytics,
    InterventionAnalyticsDashboard,
    InterventionComparison,
    InterventionCreate,
    InterventionLeaderboardEntry,
    InterventionResponse,
    InterventionTrendPoint,
    InterventionUpdate,
    LearnedEffectivenessResponse,
    TypeComparisonMetrics,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/interventions", tags=["Interventions"])
service = InterventionService()


def _to_response(record) -> InterventionResponse:
    return InterventionResponse(
        id=record.id,
        user_id=record.user_id,
        classroom_id=record.classroom_id,
        teacher_id=record.teacher_id,
        intervention_type=record.intervention_type,
        topic=record.topic,
        status=record.status,
        priority=record.priority,
        estimated_impact=record.estimated_impact,
        effectiveness_score=record.effectiveness_score,
        notes=record.notes,
        assigned_at=record.assigned_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


@router.post("", response_model=InterventionResponse, status_code=201)
async def create_intervention(
    body: InterventionCreate,
    session: AsyncSession = Depends(get_session),
):
    record = await service.create(body, session)
    await session.commit()
    return _to_response(record)


@router.put("/{intervention_id}", response_model=InterventionResponse)
async def update_intervention(
    intervention_id: str,
    body: InterventionUpdate,
    session: AsyncSession = Depends(get_session),
):
    record = await service.update(intervention_id, body, session)
    if not record:
        raise HTTPException(status_code=404, detail="Intervention not found")
    await session.commit()
    return _to_response(record)


@router.get("", response_model=list[InterventionResponse])
async def list_interventions(
    user_id: str | None = Query(None),
    classroom_id: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    if user_id:
        records = await service.list_for_user(user_id, session, status)
    elif classroom_id:
        records = await service.list_for_classroom(classroom_id, session, status)
    else:
        records = []
    return [_to_response(r) for r in records]


@router.post("/{intervention_id}/effectiveness", response_model=InterventionResponse)
async def compute_effectiveness(
    intervention_id: str,
    session: AsyncSession = Depends(get_session),
):
    score = await service.compute_effectiveness(intervention_id, session)
    if score is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot compute effectiveness. "
                "Ensure intervention has a topic and "
                "pre/post mastery data exists."
            ),
        )
    await session.commit()
    record = await service.get(intervention_id, session)
    return _to_response(record)


@router.post("/{intervention_id}/effectiveness-weighted", response_model=EffectivenessResponse)
async def compute_weighted_effectiveness(
    intervention_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await service.compute_weighted_effectiveness(intervention_id, session)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot compute weighted effectiveness. "
                "Ensure intervention has a topic and "
                "pre/post data exists."
            ),
        )
    await session.commit()
    return EffectivenessResponse(
        total_score=result["total_score"],
        components=EffectivenessComponents(**result["components"]),
        confidence=result.get("confidence", 1.0),
        sample_size=result.get("sample_size", 0),
    )


@router.get("/kb/query", response_model=list[dict])
async def query_intervention_kb(
    intervention_type: str | None = Query(None),
    topic: str | None = Query(None),
    min_effectiveness: float | None = Query(None),
    max_results: int = Query(20),
    session: AsyncSession = Depends(get_session),
):
    kb = InterventionKnowledgeBase()
    entries = await kb.query(
        session=session,
        intervention_type=intervention_type,
        topic=topic,
        min_effectiveness=min_effectiveness,
        max_results=max_results,
    )
    return [
        {
            "id": str(e.id),
            "intervention_type": e.intervention_type,
            "topic": e.topic,
            "effectiveness_score": e.effectiveness_score,
            "mastery_change": e.mastery_change,
            "readiness_change": e.readiness_change,
            "retention_change": e.retention_change,
            "misconception_reduction": e.misconception_reduction,
            "pre_mastery_score": e.pre_mastery_score,
            "post_mastery_score": e.post_mastery_score,
            "completion_days": e.completion_days,
            "completed_at": str(e.completed_at),
        }
        for e in entries
    ]


@router.get("/kb/summary")
async def intervention_kb_summary(
    session: AsyncSession = Depends(get_session),
):
    kb = InterventionKnowledgeBase()
    return await kb.get_effectiveness_summary(session=session)


@router.get("/analytics/summary", response_model=InterventionAnalytics)
async def intervention_analytics(
    user_id: str | None = Query(None),
    teacher_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_analytics(session, user_id=user_id, teacher_id=teacher_id)


@router.post("/from-readiness/{user_id}", response_model=list[InterventionResponse])
async def create_from_readiness(
    user_id: str,
    teacher_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    readiness = ReadinessService()
    profile = await readiness.get_readiness(session, UUID(user_id))
    if not profile.recommended_interventions:
        return []
    records = await service.persist_planned(
        interventions=profile.recommended_interventions,
        user_id=user_id,
        session=session,
        teacher_id=teacher_id,
    )
    await session.commit()
    return [_to_response(r) for r in records]


@router.get("/learning-insights", response_model=LearnedEffectivenessResponse)
async def get_learning_insights(
    session: AsyncSession = Depends(get_session),
):
    learner = InterventionLearningEngine(session)
    eff_by_type = await learner.get_effectiveness_by_type()
    if not eff_by_type:
        return LearnedEffectivenessResponse(
            effectiveness_by_type={},
            global_average=0.0,
            top_recommended_type=None,
            learned_boost=0.0,
        )
    global_avg = round(sum(eff_by_type.values()) / len(eff_by_type), 1)
    top_type = max(eff_by_type, key=lambda k: eff_by_type[k])  # type: ignore[arg-type]
    boost = min((sorted(eff_by_type.values(), reverse=True)[0] - global_avg) / 100, 0.5)
    boost = max(0.0, boost)
    return LearnedEffectivenessResponse(
        effectiveness_by_type=eff_by_type,
        global_average=global_avg,
        top_recommended_type=top_type,
        learned_boost=round(boost, 3),
    )


@router.get("/analytics/leaderboard", response_model=list[InterventionLeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    return await _get_leaderboard_data(limit, session)


async def _get_leaderboard_data(
    limit: int = 10,
    session: AsyncSession | None = None,
):
    result = await session.execute(
        select(
            InterventionAssignment.id,
            InterventionAssignment.intervention_type,
            InterventionAssignment.topic,
            InterventionAssignment.effectiveness_score,
            InterventionAssignment.completed_at,
        )
        .where(InterventionAssignment.effectiveness_score.isnot(None))
        .order_by(InterventionAssignment.effectiveness_score.desc())
        .limit(limit)
    )
    return [
        InterventionLeaderboardEntry(
            id=row.id,
            intervention_type=row.intervention_type,
            topic=row.topic,
            effectiveness_score=row.effectiveness_score,
            completion_days=None,
            completed_at=str(row.completed_at) if row.completed_at else None,
        )
        for row in result.fetchall()
    ]


@router.get("/analytics/trends", response_model=list[InterventionTrendPoint])
async def get_effectiveness_trends(
    months: int = Query(6, ge=1, le=24),
    session: AsyncSession = Depends(get_session),
):
    return await _get_effectiveness_trends_data(months, session)


async def _get_effectiveness_trends_data(
    months: int = 6,
    session: AsyncSession | None = None,
):
    result = await session.execute(
        select(
            func.date_trunc("month", InterventionAssignment.completed_at).label("period"),
            func.avg(InterventionAssignment.effectiveness_score).label("avg_effectiveness"),
            func.count().label("count"),
        )
        .where(InterventionAssignment.effectiveness_score.isnot(None))
        .where(InterventionAssignment.completed_at.isnot(None))
        .where(
            InterventionAssignment.completed_at >= sa_text(f"now() - interval '{months} months'")
        )
        .group_by(sa_text("period"))
        .order_by(sa_text("period"))
    )
    return [
        InterventionTrendPoint(
            period=str(row.period),
            avg_effectiveness=round(float(row.avg_effectiveness), 1),
            count=int(row.count),  # type: ignore[call-overload]
        )
        for row in result.fetchall()
    ]


@router.get("/analytics/compare", response_model=InterventionComparison)
async def compare_intervention_types(
    types: str = Query(..., description="Comma-separated intervention types"),
    topic: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    return await _compare_intervention_types_data(types, topic, session)


async def _compare_intervention_types_data(
    types: str,
    topic: str | None = None,
    session: AsyncSession | None = None,
):
    type_list = [t.strip() for t in types.split(",") if t.strip()]
    if not type_list:
        raise HTTPException(status_code=400, detail="At least one intervention type required")

    stmt = select(
        InterventionKnowledgeEntry.intervention_type,
        func.count().label("cnt"),
        func.avg(InterventionKnowledgeEntry.effectiveness_score).label("avg_eff"),
        func.avg(InterventionKnowledgeEntry.mastery_change).label("avg_mastery"),
        func.avg(InterventionKnowledgeEntry.readiness_change).label("avg_readiness"),
        func.avg(InterventionKnowledgeEntry.retention_change).label("avg_retention"),
        func.avg(InterventionKnowledgeEntry.misconception_reduction).label("avg_miscon"),
        func.avg(InterventionKnowledgeEntry.completion_days).label("avg_days"),
    ).where(InterventionKnowledgeEntry.intervention_type.in_(type_list))

    if topic:
        stmt = stmt.where(InterventionKnowledgeEntry.topic == topic)

    stmt = stmt.group_by(InterventionKnowledgeEntry.intervention_type)

    result = await session.execute(stmt)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No KB entries found for the given types")

    metrics = [
        TypeComparisonMetrics(
            intervention_type=row.intervention_type,
            count=int(row.cnt),
            avg_effectiveness=round(float(row.avg_eff), 1) if row.avg_eff else 0.0,
            avg_mastery_change=round(float(row.avg_mastery), 3) if row.avg_mastery else None,
            avg_readiness_change=round(float(row.avg_readiness), 3) if row.avg_readiness else None,
            avg_retention_change=round(float(row.avg_retention), 3) if row.avg_retention else None,
            avg_misconception_reduction=round(float(row.avg_miscon), 3) if row.avg_miscon else None,
            avg_completion_days=round(float(row.avg_days), 1) if row.avg_days else None,
        )
        for row in rows
    ]

    return InterventionComparison(types=metrics)


@router.get("/analytics/dashboard", response_model=InterventionAnalyticsDashboard)
async def get_analytics_dashboard(
    teacher_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    try:
        teacher_id_str: str | None = teacher_id
        summary_raw = await service.get_analytics(
            session=session,
            teacher_id=teacher_id_str,
        )
        summary = InterventionAnalytics(**summary_raw)
        leaderboard = await _get_leaderboard_data(session=session)
        learner = InterventionLearningEngine(session)
        eff_by_type = await learner.get_effectiveness_by_type()
        if eff_by_type:
            global_avg = round(sum(eff_by_type.values()) / len(eff_by_type), 1)
            top_type = max(eff_by_type, key=lambda k: eff_by_type[k])  # type: ignore[arg-type]
            boost = min((sorted(eff_by_type.values(), reverse=True)[0] - global_avg) / 100, 0.5)
            learning_insights = LearnedEffectivenessResponse(
                effectiveness_by_type=eff_by_type,
                global_average=global_avg,
                top_recommended_type=top_type,
                learned_boost=max(0.0, boost),
            )
        else:
            learning_insights = None
        trends = await _get_effectiveness_trends_data(session=session)

        all_types = list(summary.effectiveness_by_type.keys())
        comparison = None
        if len(all_types) >= 2:
            try:
                comparison = await _compare_intervention_types_data(
                    types=",".join(all_types),
                    session=session,
                )
            except Exception:
                logger.warning("comparison_fetch_failed", exc_info=True)

        kb_count_result = await session.execute(
            select(func.count()).select_from(InterventionKnowledgeEntry)
        )
        total_kb_entries = kb_count_result.scalar() or 0
        overall_confidence = round(min(total_kb_entries / (total_kb_entries + 20), 1.0), 3)

        return InterventionAnalyticsDashboard(
            summary=summary,
            leaderboard=leaderboard,
            learning_insights=learning_insights,
            trends=trends,
            comparison=comparison,
            overall_confidence=overall_confidence,
            total_kb_entries=total_kb_entries,
        )
    except Exception:
        logger.exception("dashboard_failed")
        raise


@router.get("/{intervention_id}", response_model=InterventionResponse)
async def get_intervention(
    intervention_id: str,
    session: AsyncSession = Depends(get_session),
):
    record = await service.get(intervention_id, session)
    if not record:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return _to_response(record)
