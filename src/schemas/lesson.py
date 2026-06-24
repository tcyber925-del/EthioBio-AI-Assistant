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
    classroom_id: Optional[UUID] = None
    model: Optional[str] = None
    generate_exit_ticket: bool = False
    generate_differentiation: bool = False
    generate_diagram_suggestions: bool = False
    generate_misconception_activities: bool = False


class ExitTicketQuestion(SchemaModel):
    question_type: str = Field(
        ...,
        pattern="^(multiple_choice|true_false|short_answer)$",
    )
    question_text: str
    options: Optional[list[str]] = None
    correct_answer: str
    explanation: Optional[str] = None


class DifferentiationActivity(SchemaModel):
    group: str = Field(..., pattern="^(support|standard|advanced)$")
    description: str
    duration_minutes: int = 10


class DiagramSuggestion(SchemaModel):
    title: str
    description: str
    diagram_type: str = Field(
        ...,
        pattern="^(flowchart|labeling|concept_map|comparison|process|anatomy)$",
    )


class LessonPlanRatingRequest(SchemaModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
    used_in_class: bool = False


class MisconceptionActivity(SchemaModel):
    misconception: str
    activity_name: str
    description: str
    duration_minutes: int = 10
    activity_type: str = Field(
        ...,
        pattern="^(concept_conflict|diagnostic_question|evidence_challenge|reconstruction)$",
    )


class LessonPlanResponse(SchemaModel):
    id: Optional[UUID] = None
    objective: str
    prior_knowledge: Optional[str]
    explanation: str
    activities: list[dict]
    assessment: str
    homework: Optional[str]
    teacher_notes: Optional[str]
    model_used: str
    classroom_id: Optional[UUID] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    used_in_class: bool = False
    created_at: Optional[str] = None
    exit_ticket: Optional[list[ExitTicketQuestion]] = None
    differentiation: Optional[list[DifferentiationActivity]] = None
    diagram_suggestions: Optional[list[DiagramSuggestion]] = None
    misconception_activities: Optional[list[MisconceptionActivity]] = None
    classroom_context: Optional[dict] = None
