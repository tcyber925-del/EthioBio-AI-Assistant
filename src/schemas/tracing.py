from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class TraceResponse(SchemaModel):
    trace_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str
    error: Optional[str] = None
    user_message: str = ""
    response: Optional[str] = None
    user_id: Optional[str] = None
    grade_level: Optional[int] = None
    language: Optional[str] = None
    intent: Optional[str] = None
    nodes_visited: list = []
    node_timings: dict = {}
    metadata: dict = {}
    duration_ms: float = 0.0


class TraceListResponse(SchemaModel):
    traces: list[TraceResponse]
    total: int
    limit: int
    offset: int


class TraceDeleteResponse(SchemaModel):
    deleted: bool
    trace_id: str
