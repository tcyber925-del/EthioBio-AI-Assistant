from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.learning_intelligence.readiness.models.intervention import (
    Intervention,
)


class StudentRisk(BaseModel):
    student_id: UUID
    readiness_score: float
    risk_level: str
    risk_factors: list[str]
    recommended_action: str


class ClassroomProfile(BaseModel):
    classroom_id: UUID
    generated_at: datetime
    total_students: int
    classroom_health: float
    readiness_distribution: dict[str, int]
    risk_students: list[StudentRisk]
    intervention_candidates: list[Intervention]
    mastery_heatmap: dict[str, float]
