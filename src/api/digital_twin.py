import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin import ForecastingEngine, SimulationEngine, TwinBuilder
from src.database.models import StudentDigitalTwin
from src.database.session import get_session
from src.schemas.digital_twin import (
    DigitalTwinDashboardResponse,
    DigitalTwinResponse,
    ForecastResponse,
    MasteryForecastResponse,
    SimulationAction,
    SimulationResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])


@router.get("/{user_id}", response_model=DigitalTwinResponse)
async def get_twin(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")
    return _twin_to_response(twin)


@router.post("/{user_id}/rebuild", response_model=DigitalTwinResponse)
async def rebuild_twin(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    builder = TwinBuilder(session)
    try:
        await builder.rebuild(user_id)
    except Exception as e:
        logger.error("twin_rebuild_error", user_id=str(user_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {e}")

    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=500, detail="Twin not found after rebuild")
    return _twin_to_response(twin)


@router.get("/{user_id}/dashboard", response_model=DigitalTwinDashboardResponse)
async def get_twin_dashboard(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    twin = await session.get(StudentDigitalTwin, user_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")

    dims = {
        "knowledge": twin.knowledge_state,
        "mastery": twin.mastery_state,
        "misconceptions": twin.misconception_state,
        "retention": twin.retention_state,
        "readiness": twin.readiness_state,
        "interventions": twin.intervention_state,
    }
    summary = {}
    for name, val in dims.items():
        if val and isinstance(val, dict):
            if name == "misconceptions":
                summary[name] = {
                    "active": val.get("total_active", 0),
                    "resolved": val.get("total_resolved", 0),
                }
            elif name == "interventions":
                summary[name] = {
                    "active": val.get("active_count", 0),
                    "completed": val.get("completed_count", 0),
                }
            else:
                summary[name] = {
                    "score": val.get("overall", 0),
                }

    risk_indicators = _build_risk_indicators(twin)

    return DigitalTwinDashboardResponse(
        user_id=user_id,
        overall_health=twin.overall_health or "unknown",
        dimension_summary=summary,
        risk_indicators=risk_indicators,
        last_built_at=twin.last_built_at.isoformat() if twin.last_built_at else None,
    )


@router.get("/{user_id}/forecast", response_model=ForecastResponse)
async def get_twin_forecast(
    user_id: uuid.UUID,
    weeks_ahead: int = 4,
    session: AsyncSession = Depends(get_session),
):
    engine = ForecastingEngine(session)
    forecast = await engine.forecast_all(user_id, weeks_ahead)
    return ForecastResponse(**forecast)


@router.get("/{user_id}/forecast/mastery/{topic}", response_model=MasteryForecastResponse)
async def get_mastery_forecast(
    user_id: uuid.UUID,
    topic: str,
    weeks_ahead: int = 4,
    session: AsyncSession = Depends(get_session),
):
    engine = ForecastingEngine(session)
    result = await engine.forecast_mastery_topic(user_id, topic, weeks_ahead)
    return MasteryForecastResponse(**result)


@router.post("/{user_id}/simulate", response_model=SimulationResponse)
async def simulate_twin_scenario(
    user_id: uuid.UUID,
    actions: list[SimulationAction],
    weeks_ahead: int = 4,
    session: AsyncSession = Depends(get_session),
):
    engine = SimulationEngine(session)
    result = await engine.simulate(
        user_id,
        [a.model_dump() for a in actions],
        weeks_ahead,
    )
    return SimulationResponse(**result)


def _twin_to_response(twin: StudentDigitalTwin) -> DigitalTwinResponse:
    return DigitalTwinResponse(
        user_id=twin.user_id,
        knowledge_state=twin.knowledge_state or {},
        mastery_state=twin.mastery_state or {},
        misconception_state=twin.misconception_state or {},
        retention_state=twin.retention_state or {},
        readiness_state=twin.readiness_state or {},
        intervention_state=twin.intervention_state or {},
        overall_health=twin.overall_health or "unknown",
        confidence=twin.confidence or 0.0,
        last_built_at=twin.last_built_at.isoformat() if twin.last_built_at else None,
        created_at=twin.created_at.isoformat() if twin.created_at else "",
        updated_at=twin.updated_at.isoformat() if twin.updated_at else "",
    )


def _build_risk_indicators(twin: StudentDigitalTwin) -> list[dict]:
    indicators: list[dict] = []

    mc = twin.misconception_state or {}
    for topic, patterns in mc.get("topics", {}).items():
        for pattern in patterns:
            if pattern.get("severity") in ("misconception", "persistent_misconception"):
                indicators.append(
                    {
                        "topic": topic,
                        "type": "misconception",
                        "severity": pattern.get("severity", "medium"),
                        "detail": pattern.get("pattern", "")[:100],
                    }
                )

    rt = twin.retention_state or {}
    for topic, data in rt.get("topics", {}).items():
        if isinstance(data, dict) and data.get("forgetting_risk") == "high":
            indicators.append(
                {
                    "topic": topic,
                    "type": "retention",
                    "severity": "high",
                    "detail": f"No review in {data.get('days_since_review', '?')} days",
                }
            )

    rd = twin.readiness_state or {}
    for topic, data in rd.get("topics", {}).items():
        if isinstance(data, dict) and data.get("risk_level") == "high":
            indicators.append(
                {
                    "topic": topic,
                    "type": "readiness",
                    "severity": "high",
                    "detail": f"Readiness score: {data.get('readiness_score', 0)}",
                }
            )

    return indicators
