from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TeacherMetric(BaseModel):
    teacher_id: UUID
    classroom_count: int
    avg_student_readiness: float
    intervention_rate: float
    active_plan_count: int


class SchoolProfile(BaseModel):
    school_id: UUID
    generated_at: datetime
    total_teachers: int
    total_classrooms: int
    total_students: int
    avg_health: float
    health_distribution: dict[str, int]
    teacher_metrics: list[TeacherMetric]
    at_risk_classrooms: list[dict]
