from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class Message(SchemaModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(SchemaModel):
    messages: list[Message]
    user_id: UUID
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: str = "en"
    stream: bool = False


class ChatResponse(SchemaModel):
    reply: str
    model_used: str
    confidence: float
    sources: list[str] = []


class ErrorResponse(SchemaModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(SchemaModel):
    status: str
    version: str = "1.1.0"
    ollama: bool = False
    database: bool = False
