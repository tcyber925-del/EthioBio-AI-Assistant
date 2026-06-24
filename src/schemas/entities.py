"""Unified entity models for Wave 0 Foundation Stabilization.

These are canonical API representations that map across DB models.
Not ORM models — they define the public contract for entity data.
"""

import enum
from datetime import datetime
from uuid import UUID

from src.schemas.base import SchemaModel


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"
    parent = "parent"


class StudentEntity(SchemaModel):
    id: UUID
    email: str | None = None
    grade_level: int | None = None
    language_preference: str = "en"
    school: str | None = None
    region: str | None = None
    weak_areas: list[str] = []
    created_at: datetime | None = None


class TeacherEntity(SchemaModel):
    id: UUID
    email: str | None = None
    classrooms: list[UUID] = []
    created_at: datetime | None = None


class ClassroomEntity(SchemaModel):
    id: UUID
    name: str
    grade_level: int
    teacher_id: UUID
    school_id: UUID | None = None
    student_ids: list[UUID] = []
    created_at: datetime | None = None


class AssessmentEntity(SchemaModel):
    id: UUID
    title: str
    grade_level: int
    topic: str
    question_count: int
    status: str = "draft"
    created_at: datetime | None = None


class InterventionEntity(SchemaModel):
    id: UUID
    student_id: UUID | None = None
    classroom_id: UUID | None = None
    intervention_type: str
    topic: str | None = None
    status: str = "planned"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    effectiveness_score: float | None = None


class LessonEntity(SchemaModel):
    id: UUID
    teacher_id: UUID | None = None
    grade_level: int
    topic: str
    objective: str
    status: str = "draft"
    created_at: datetime | None = None
