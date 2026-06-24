from typing import Optional

from src.schemas.base import SchemaModel


class PrerequisiteGap(SchemaModel):
    topic: str
    unit: Optional[str] = None
    depth: int
    mastery_score: Optional[float] = None
    misconception_count: int = 0
    misconceptions: list[dict] = []


class MisconceptionCascadeNode(SchemaModel):
    topic: str
    frequency: int
    severity: str
    prerequisite_gaps: list[PrerequisiteGap] = []


class TopicMisconceptionWeight(SchemaModel):
    topic: str
    unit: Optional[str] = None
    grade_level: int
    active_misconception_count: int
