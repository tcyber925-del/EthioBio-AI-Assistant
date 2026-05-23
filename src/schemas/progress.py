from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class ProgressRequest(SchemaModel):
    student_id: UUID
    days: int = Field(30, ge=1, le=365)


class ProgressResponse(SchemaModel):
    student_id: UUID
    topics: dict[str, Any]
    weak_areas: list[str]
    overall_score: float
    trend: str


class ParentSummaryRequest(SchemaModel):
    parent_id: UUID
    student_id: UUID
    language: str = "en"


class ParentSummaryResponse(SchemaModel):
    summary_text: str
    summary_amharic: Optional[str]
    week_start: datetime
    week_end: datetime
    is_low_performance_warning: bool
