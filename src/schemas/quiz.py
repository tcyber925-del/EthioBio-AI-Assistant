from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class QuestionSchema(BaseModel):
    question_type: str = Field(..., pattern="^(multiple_choice|true_false|short_answer|matching|diagram_label)$")
    question_text: str
    options: Optional[list[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")


class QuizGenerateRequest(BaseModel):
    grade_level: int = Field(..., ge=7, le=12)
    topic: str
    question_count: int = Field(5, ge=1, le=30)
    types: list[str] = Field(default_factory=lambda: ["multiple_choice", "true_false"])
    language: str = "en"
    teacher_id: Optional[UUID] = None


class QuizGenerateResponse(BaseModel):
    title: str
    grade_level: int
    topic: str
    questions: list[QuestionSchema]
    answer_key: str
    model_used: str


class QuizSubmitRequest(BaseModel):
    quiz_id: UUID
    user_id: UUID
    answers: list[dict]


class QuizSubmitResponse(BaseModel):
    score: float
    total: int
    correct: int
    feedback: list[dict]
