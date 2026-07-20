from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel
from src.schemas.common import LanguageEnum


class TutorRequest(SchemaModel):
    user_id: Optional[UUID] = None
    question: str
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: LanguageEnum = LanguageEnum.EN
    use_rag: bool = True
    model: Optional[str] = None
    socratic_mode: bool = False
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
    session_id: Optional[str] = None
    generate_diagram: bool = True
    stream: bool = False


class TutorResponse(SchemaModel):
    answer: str
    language: str
    sources: list[str] = []
    model_used: str
    confidence: float
    status: str = "approved"
    requires_teacher_review: bool = False
    session_id: str = ""
    socratic_mode: bool = False
    socratic_stage: str = ""
    socratic_focus: str = ""
    socratic_understanding: str = ""
    socratic_next_question: str = ""
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
    xp_awarded: int = 0
    level_up: bool = False
    new_level: int = 0
    diagram_svg: str = ""
    diagram_labels: list[dict] = Field(default_factory=list)
    diagram_title: str = ""
    diagram_textbook_ref: str = ""
