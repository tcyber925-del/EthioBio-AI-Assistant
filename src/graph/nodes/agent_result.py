"""Agent Result schema for Agentic RAG.

Standardized result type for all agents per PRD-001A.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Standardized result from agent execution.

    All agents return this type to ensure consistent communication.
    """

    success: bool
    message: str = ""
    state_updates: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, message: str = "", state_updates: dict | None = None) -> "AgentResult":
        """Create a successful result."""
        return cls(
            success=True,
            message=message,
            state_updates=state_updates or {},
        )

    @classmethod
    def fail(cls, message: str, errors: list[str] | None = None) -> "AgentResult":
        """Create a failed result."""
        return cls(
            success=False,
            message=message,
            errors=errors or [message],
        )

    @classmethod
    def partial(
        cls, message: str, state_updates: dict | None = None, errors: list[str] | None = None
    ) -> "AgentResult":
        """Create a partial success result."""
        return cls(
            success=True,
            message=message,
            state_updates=state_updates or {},
            errors=errors or [],
            metadata={"partial": True},
        )
