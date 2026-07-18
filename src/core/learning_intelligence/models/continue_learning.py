from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from src.core.learning_intelligence.recommendation.models.types import (
    LearningActionType,
)


class LearningCard(BaseModel):
    id: str
    title: str
    description: str
    action_type: LearningActionType
    priority_score: float = 0.0
    estimated_minutes: int = 0
    xp_reward: Optional[int] = None
    topic: Optional[str] = None
    exam_impact: Optional[str] = None
    metadata: dict = {}


class FeedSummary(BaseModel):
    estimated_minutes: int = 0
    xp_available: int = 0


class ContinueLearningFeed(BaseModel):
    user_id: UUID
    generated_at: datetime
    primary_action: Optional[LearningCard] = None
    sections: dict[str, list[LearningCard]] = {}
    summary: FeedSummary
