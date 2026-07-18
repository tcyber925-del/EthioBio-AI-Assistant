from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.core.learning_intelligence.recommendation.models.types import (
    LearningActionType,
)


class LearningRecommendation(BaseModel):
    id: str
    action_type: LearningActionType
    topic: Optional[str] = None
    priority_score: float = 0.0
    reason: str = ""
    explanation: str = ""
    generated_at: datetime
    metadata: dict = {}
