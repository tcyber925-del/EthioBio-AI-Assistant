from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class InterventionCreate(SchemaModel):
    user_id: UUID
    classroom_id: Optional[UUID] = None
    teacher_id: Optional[UUID] = None
    intervention_type: str = Field(
        ...,
        pattern=(
            "^(REVIEW_TOPIC|REVISE_MISCONCEPTION|RECOVERY_PLAN"
            "|TAKE_QUIZ|EXAM_PRACTICE|TUTOR_SESSION"
            "|ENGAGEMENT_BOOST)$"
        ),
    )
    topic: Optional[str] = None
    priority: float = Field(0.5, ge=0.0, le=1.0)
    estimated_impact: float = Field(0.0, ge=0.0, le=100.0)
    notes: Optional[str] = None


class InterventionUpdate(SchemaModel):
    status: Optional[str] = Field(None, pattern="^(planned|active|completed|cancelled)$")
    effectiveness_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = None


class InterventionResponse(SchemaModel):
    id: UUID
    user_id: UUID
    classroom_id: Optional[UUID]
    teacher_id: Optional[UUID]
    intervention_type: str
    topic: Optional[str]
    status: str
    priority: float
    estimated_impact: float
    effectiveness_score: Optional[float]
    notes: Optional[str]
    assigned_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class EffectivenessComponents(SchemaModel):
    mastery_change: float
    readiness_change: float
    retention_change: float
    misconception_reduction: float


class EffectivenessResponse(SchemaModel):
    total_score: float
    components: EffectivenessComponents
    confidence: float = 1.0
    sample_size: int = 0


class InterventionAnalytics(SchemaModel):
    total_interventions: int
    completed_count: int
    active_count: int
    completion_rate: float
    average_effectiveness: float
    effectiveness_by_type: dict[str, float]
    effectiveness_by_topic: dict[str, float]
    effectiveness_weights: dict[str, float] = {}
    trend: list[dict] = []


class LearnedEffectivenessResponse(SchemaModel):
    effectiveness_by_type: dict[str, float]
    global_average: float
    top_recommended_type: str | None
    learned_boost: float


class InterventionLeaderboardEntry(SchemaModel):
    id: UUID
    intervention_type: str
    topic: str | None
    effectiveness_score: float | None
    completion_days: int | None
    completed_at: str | None


class InterventionTrendPoint(SchemaModel):
    period: str
    avg_effectiveness: float
    count: int


class TypeComparisonMetrics(SchemaModel):
    intervention_type: str
    count: int
    avg_effectiveness: float
    avg_mastery_change: float | None = None
    avg_readiness_change: float | None = None
    avg_retention_change: float | None = None
    avg_misconception_reduction: float | None = None
    avg_completion_days: float | None = None


class InterventionComparison(SchemaModel):
    types: list[TypeComparisonMetrics]


class InterventionAnalyticsDashboard(SchemaModel):
    summary: InterventionAnalytics
    leaderboard: list[InterventionLeaderboardEntry]
    learning_insights: LearnedEffectivenessResponse | None
    trends: list[InterventionTrendPoint]
    comparison: InterventionComparison | None = None
    overall_confidence: float = 1.0
    total_kb_entries: int = 0
