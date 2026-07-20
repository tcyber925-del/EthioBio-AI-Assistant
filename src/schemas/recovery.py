from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class MisconceptionInfo(SchemaModel):
    pattern_type: str
    description: str
    frequency: int


class WeakTopicDetail(SchemaModel):
    topic: str
    unit: str = ""
    grade_level: int = 0
    average_score: float
    attempt_count: int = 0
    severity: str
    confidence: float = 0.0
    misconceptions: list[MisconceptionInfo] = []
    last_assessed_at: Optional[datetime] = None


class WeakTopicsResponse(SchemaModel):
    user_id: UUID
    weak_topics: list[WeakTopicDetail] = []
    total_weak_topics: int = 0


class RecoveryTaskResponse(SchemaModel):
    id: UUID
    plan_id: UUID
    title: str
    task_type: str
    description: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    xp_awarded: int = 0
    created_at: datetime


class RecoveryPlanResponse(SchemaModel):
    id: UUID
    user_id: UUID
    topic: str
    total_tasks: int
    completed_tasks: int
    status: str
    progress_pct: float = 0.0
    tasks: list[RecoveryTaskResponse] = []
    created_at: datetime
    updated_at: datetime


class RecoveryTaskCreate(SchemaModel):
    title: str
    task_type: str = "practice"
    description: Optional[str] = None


class CreateRecoveryPlanRequest(SchemaModel):
    user_id: UUID
    topic: str
    tasks: list[RecoveryTaskCreate]


class CompleteTaskResponse(SchemaModel):
    task_id: UUID
    plan_id: UUID
    xp_awarded: int = 0
    milestone_bonus: int = 0
    total_xp: int = 0
    level_up: bool = False
    new_level: int = 0
    plan_completed: bool = False
    progress_pct: float


class GeneratedTaskInfo(SchemaModel):
    id: UUID
    title: str
    task_type: str
    description: Optional[str] = None


class GeneratedPlanInfo(SchemaModel):
    id: UUID
    user_id: UUID
    topic: str
    total_tasks: int
    status: str
    weak_topics_addressed: int
    tasks: list[GeneratedTaskInfo]
    created_at: Optional[str] = None


class GenerateRecoveryPlanResponse(SchemaModel):
    plan: Optional[GeneratedPlanInfo] = None
    error: Optional[str] = None


class GenerateRecoveryPlanRequest(SchemaModel):
    topic_filter: Optional[str] = None
    stream: bool = False


class RecommendationInfo(SchemaModel):
    type: str
    message: str
    priority: str = "medium"


class MasteryHistoryPoint(SchemaModel):
    average_score: float
    attempt_count: int
    severity: str
    confidence: float
    source: str
    recorded_at: datetime


class MasteryHistoryResponse(SchemaModel):
    user_id: UUID
    topic: str
    history: list[MasteryHistoryPoint] = []


class SpacedRepetitionItem(SchemaModel):
    id: UUID
    topic: str
    unit: str = ""
    grade_level: int = 0
    mastery_score: float
    interval_days: int
    ease_factor: float
    next_review_at: datetime
    last_reviewed_at: Optional[datetime] = None
    review_count: int = 0
    is_due: bool = False
    days_overdue: int = 0


class SpacedRepetitionScheduleResponse(SchemaModel):
    user_id: UUID
    total_items: int
    items: list[SpacedRepetitionItem] = []


class DueReviewsResponse(SchemaModel):
    user_id: UUID
    total_due: int
    items: list[SpacedRepetitionItem] = []


class SpacedRepetitionGenerateResponse(SchemaModel):
    user_id: UUID
    total_generated: int
    items: list[dict]


class SpacedRepetitionReviewRequest(SchemaModel):
    user_id: UUID
    topic: str
    new_score: float


class SpacedRepetitionReviewResponse(SchemaModel):
    topic: str
    interval_days: int
    ease_factor: float
    next_review_at: datetime
    review_count: int


class RecoveryNotificationResponse(SchemaModel):
    id: UUID
    topic: str
    event_type: str
    message: str
    improvement_pct: Optional[float] = None
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    is_read: bool = False
    created_at: datetime


class RecoveryNotificationListResponse(SchemaModel):
    user_id: UUID
    notifications: list[RecoveryNotificationResponse] = []
    total_unread: int = 0
    total: int = 0


class RecoveryDashboardResponse(SchemaModel):
    user_id: UUID
    weak_topics: list[WeakTopicDetail] = []
    total_weak_topics: int = 0
    active_plans: list[RecoveryPlanResponse] = []
    total_active_plans: int = 0
    recommendations: list[RecommendationInfo] = []
    due_reviews: list[SpacedRepetitionItem] = []
    total_due_reviews: int = 0
    unread_notifications: int = 0
    notifications: list[RecoveryNotificationResponse] = []
