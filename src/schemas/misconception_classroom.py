from uuid import UUID

from src.schemas.base import SchemaModel


class ClassroomMisconceptionTopic(SchemaModel):
    topic: str
    affected_students: int
    total_students: int
    impact_percentage: float
    avg_severity_rank: float
    severity_distribution: dict[str, int]
    top_pattern: str = ""
    top_pattern_frequency: int = 0


class ClassroomMisconceptionHeatmap(SchemaModel):
    classroom_id: UUID
    total_students: int
    students_with_misconceptions: int
    total_unresolved_patterns: int
    by_topic: list[ClassroomMisconceptionTopic]
    improvement_trend: str
    generated_at: str
