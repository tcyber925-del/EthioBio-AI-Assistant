from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict


class UsageInfo(TypedDict, total=False):
    """Token usage information from a chat response."""

    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


@dataclass
class ProviderInfo:
    """Metadata about a provider and its available models."""

    name: str
    provider_type: str  # "ollama", "openai", "anthropic", "openai-compatible"
    base_url: str
    available_models: list[str] = field(default_factory=list)
    is_healthy: bool = False
    is_default: bool = False


@dataclass
class ChatResponse:
    """Unified response from any provider."""

    content: str
    model: str
    usage: UsageInfo
    provider: str


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this provider is configured (credentials/URL set) and reachable."""
        ...

    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """List models available through this provider. May trigger a network call."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Perform a live health check against the provider's API endpoint."""
        ...

    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Return provider metadata."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'ollama', 'openai')."""
        ...
