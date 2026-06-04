from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel
from src.schemas.common import LanguageEnum


class LessonPlanRequest(SchemaModel):
    grade_level: int = Field(..., ge=7, le=12)
    topic: str
    duration_minutes: int = Field(40, ge=20, le=120)
    language: LanguageEnum = LanguageEnum.EN
    teacher_id: Optional[UUID] = None
    model: Optional[str] = None


class LessonPlanResponse(SchemaModel):
    objective: str
    prior_knowledge: Optional[str]
    explanation: str
    activities: list[dict]
    assessment: str
    homework: Optional[str]
    teacher_notes: Optional[str]
    model_used: str
