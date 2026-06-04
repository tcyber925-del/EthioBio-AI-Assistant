from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel
from src.schemas.common import LanguageEnum


class TutorRequest(SchemaModel):
    user_id: UUID
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


class TutorResponse(SchemaModel):
    answer: str
    language: str
    sources: list[str] = []
    model_used: str
    confidence: float
    socratic_mode: bool = False
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
    xp_awarded: int = 0
    level_up: bool = False
    new_level: int = 0
