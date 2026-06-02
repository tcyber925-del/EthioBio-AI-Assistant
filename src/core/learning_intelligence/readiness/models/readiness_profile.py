from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TopicReadiness(BaseModel):
    topic: str
    readiness_score: float
    risk_level: str  # LOW / MODERATE / HIGH / CRITICAL
    risk_factors: list[str]
    review_status: str  # current / overdue


class ExamReadinessProfile(BaseModel):
    user_id: UUID
    generated_at: datetime
    overall_readiness: float  # 0-100
    readiness_band: str  # Critical / Developing / Ready / Strong
    topic_readiness: list[TopicReadiness]
    risk_topics: list[str]
