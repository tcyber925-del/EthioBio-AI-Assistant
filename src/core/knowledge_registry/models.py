from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from src.core.retrieval.models import TextMatch


class LifecycleState(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PUBLISHED = "published"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    FAILED = "failed"


class KnowledgeObject(BaseModel):
    id: str
    workspace_id: str
    collection_id: str | None
    owner_id: str
    title: str
    content_type: str
    content_hash: str | None
    lifecycle_state: LifecycleState
    enrichment_status: str
    version: int
    metadata: dict
    created_at: datetime
    updated_at: datetime


class NewKnowledgeObject(BaseModel):
    workspace_id: str
    collection_id: str | None = None
    owner_id: str
    title: str
    content_type: str
    content_hash: str | None = None
    metadata: dict = {}


class KnowledgeFilter(BaseModel):
    workspace_id: str | None = None
    collection_id: str | None = None
    lifecycle_states: list[LifecycleState] | None = None
    enrichment_status: str | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


class LifecycleTransition(BaseModel):
    to_state: LifecycleState
    reason: str | None = None


class KnowledgeObjectVersion(BaseModel):
    id: str
    ko_id: str
    version: int
    snapshot: dict
    created_at: datetime


class SearchResult(BaseModel):
    ko_id: str
    title: str
    content_type: str
    score: float
    matches: list["TextMatch"]
