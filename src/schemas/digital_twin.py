from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class DigitalTwinResponse(SchemaModel):
    user_id: UUID
    knowledge_state: dict = {}
    mastery_state: dict = {}
    misconception_state: dict = {}
    retention_state: dict = {}
    readiness_state: dict = {}
    intervention_state: dict = {}
    overall_health: str = "unknown"
    confidence: float = 0.0
    last_built_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class DigitalTwinDashboardResponse(SchemaModel):
    user_id: UUID
    overall_health: str = "unknown"
    dimension_summary: dict = {}
    risk_indicators: list[dict] = []
    last_built_at: Optional[str] = None


class ForecastResponse(SchemaModel):
    user_id: str
    weeks_ahead: int
    generated_at: str
    mastery: list[dict] = []
    retention: list[dict] = []
    readiness: dict = {}
    risk: list[dict] = []


class MasteryForecastResponse(SchemaModel):
    topic: str
    current: float = 0.0
    projected: float = 0.0
    trend: str = "unknown"
    confidence: str = "low"
    data_points: int = 0


class SimulationAction(SchemaModel):
    type: str
    topic: str = ""
    value: float = 0.0


class SimulationResponse(SchemaModel):
    user_id: str
    weeks_ahead: int
    baseline: dict = {}
    simulated: Optional[dict] = None
    actions: list[dict] = []
