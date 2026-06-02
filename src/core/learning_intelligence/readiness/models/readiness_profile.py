from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.learning_intelligence.readiness.models.intervention import (
    Intervention,
)


class TopicReadiness(BaseModel):
    topic: str
    readiness_score: float
    risk_level: str  # LOW / MODERATE / HIGH / CRITICAL
    risk_factors: list[str]
    review_status: str  # current / overdue
    forgetting_risk: float | None = None  # 0.0-1.0


class ExamReadinessProfile(BaseModel):
    user_id: UUID
    generated_at: datetime
    overall_readiness: float  # 0-100
    readiness_band: str  # Critical / Developing / Ready / Strong
    topic_readiness: list[TopicReadiness]
    risk_topics: list[str]
    confidence_score: float = 0.5  # 0.0-1.0, confidence in prediction
    projected_exam_score: float = 0.0  # 0-100
    recommended_interventions: list[Intervention] = []
