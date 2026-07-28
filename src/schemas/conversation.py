from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class ConversationRequest:
    user_id: str
    conversation_id: str
    session_id: str
    transcript: str
    language: Optional[str] = None
    language_confidence: Optional[float] = None
    modality: Literal["text", "voice"] = "text"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationResponse:
    answer: str
    language: str = "en"
    sources: list = field(default_factory=list)
    model_used: str = ""
    confidence: float = 0.0
    status: str = "approved"
    requires_teacher_review: bool = False
    session_id: str = ""
    metadata: dict = field(default_factory=dict)
