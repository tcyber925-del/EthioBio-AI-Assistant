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
