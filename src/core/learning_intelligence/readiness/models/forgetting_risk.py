from pydantic import BaseModel


class ForgettingRisk(BaseModel):
    topic: str
    forgetting_risk: float
    days_overdue: int = 0
    ease_factor: float = 2.5
    review_count: int = 0
    contributing_factors: list[str] = []
