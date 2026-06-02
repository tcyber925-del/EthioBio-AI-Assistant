from pydantic import BaseModel


class StabilityScore(BaseModel):
    topic: str
    stability_score: float
    stability_band: str  # Stable / Moderate / Volatile
