from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class SessionStartRequest(SchemaModel):
    user_id: UUID
    topic: Optional[str] = None
    tutoring_mode: str = "direct"


class SessionStartResponse(SchemaModel):
    session_id: UUID
    user_id: UUID
    active_topic: Optional[str] = None
    tutoring_mode: str
    started_at: datetime
    last_active_at: datetime


class SessionHeartbeatResponse(SchemaModel):
    session_id: UUID
    last_active_at: datetime


class SummarizeRequest(SchemaModel):
    conversation_context: Optional[str] = None


class SummarizeResponse(SchemaModel):
    summary_id: UUID
    topic: str
    understanding_level: Optional[str] = None
    key_misconceptions: list = []
    confidence: float = 0.0
    next_learning_goal: Optional[str] = None
    created_at: datetime


class SessionCloseResponse(SchemaModel):
    session_id: UUID
    summary: Optional[str] = None
    summary_detail: Optional[SummarizeResponse] = None
    closed: bool


class SessionResponse(SchemaModel):
    session_id: UUID
    user_id: UUID
    active_topic: Optional[str] = None
    tutoring_mode: str
    educational_context: Optional[str] = None
    unresolved_questions: list = []
    started_at: datetime
    last_active_at: datetime
    summary: Optional[str] = None


class SocraticStateResponse(SchemaModel):
    user_id: UUID
    topic: str
    socratic_stage: str
    current_focus: Optional[str] = None
    student_understanding: str
    next_question: Optional[str] = None
    conceptual_gaps: list = []
    updated_at: datetime


class SocraticStateUpdateRequest(SchemaModel):
    user_id: UUID
    topic: str
    socratic_stage: Optional[str] = None
    current_focus: Optional[str] = None
    student_understanding: Optional[str] = None
    next_question: Optional[str] = None
    conceptual_gaps: Optional[list] = None


class MemoryEventRequest(SchemaModel):
    user_id: UUID
    event_type: str
    topic: Optional[str] = None
    event_metadata: dict = {}


class MemoryEventResponse(SchemaModel):
    id: UUID
    user_id: UUID
    event_type: str
    topic: Optional[str] = None
    event_metadata: dict = {}
    created_at: datetime


class MemoryEventListResponse(SchemaModel):
    events: list[MemoryEventResponse] = []
    total: int = 0


class SummaryResponse(SchemaModel):
    id: UUID
    user_id: UUID
    topic: str
    understanding_level: Optional[str] = None
    key_misconceptions: list = []
    confidence: float = 0.0
    next_learning_goal: Optional[str] = None
    created_at: datetime


class SummaryListResponse(SchemaModel):
    summaries: list[SummaryResponse] = []
    total: int = 0


class MemorySearchRequest(SchemaModel):
    query: str
    topic: Optional[str] = None
    user_id: Optional[str] = None
    n_results: int = 5


class MemorySearchResult(SchemaModel):
    memory_id: str
    content: str
    metadata: dict = {}
    score: float = 0.0
    similarity: float = 0.0


class MemorySearchResponse(SchemaModel):
    results: list[MemorySearchResult] = []
    total: int = 0
