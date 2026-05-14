from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class TutorRequest(BaseModel):
    user_id: UUID
    question: str
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: str = "en"
    use_rag: bool = True


class TutorResponse(BaseModel):
    answer: str
    language: str
    sources: list[str] = []
    model_used: str
    confidence: float
