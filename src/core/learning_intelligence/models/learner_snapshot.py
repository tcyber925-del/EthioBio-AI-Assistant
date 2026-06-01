from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel


class MisconceptionSummary(BaseModel):
    topic: str
    pattern_type: str
    frequency: int


class RecoverySummary(BaseModel):
    topic: str
    progress_pct: float
    completed_tasks: int
    total_tasks: int
    status: str


class ReviewSummary(BaseModel):
    topic: str
    next_review_at: datetime
    days_overdue: int


class EducationalMemorySummary(BaseModel):
    understanding_level: str | None = None
    confidence: float | None = None
    active_learning_goals: list[str] = []
    recent_topics: list[str] = []


class GamificationSummary(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    total_xp: int = 0
    level: int = 1
    recent_activity_score: float = 0.0


class LearnerSnapshot(BaseModel):
    user_id: UUID
    generated_at: datetime

    mastery_by_topic: dict = {}
    ability_by_topic: dict = {}
    weak_topics: list[str] = []
    strong_topics: list[str] = []

    misconceptions: list[MisconceptionSummary] = []

    active_recovery_plans: list[RecoverySummary] = []

    due_reviews: list[ReviewSummary] = []

    educational_memory: EducationalMemorySummary = EducationalMemorySummary()

    gamification: GamificationSummary = GamificationSummary()

    learning_goals: list[str] = []

    degraded: bool = False
    degraded_sources: list[str] = []

    def model_post_init(self, _context):
        object.__setattr__(self, "generated_at", datetime.now(timezone.utc))
