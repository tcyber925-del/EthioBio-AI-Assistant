"""Event schema foundation for Wave 0.

Standard EducationalEvent interface that all platform events conform to.
Not the full Event Bus (deferred to Wave 8) — just the schema contract.
"""

import enum
from datetime import datetime
from uuid import UUID

from src.schemas.base import SchemaModel


class EventCategory(str, enum.Enum):
    assessment = "assessment"
    learning = "learning"
    mastery = "mastery"
    readiness = "readiness"
    intervention = "intervention"
    prediction = "prediction"
    classroom = "classroom"
    teacher = "teacher"
    agent = "agent"
    system = "system"


class EducationalEvent(SchemaModel):
    event_id: UUID
    event_type: str
    category: EventCategory
    timestamp: datetime
    actor_type: str
    actor_id: UUID
    entity_type: str
    entity_id: UUID
    source_service: str
    metadata: dict = {}
    version: int = 1


class EventEnvelope(SchemaModel):
    event: EducationalEvent
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    published_at: datetime | None = None
