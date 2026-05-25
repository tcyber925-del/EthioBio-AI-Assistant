from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class QuestionSchema(SchemaModel):
    question_type: str = Field(
        ...,
        pattern="^(multiple_choice|true_false|short_answer|matching|diagram_label)$",
    )
    question_text: str
    options: Optional[list[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")


class QuizGenerateRequest(SchemaModel):
    grade_level: int = Field(..., ge=7, le=12)
    topic: str
    question_count: int = Field(5, ge=1, le=30)
    types: list[str] = Field(default_factory=lambda: ["multiple_choice", "true_false"])
    language: str = "en"
    teacher_id: Optional[UUID] = None
    model: Optional[str] = None


class QuizGenerateResponse(SchemaModel):
    title: str
    grade_level: int
    topic: str
    questions: list[QuestionSchema]
    answer_key: str
    model_used: str


class QuizSubmitRequest(SchemaModel):
    quiz_id: UUID
    user_id: UUID
    answers: list[dict]


class QuizSubmitResponse(SchemaModel):
    score: float
    total: int
    correct: int
    feedback: list[dict]
    xp_awarded: int = 0
