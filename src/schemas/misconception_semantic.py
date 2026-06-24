from typing import Optional

from src.schemas.base import SchemaModel


class SemanticAnalysisRequest(SchemaModel):
    topic: str
    wrong_answer: str
    correct_answer: str
    question_text: str = ""


class SemanticAnalysisResult(SchemaModel):
    has_misconception: bool = False
    misconception: Optional[str] = None
    misconception_type: Optional[str] = None
    explanation: str = ""
    confidence: float = 0.0
    related_patterns: list[str] = []
