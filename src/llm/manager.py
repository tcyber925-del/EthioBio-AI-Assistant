import time
from collections.abc import AsyncGenerator

import structlog

from src.config import settings
from src.llm.circuit_breaker import CircuitBreaker
from src.llm.providers.anthropic_provider import AnthropicProvider
from src.llm.providers.base import LLMProvider
from src.llm.providers.ollama import OllamaProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.providers.openrouter import OpenRouterProvider
from src.llm.registry import ModelRegistry

logger = structlog.get_logger()


class ProviderManager:
    """Centralized manager for multi-provider LLM routing with fallback chain."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_chain: list[str] = []
        self._active_model: str = settings.ollama_chat_model
        self._registry = ModelRegistry()
        self.breakers: dict[str, CircuitBreaker] = {}
        self._init_providers()

    def _get_breaker(self, name: str) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name)
        return self.breakers[name]

    def _init_providers(self):
        """Initialize all configured providers."""
        ollama = OllamaProvider()
        self._providers["ollama"] = ollama

        self._providers["openrouter"] = OpenRouterProvider()
        if settings.openrouter_api_key:
            self._fallback_chain.append("openrouter")

        if settings.fallback_provider and settings.fallback_provider.lower() == "openai":
            self._providers["openai"] = OpenAIProvider()
            self._fallback_chain.append("openai")

        if settings.fallback_provider and settings.fallback_provider.lower() == "anthropic":
            self._providers["anthropic"] = AnthropicProvider()
            self._fallback_chain.append("anthropic")

        compat_url = getattr(settings, "provider_openai_compatible_url", None)
        compat_key = getattr(settings, "provider_openai_compatible_api_key", None)
        compat_model = getattr(settings, "provider_openai_compatible_model", None)
        if compat_url and compat_key:
            name = getattr(settings, "provider_openai_compatible_name", "lm-studio")
            self._providers[name] = OpenAIProvider(
                api_key=compat_key, model=compat_model, base_url=compat_url, name=name
            )
            self._fallback_chain.append(name)

        self._fallback_chain = ["ollama"] + self._fallback_chain

    @property
    def active_model(self) -> str:
        return self._active_model

    def set_active_model(self, model: str):
        """Set the preferred model for subsequent requests."""
        self._active_model = model
        logger.info("provider_manager_model_changed", model=model)

    async def list_available_models(self) -> list[dict]:
        """List models across all providers, grouped by provider.
        Each entry includes an `available` flag for the UI to indicate
        whether the provider is configured and ready to use."""
        models = []
        for name, provider in self._providers.items():
            available = await provider.is_available()
            provider_models = await provider.get_available_models()
            for m in provider_models:
                models.append(
                    {
                        "id": f"{name}/{m}",
                        "name": m,
                        "provider": name,
                        "available": available,
                        "is_default": m == settings.ollama_chat_model,
                    }
                )
        return models

    async def get_provider_info(self) -> list[dict]:
        """Get health and info for all providers."""
        infos = []
        for name, provider in self._providers.items():
            info = provider.get_info()
            if name == "ollama":
                info.available_models = await provider.get_available_models()
                info.is_healthy = await provider.check_health()
            infos.append(
                {
                    "name": info.name,
                    "provider_type": info.provider_type,
                    "base_url": info.base_url,
                    "available_models": info.available_models,
                    "is_healthy": info.is_healthy,
                    "is_default": info.is_default,
                }
            )
        return infos

    async def route(
        self,
        messages: list[dict],
        request_type: str = "chat",
        session=None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        preferred_model: str | None = None,
    ) -> dict:
        """Route a request through the provider chain with fallback."""
        start_time = time.monotonic()
        model_to_use = preferred_model or self._active_model
        last_error = None
        skipped: list[str] = []

        if "/" not in model_to_use:
            candidate = f"ollama/{model_to_use}"
        else:
            candidate = model_to_use

        preferred_provider = candidate.split("/")[0] if "/" in candidate else "ollama"
        ordered_providers = [preferred_provider] + [
            p for p in self._fallback_chain if p != preferred_provider
        ]

        for provider_name in ordered_providers:
            provider = self._providers.get(provider_name)
            if not provider:
                skipped.append(f"{provider_name}: not_configured")
                continue
            breaker = self._get_breaker(provider_name)
            if not breaker.is_available:
                skipped.append(f"{provider_name}: circuit_open")
                continue
            if not await provider.is_available():
                skipped.append(f"{provider_name}: unavailable")
                continue

            try:
                chat_messages = list(messages)
                if provider_name == "ollama" and "/" in candidate:
                    model_name = candidate.split("/", 1)[1]
                    chat_messages = [
                        {"role": "system", "content": f"__model__:{model_name}"},
                    ] + chat_messages

                response = await provider.chat(
                    messages=chat_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                breaker.record_success()
                latency = int((time.monotonic() - start_time) * 1000)

                logger.info(
                    "provider_manager_success",
                    model=response.model,
                    provider=provider_name,
                    latency_ms=latency,
                    request_type=request_type,
                )

                return {
                    "content": response.content,
                    "model": response.model,
                    "confidence": 0.85,
                    "usage": response.usage,
                }
            except Exception as e:
                last_error = str(e)
                breaker.record_failure()
                logger.warning(
                    "provider_manager_provider_failed",
                    provider=provider_name,
                    error=last_error,
                )
                continue

        latency = int((time.monotonic() - start_time) * 1000)
        logger.error(
            "provider_manager_all_failed",
            error=last_error,
            latency_ms=latency,
        )
        if last_error is None:
            raise ConnectionError(
                f"All LLM providers failed (none was attempted; skipped: {skipped})"
            )
        raise ConnectionError(f"All LLM providers failed. Last error: {last_error}")

    async def route_stream(
        self,
        messages: list[dict],
        request_type: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        preferred_model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response through the provider chain with fallback."""
        model_to_use = preferred_model or self._active_model
        last_error = None
        skipped: list[str] = []

        if "/" not in model_to_use:
            candidate = f"ollama/{model_to_use}"
        else:
            candidate = model_to_use

        preferred_provider = candidate.split("/")[0] if "/" in candidate else "ollama"
        ordered_providers = [preferred_provider] + [
            p for p in self._fallback_chain if p != preferred_provider
        ]

        for provider_name in ordered_providers:
            provider = self._providers.get(provider_name)
            if not provider:
                skipped.append(f"{provider_name}: not_configured")
                continue
            breaker = self._get_breaker(provider_name)
            if not breaker.is_available:
                skipped.append(f"{provider_name}: circuit_open")
                continue
            if not await provider.is_available():
                skipped.append(f"{provider_name}: unavailable")
                continue

            try:
                chat_messages = list(messages)
                if provider_name == "ollama" and "/" in candidate:
                    model_name = candidate.split("/", 1)[1]
                    chat_messages = [
                        {"role": "system", "content": f"__model__:{model_name}"},
                    ] + chat_messages

                async for token in provider.chat_stream(
                    messages=chat_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield token
                breaker.record_success()
                return  # success
            except Exception as e:
                last_error = str(e)
                breaker.record_failure()
                logger.warning(
                    "provider_manager_stream_failed",
                    provider=provider_name,
                    error=last_error,
                )
                continue

        if last_error is None:
            raise ConnectionError(
                f"All LLM providers failed for streaming (none was attempted; skipped: {skipped})"
            )
        raise ConnectionError(f"All LLM providers failed for streaming. Last error: {last_error}")

    async def check_health(self) -> dict:
        """Check health of all providers."""
        health = {}
        for name, provider in self._providers.items():
            health[name] = {
                "healthy": await provider.check_health(),
                "models": await provider.get_available_models(),
            }
        return health

    async def refresh_models(self):
        """Refresh Ollama model cache across all providers."""
        await self._registry.refresh()
        for provider in self._providers.values():
            if hasattr(provider, "_available_models"):
                provider._available_models = None

    async def close(self):
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()
        await self._registry.close()
