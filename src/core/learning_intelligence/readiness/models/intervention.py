from pydantic import BaseModel


class Intervention(BaseModel):
    topic: str
    priority: float  # 0.0-1.0
    action_type: str  # e.g. REVIEW_TOPIC, REVISE_MISCONCEPTION
    estimated_impact: float  # 0-100
    reason: str
