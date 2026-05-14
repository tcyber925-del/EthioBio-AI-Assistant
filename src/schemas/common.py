from pydantic import BaseModel, Field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class Message(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    user_id: UUID
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: str = "en"
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    model_used: str
    confidence: float
    sources: list[str] = []


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.1.0"
    ollama: bool = False
    database: bool = False
