from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TutorRequest(BaseModel):
    user_id: UUID
    question: str
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: str = "en"
    use_rag: bool = True
    model: Optional[str] = None
    socratic_mode: bool = False


class TutorResponse(BaseModel):
    answer: str
    language: str
    sources: list[str] = []
    model_used: str
    confidence: float
    socratic_mode: bool = False
