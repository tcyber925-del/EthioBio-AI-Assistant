from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KnowledgeEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    ko_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str


class KnowledgeObjectRegistered(KnowledgeEvent):
    event_type: str = "knowledge_object_registered"
    workspace_id: str
    title: str
    content_type: str
    actor_id: str


class LifecycleChanged(KnowledgeEvent):
    event_type: str = "lifecycle_changed"
    from_state: str
    to_state: str
    reason: str | None = None


class MetadataUpdated(KnowledgeEvent):
    event_type: str = "metadata_updated"
    changes: dict


class KnowledgeObjectDeleted(KnowledgeEvent):
    event_type: str = "knowledge_object_deleted"
    reason: str | None = None


class VersionCreated(KnowledgeEvent):
    event_type: str = "version_created"
    version_number: int
