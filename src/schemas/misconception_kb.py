from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class MisconceptionKBEntry(SchemaModel):
    id: UUID
    topic: str
    misconception: str
    explanation: str
    severity: str
    related_objectives: list[str] = []
    recommended_strategies: list[str] = []
    detection_patterns: list[str] = []
    grade_level: int = 10
    created_at: datetime
    updated_at: datetime


class MisconceptionKBEntryCreate(SchemaModel):
    topic: str
    misconception: str
    explanation: str
    severity: str = "misconception"
    related_objectives: list[str] = []
    recommended_strategies: list[str] = []
    detection_patterns: list[str] = []
    grade_level: int = 10


class MisconceptionClassificationResult(SchemaModel):
    entry_id: Optional[str] = None
    misconception: Optional[str] = None
    explanation: Optional[str] = None
    severity: Optional[str] = None
    recommended_strategies: list[str] = []
    match_confidence: float = 0.0
    matched: bool = False


class ClassifyMisconceptionRequest(SchemaModel):
    topic: str
    wrong_answer: str


class SeverityDefinition(SchemaModel):
    key: str
    label: str
    rank: int
    description: str
