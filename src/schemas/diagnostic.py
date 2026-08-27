from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel
from src.schemas.common import LanguageEnum, SubjectEnum
from src.schemas.quiz import QuestionSchema


class DiagnosticRequest(SchemaModel):
    user_id: UUID
    grade_level: int = Field(..., ge=7, le=12)
    subject: Optional[SubjectEnum] = None
    topics: list[str] = Field(..., min_length=1, max_length=10)
    questions_per_topic: int = Field(3, ge=1, le=10)
    language: LanguageEnum = LanguageEnum.EN
    model: Optional[str] = None
    stream: bool = False


class TopicBaseline(SchemaModel):
    topic: str
    score: float
    total: int
    correct: int
    severity: str
    questions: list[QuestionSchema]


class DiagnosticResponse(SchemaModel):
    diagnostic_id: UUID
    user_id: UUID
    grade_level: int
    overall_score: float
    overall_severity: str
    topic_baselines: list[TopicBaseline]
    weakest_topics: list[str]
    strongest_topics: list[str]
    generated_at: datetime
    model_used: str
