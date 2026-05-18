from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class LessonPlanRequest(BaseModel):
    grade_level: int = Field(..., ge=7, le=12)
    topic: str
    duration_minutes: int = Field(40, ge=20, le=120)
    language: str = "en"
    teacher_id: Optional[UUID] = None
    model: Optional[str] = None


class LessonPlanResponse(BaseModel):
    objective: str
    prior_knowledge: Optional[str]
    explanation: str
    activities: list[dict]
    assessment: str
    homework: Optional[str]
    teacher_notes: Optional[str]
    model_used: str
