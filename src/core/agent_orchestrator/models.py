from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class AgentStatus(str, Enum):
    idle = "idle"
    busy = "busy"
    error = "error"


@dataclass
class AgentCapability:
    name: str
    description: str
    input_schema: dict | None = None
    output_schema: dict | None = None
    requires_llm: bool = True
    requires_retrieval: bool = False
    requires_user_id: bool = False


@dataclass
class AgentRegistration:
    agent: Any
    name: str
    description: str
    capabilities: list[AgentCapability]
    status: AgentStatus = AgentStatus.idle
    version: str = "1.0.0"


@dataclass
class AgentMessage:
    message_id: UUID = field(default_factory=uuid4)
    task_id: str = ""
    sender: str = ""
    receiver: str = ""
    objective: str = ""
    context: dict | None = None
    findings: dict | None = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict | None = None


@dataclass
class TaskAssignment:
    task_id: str
    agent_name: str
    objective: str
    context: dict
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReflectionVerdict(str, Enum):
    success = "success"
    partial = "partial"
    failure = "failure"


@dataclass
class AgentReflection:
    reflection_id: UUID = field(default_factory=uuid4)
    agent_name: str = ""
    task_id: str = ""
    objective: str = ""
    verdict: ReflectionVerdict = ReflectionVerdict.success
    confidence: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None
    improvement_suggestion: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
