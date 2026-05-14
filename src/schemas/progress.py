from pydantic import BaseModel, Field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class ProgressRequest(BaseModel):
    student_id: UUID
    days: int = Field(30, ge=1, le=365)


class ProgressResponse(BaseModel):
    student_id: UUID
    topics: dict[str, Any]
    weak_areas: list[str]
    overall_score: float
    trend: str


class ParentSummaryRequest(BaseModel):
    parent_id: UUID
    student_id: UUID
    language: str = "en"


class ParentSummaryResponse(BaseModel):
    summary_text: str
    summary_amharic: Optional[str]
    week_start: datetime
    week_end: datetime
    is_low_performance_warning: bool
