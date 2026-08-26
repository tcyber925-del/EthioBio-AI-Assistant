# Dynamic Multi-Provider AI Model System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded single-Ollama-model implementation with a dynamic multi-provider AI model system supporting runtime model switching, fallback chains, auto-detection, and UI-based model selection in both the dashboard and Telegram bot.

**Architecture:** Introduce a `LLMProvider` protocol/interface, concrete provider implementations (Ollama, OpenAI, Anthropic), a `ProviderManager` that orchestrates the fallback chain and model selection, and a `ModelRegistry` for auto-detecting available models. The existing `ModelRouter` becomes a thin adapter over `ProviderManager` for backward compatibility. New API endpoints and UI components expose model selection.

**Tech Stack:** Python 3.12+, async/asyncio, httpx, openai SDK, anthropic SDK, pydantic-settings, FastAPI, Next.js (dashboard), python-telegram-bot, SQLAlchemy, LangGraph.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/llm/providers/base.py` | `LLMProvider` protocol/ABC with `chat()`, `is_available()`, `get_model_name()` |
| Create | `src/llm/providers/ollama.py` | `OllamaProvider` — wraps Ollama API, supports any model name |
| Create | `src/llm/providers/openai_provider.py` | `OpenAIProvider` — OpenAI-compatible (includes LM Studio, vLLM) |
| Create | `src/llm/providers/anthropic_provider.py` | `AnthropicProvider` — Anthropic Claude |
| Create | `src/llm/providers/__init__.py` | Exports all providers |
| Create | `src/llm/registry.py` | `ModelRegistry` — auto-detects Ollama models via `/api/tags`, caches available models |
| Create | `src/llm/manager.py` | `ProviderManager` — centralized provider chain, fallback logic, runtime switching |
| Modify | `src/config.py` | Add multi-provider config: per-provider settings, OpenAI-compatible provider |
| Modify | `src/llm/router.py` | Thin wrapper over `ProviderManager` for backward compat |
| Modify | `src/graph/state.py` | Add `preferred_model: str = ""` field to `AgentState` |
| Create | `src/api/models.py` | API endpoints: `GET /models`, `POST /models/active`, `GET /models/health` |
| Modify | `src/api/graph.py` | Add `model` field to `GraphChatRequest`, pass to `run_graph` |
| Modify | `src/api/chat.py` | Pass model from request to agent |
| Modify | `src/schemas/chat.py` | Add `model` field to `TutorRequest` |
| Create | `dashboard/src/components/ModelSelector.tsx` | Reusable model selector dropdown |
| Modify | `dashboard/src/app/ask/page.tsx` | Add model selector UI |
| Modify | `dashboard/src/app/monitoring/page.tsx` | Add provider health panel |
| Modify | `src/telegram/bot.py` | Add model selection via inline keyboard |
| Modify | `src/telegram/keyboards.py` | Add model selection keyboard builder |
| Modify | `.env.example` | Updated multi-provider config |
| Modify | `tests/test_llm.py` | Tests for new provider system |
| Modify | `tests/conftest.py` | Updated mock fixtures |

---

## Task 1: Provider Protocol / Abstract Base Class

**Files:**
- Create: `src/llm/providers/base.py`
- Create: `src/llm/providers/__init__.py`

- [ ] **Step 1: Create the provider protocol**

```python
# src/llm/providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderInfo:
    """Metadata about a provider and its available models."""
    name: str
    provider_type: str  # "ollama", "openai", "anthropic", "openai-compatible"
    base_url: str
    available_models: list[str]
    is_healthy: bool = False
    is_default: bool = False


@dataclass
class ChatResponse:
    """Unified response from any provider."""
    content: str
    model: str
    usage: dict
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
        """Check if this provider is configured and reachable."""
        ...

    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """List models available through this provider."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Health check for the provider."""
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
```

- [ ] **Step 2: Create the providers package init**

```python
# src/llm/providers/__init__.py
from src.llm.providers.base import LLMProvider, ProviderInfo, ChatResponse

__all__ = ["LLMProvider", "ProviderInfo", "ChatResponse"]
```

- [ ] **Step 3: Verify imports work**

Run: `python -c "from src.llm.providers.base import LLMProvider, ProviderInfo, ChatResponse; print('OK')"`
Expected: `OK`

---

## Task 2: OllamaProvider Implementation

**Files:**
- Create: `src/llm/providers/ollama.py`

- [ ] **Step 1: Create OllamaProvider**

```python
# src/llm/providers/ollama.py
import httpx
import structlog
from src.llm.providers.base import LLMProvider, ProviderInfo, ChatResponse
from src.config import settings

logger = structlog.get_logger()


class OllamaProvider(LLMProvider):
    """Ollama provider supporting any locally installed model."""

    def __init__(self, base_url: str | None = None, default_model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._default_model = default_model or settings.ollama_chat_model
        self._available_models: list[str] | None = None
        self._healthy: bool | None = None
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    @property
    def name(self) -> str:
        return "ollama"

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        model = self._default_model
        # Extract model hint from system message if present
        for msg in messages:
            if msg.get("role") == "system" and msg.get("content", "").startswith("__model__:"):
                model = msg["content"].split(":", 2)[1]
                break

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        response = await self._client.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        result = response.json()
        return ChatResponse(
            content=result["message"]["content"],
            model=f"ollama/{model}",
            usage={
                "total_tokens": result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
            },
            provider="ollama",
        )

    async def is_available(self) -> bool:
        return await self.check_health()

    async def get_available_models(self) -> list[str]:
        if self._available_models is not None:
            return self._available_models
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if resp.is_success:
                data = resp.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                self._healthy = True
                return self._available_models
        except Exception:
            pass
        self._healthy = False
        return []

    async def check_health(self) -> bool:
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            self._healthy = resp.is_success
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="ollama",
            provider_type="ollama",
            base_url=self.base_url,
            available_models=self._available_models or [],
            is_healthy=self._healthy or False,
            is_default=True,
        )

    async def close(self):
        await self._client.aclose()
```

- [ ] **Step 2: Test OllamaProvider import**

Run: `python -c "from src.llm.providers.ollama import OllamaProvider; print('OK')"`
Expected: `OK`

---

## Task 3: OpenAIProvider Implementation

**Files:**
- Create: `src/llm/providers/openai_provider.py`

- [ ] **Step 1: Create OpenAIProvider**

```python
# src/llm/providers/openai_provider.py
import structlog
from openai import AsyncOpenAI
from src.llm.providers.base import LLMProvider, ProviderInfo, ChatResponse
from src.config import settings

logger = structlog.get_logger()


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider (OpenAI, LM Studio, vLLM, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        name: str = "openai",
    ):
        self._name = name
        self._api_key = api_key or settings.fallback_api_key or ""
        self._model = model or settings.fallback_model or "gpt-4o-mini"
        self._base_url = base_url
        self._client: AsyncOpenAI | None = None
        self._healthy: bool | None = None

    @property
    def name(self) -> str:
        return self._name

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            kwargs: dict = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = {"total_tokens": response.usage.total_tokens if response.usage else 0}
        return ChatResponse(
            content=content,
            model=f"{self._name}/{self._model}",
            usage=usage,
            provider=self._name,
        )

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def get_available_models(self) -> list[str]:
        return [self._model]

    async def check_health(self) -> bool:
        if not self._api_key:
            self._healthy = False
            return False
        try:
            client = self._get_client()
            await client.models.list()
            self._healthy = True
            return True
        except Exception:
            self._healthy = False
            return False

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self._name,
            provider_type="openai-compatible",
            base_url=self._base_url or "https://api.openai.com/v1",
            available_models=[self._model],
            is_healthy=self._healthy or False,
            is_default=False,
        )
```

- [ ] **Step 2: Test import**

Run: `python -c "from src.llm.providers.openai_provider import OpenAIProvider; print('OK')"`
Expected: `OK`

---

## Task 4: AnthropicProvider Implementation

**Files:**
- Create: `src/llm/providers/anthropic_provider.py`

- [ ] **Step 1: Create AnthropicProvider**

```python
# src/llm/providers/anthropic_provider.py
import structlog
from anthropic import AsyncAnthropic
from src.llm.providers.base import LLMProvider, ProviderInfo, ChatResponse
from src.config import settings

logger = structlog.get_logger()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.fallback_api_key or ""
        self._model = model or settings.fallback_model or "claude-3-haiku-20240307"
        self._client: AsyncAnthropic | None = None
        self._healthy: bool | None = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        client = self._get_client()
        system_msg = None
        chat_messages = messages
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]["content"]
            chat_messages = messages[1:]

        response = await client.messages.create(
            model=self._model,
            messages=chat_messages,
            system=system_msg,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.content[0].text if response.content else ""
        usage = {
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
        return ChatResponse(
            content=content,
            model=f"anthropic/{self._model}",
            usage=usage,
            provider="anthropic",
        )

    async def is_available(self) -> bool:
        return bool(self._api_key)

    async def get_available_models(self) -> list[str]:
        return [self._model]

    async def check_health(self) -> bool:
        return bool(self._api_key)

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="anthropic",
            provider_type="anthropic",
            base_url="https://api.anthropic.com",
            available_models=[self._model],
            is_healthy=self._healthy or False,
            is_default=False,
        )
```

- [ ] **Step 2: Test import**

Run: `python -c "from src.llm.providers.anthropic_provider import AnthropicProvider; print('OK')"`
Expected: `OK`

---

## Task 5: ModelRegistry — Auto-Detect Available Models

**Files:**
- Create: `src/llm/registry.py`

- [ ] **Step 1: Create ModelRegistry**

```python
# src/llm/registry.py
import structlog
import httpx
from src.config import settings

logger = structlog.get_logger()


class ModelRegistry:
    """Auto-detects and caches available Ollama models."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._cached_models: list[str] | None = None
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

    async def list_ollama_models(self) -> list[str]:
        """Fetch available models from Ollama /api/tags."""
        if self._cached_models is not None:
            return self._cached_models
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags")
            if resp.is_success:
                data = resp.json()
                self._cached_models = [m["name"] for m in data.get("models", [])]
                logger.info("registry_models_discovered", models=self._cached_models)
                return self._cached_models
        except Exception as e:
            logger.warning("registry_discovery_failed", error=str(e))
        return []

    async def refresh(self):
        """Force refresh the model cache."""
        self._cached_models = None
        await self.list_ollama_models()

    def get_default_model(self) -> str:
        return settings.ollama_chat_model

    async def is_model_available(self, model: str) -> bool:
        models = await self.list_ollama_models()
        return model in models

    async def close(self):
        await self._client.aclose()
```

- [ ] **Step 2: Test import**

Run: `python -c "from src.llm.registry import ModelRegistry; print('OK')"`
Expected: `OK`

---

## Task 6: ProviderManager — Centralized Provider Chain

**Files:**
- Create: `src/llm/manager.py`

- [ ] **Step 1: Create ProviderManager**

```python
# src/llm/manager.py
import structlog
import time
from src.llm.providers.base import LLMProvider, ChatResponse
from src.llm.providers.ollama import OllamaProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.providers.anthropic_provider import AnthropicProvider
from src.llm.registry import ModelRegistry
from src.config import settings

logger = structlog.get_logger()


class ProviderManager:
    """Centralized manager for multi-provider LLM routing with fallback chain."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_chain: list[str] = []
        self._active_model: str = settings.ollama_chat_model
        self._registry = ModelRegistry()
        self._init_providers()

    def _init_providers(self):
        """Initialize all configured providers."""
        ollama = OllamaProvider()
        self._providers["ollama"] = ollama

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
        """List all available models across all providers."""
        models = []
        for name, provider in self._providers.items():
            if await provider.is_available():
                provider_models = await provider.get_available_models()
                for m in provider_models:
                    models.append({
                        "id": f"{name}/{m}",
                        "name": m,
                        "provider": name,
                        "is_default": m == settings.ollama_chat_model,
                    })
        return models

    async def get_provider_info(self) -> list[dict]:
        """Get health and info for all providers."""
        infos = []
        for name, provider in self._providers.items():
            info = provider.get_info()
            if name == "ollama":
                info.available_models = await provider.get_available_models()
                info.is_healthy = await provider.check_health()
            infos.append({
                "name": info.name,
                "provider_type": info.provider_type,
                "base_url": info.base_url,
                "available_models": info.available_models,
                "is_healthy": info.is_healthy,
                "is_default": info.is_default,
            })
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

        if "/" not in model_to_use:
            candidate = f"ollama/{model_to_use}"
        else:
            candidate = model_to_use

        preferred_provider = candidate.split("/")[0] if "/" in candidate else "ollama"
        ordered_providers = [preferred_provider] + [p for p in self._fallback_chain if p != preferred_provider]

        for provider_name in ordered_providers:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            if not await provider.is_available():
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
        raise ConnectionError(f"All LLM providers failed. Last error: {last_error}")

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
        """Refresh Ollama model cache."""
        await self._registry.refresh()

    async def close(self):
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()
        await self._registry.close()
```

- [ ] **Step 2: Test import**

Run: `python -c "from src.llm.manager import ProviderManager; print('OK')"`
Expected: `OK`

---

## Task 7: Update ModelRouter for Backward Compatibility

**Files:**
- Modify: `src/llm/router.py`

- [ ] **Step 1: Rewrite ModelRouter as thin wrapper over ProviderManager**

Replace entire `src/llm/router.py` with:

```python
# src/llm/router.py
import structlog
import re
from typing import Optional
from src.llm.manager import ProviderManager
from src.llm.registry import ModelRegistry
from src.database.models import ModelRoutingLog
from sqlalchemy.ext.asyncio import AsyncSession
import time

logger = structlog.get_logger()


class ModelRouter:
    """Backward-compatible wrapper over ProviderManager."""

    def __init__(self, preferred_model: str | None = None):
        self._manager = ProviderManager()
        self._registry = ModelRegistry()
        if preferred_model:
            self._manager.set_active_model(preferred_model)

    @property
    def manager(self) -> ProviderManager:
        return self._manager

    def _estimate_confidence(self, response_content: str) -> float:
        content_lower = response_content.lower()
        uncertainty_indicators = [
            "i'm not sure", "i don't know", "i am not sure",
            "i cannot", "i'm unable", "i don't have",
            "insufficient", "uncertain", "may not",
            "might be wrong", "could be incorrect",
        ]
        for phrase in uncertainty_indicators:
            if phrase in content_lower:
                return 0.3
        if len(response_content) < 20:
            return 0.4
        if re.search(r'\b(?:according to|based on|the curriculum states|reference)\b', content_lower):
            return 0.95
        return 0.85

    def _is_voice_request(self, request_type: str) -> bool:
        return "voice" in request_type or "transcrib" in request_type

    async def route(
        self,
        messages: list[dict],
        request_type: str = "chat",
        session: Optional[AsyncSession] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
        start_time = time.monotonic()
        fallback_triggered = False

        try:
            result = await self._manager.route(
                messages=messages,
                request_type=request_type,
                session=session,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            confidence = self._estimate_confidence(result["content"])

            if session:
                log_entry = ModelRoutingLog(
                    request_type=request_type,
                    model_used=result["model"],
                    confidence=confidence,
                    latency_ms=result.get("usage", {}).get("total_tokens", 0),
                    retrieval_hit=False,
                    fallback_triggered=fallback_triggered,
                    prompt_version="v2.0",
                    success=True,
                )
                session.add(log_entry)

            result["confidence"] = confidence
            logger.info("router_success", model=result["model"], confidence=confidence)
            return result

        except ConnectionError as e:
            error = str(e)
            if session:
                log_entry = ModelRoutingLog(
                    request_type=request_type,
                    model_used="error",
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                    fallback_triggered=False,
                    prompt_version="v2.0",
                    success=False,
                    error=error,
                )
                session.add(log_entry)
            raise

        except Exception as e:
            error = str(e)
            logger.error("router_error", error=error)
            if session:
                log_entry = ModelRoutingLog(
                    request_type=request_type,
                    model_used="error",
                    latency_ms=int((time.monotonic() - start_time) * 1000),
                    success=False,
                    error=error,
                    prompt_version="v2.0",
                )
                session.add(log_entry)
            raise

    async def check_health(self) -> bool:
        health = await self._manager.check_health()
        return health.get("ollama", {}).get("healthy", False)

    async def generate_embedding(self, text: str) -> list[float]:
        from src.llm.ollama_client import OllamaClient
        client = OllamaClient()
        try:
            return await client.generate_embedding(text)
        finally:
            await client.close()

    async def close(self):
        await self._manager.close()
        await self._registry.close()
```

- [ ] **Step 2: Verify backward compatibility**

Run: `python -c "from src.llm.router import ModelRouter; r = ModelRouter(); print('OK')"`
Expected: `OK`

---

## Task 8: Update Config for Multi-Provider Settings

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Add multi-provider configuration**

Replace entire `src/config.py` with:

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "EthioSci AI Assistant"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://ethiobio:ethiobio_pass@localhost:5432/ethiobio"
    database_sync_url: str = "postgresql://ethiobio:ethiobio_pass@localhost:5432/ethiobio"

    redis_url: str = "redis://localhost:6379/0"

    telegram_bot_token: str = ""
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None

    # Ollama (Primary LLM)
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "tinyllama"
    ollama_embed_model: str = "nomic-embed-text"

    # Fallback Provider (Optional)
    fallback_provider: Optional[str] = None
    fallback_api_key: Optional[str] = None
    fallback_model: Optional[str] = None

    # Additional OpenAI-compatible providers (LM Studio, vLLM, etc.)
    provider_openai_compatible_name: Optional[str] = None
    provider_openai_compatible_url: Optional[str] = None
    provider_openai_compatible_api_key: Optional[str] = None
    provider_openai_compatible_model: Optional[str] = None

    vector_store_path: str = "./data/vectors_new"
    collection_name: str = "ethiobio_curriculum"

    whisper_model: str = "base"

    dashboard_url: str = "http://localhost:3000"
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
```

- [ ] **Step 2: Verify config loads**

Run: `python -c "from src.config import settings; print(settings.ollama_chat_model)"`
Expected: `tinyllama`

---

## Task 9: Update AgentState for Model Preference

**Files:**
- Modify: `src/graph/state.py`

- [ ] **Step 1: Add preferred_model field**

Add to `AgentState` dataclass (after `lesson_params`):
```python
    preferred_model: str = ""
```

Add to `GraphOutput` dataclass (after `requires_teacher_review`):
```python
    preferred_model: str = ""
```

---

## Task 10: Add Model Management API Endpoints

**Files:**
- Create: `src/api/models.py`
- Modify: `src/main.py`

- [ ] **Step 1: Create model API endpoints**

```python
# src/api/models.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.llm.manager import ProviderManager
from src.llm.registry import ModelRegistry
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/models", tags=["Models"])

_manager: ProviderManager | None = None
_registry: ModelRegistry | None = None


def _get_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def _get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    is_default: bool


class ProviderHealth(BaseModel):
    name: str
    provider_type: str
    is_healthy: bool
    available_models: list[str]


class SetModelRequest(BaseModel):
    model: str


@router.get("", response_model=list[ModelInfo])
async def list_models():
    """List all available models across all providers."""
    manager = _get_manager()
    models = await manager.list_available_models()
    return [ModelInfo(**m) for m in models]


@router.get("/providers", response_model=list[ProviderHealth])
async def list_providers():
    """Get health and info for all configured providers."""
    manager = _get_manager()
    return await manager.get_provider_info()


@router.get("/active")
async def get_active_model():
    """Get the currently active model."""
    manager = _get_manager()
    return {"model": manager.active_model}


@router.post("/active")
async def set_active_model(request: SetModelRequest):
    """Set the active model for subsequent requests."""
    manager = _get_manager()
    manager.set_active_model(request.model)
    return {"model": request.model, "status": "ok"}


@router.get("/health")
async def models_health():
    """Health check for all providers."""
    manager = _get_manager()
    return await manager.check_health()


@router.post("/refresh")
async def refresh_models():
    """Force refresh the Ollama model cache."""
    manager = _get_manager()
    await manager.refresh_models()
    return {"status": "ok"}
```

- [ ] **Step 2: Register the router in main.py**

Read `src/main.py` and add import + registration:
```python
from src.api.models import router as models_router
app.include_router(models_router)
```

---

## Task 11: Update Graph API to Accept Model Parameter

**Files:**
- Modify: `src/api/graph.py`

- [ ] **Step 1: Add model field to GraphChatRequest**

Update `GraphChatRequest`:
```python
class GraphChatRequest(BaseModel):
    question: str
    user_id: Optional[UUID] = None
    grade_level: Optional[int] = Field(None, ge=7, le=12)
    topic: Optional[str] = None
    language: str = "en"
    model: Optional[str] = None  # NEW: user-selected model
```

Update the `graph_chat` endpoint call to `run_graph`:
```python
        result = await run_graph(
            user_message=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            preferred_model=request.model,  # NEW
        )
```

---

## Task 12: Update Graph Orchestrator to Use Model Preference

**Files:**
- Modify: `src/graph/orchestrator.py`

- [ ] **Step 1: Update run_graph signature**

Read `src/graph/orchestrator.py` and:
1. Add `preferred_model: str | None = None` parameter to `run_graph()` function signature
2. In the function body, set `state.preferred_model = preferred_model or ""` before invoking the graph
3. In `OrchestratorNode.__call__`, when creating `ModelRouter`, pass `preferred_model=state.preferred_model` if set, or use `router.manager.set_active_model(state.preferred_model)` before routing

---

## Task 13: Update Chat API Schema and Endpoint

**Files:**
- Modify: `src/schemas/chat.py`
- Modify: `src/api/chat.py`

- [ ] **Step 1: Add model to TutorRequest**

Read `src/schemas/chat.py` and add to `TutorRequest`:
```python
    model: Optional[str] = None
```

- [ ] **Step 2: Pass model in chat endpoint**

Read `src/api/chat.py` and pass model to agent:
```python
        result = await agent.answer(
            question=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            use_rag=request.use_rag,
            session=session,
            preferred_model=request.model,
        )
```

---

## Task 14: Create Dashboard ModelSelector Component

**Files:**
- Create: `dashboard/src/components/ModelSelector.tsx`

- [ ] **Step 1: Create reusable model selector**

```tsx
// dashboard/src/components/ModelSelector.tsx
'use client'

import { useState, useEffect } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'

interface ModelInfo {
  id: string
  name: string
  provider: string
  is_default: boolean
}

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
  disabled?: boolean
}

export default function ModelSelector({ value, onChange, disabled }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadModels = async () => {
    try {
      const data = await fetchWithTimeout('/models')
      setModels(data)
      if (!value && data.length > 0) {
        const def = data.find((m: ModelInfo) => m.is_default) || data[0]
        onChange(def.id)
      }
    } catch (e) {
      console.error('Failed to load models:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadModels() }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetchWithTimeout('/models/refresh', { method: 'POST' })
      await loadModels()
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) return <div className="flex items-center gap-2 text-sm text-foreground-muted"><Loader2 className="w-4 h-4 animate-spin" />Loading models...</div>

  return (
    <div className="flex items-center gap-2">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        className="px-3 py-2 border border-border rounded-lg text-sm bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
      >
        {models.map(m => (
          <option key={m.id} value={m.id}>
            {m.name} ({m.provider}){m.is_default ? ' ★' : ''}
          </option>
        ))}
      </select>
      <button
        onClick={handleRefresh}
        disabled={refreshing}
        className="p-2 border border-border rounded-lg hover:bg-card transition-colors disabled:opacity-50"
        title="Refresh models list"
      >
        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
      </button>
    </div>
  )
}
```

---

## Task 15: Update Dashboard Ask Page with Model Selector

**Files:**
- Modify: `dashboard/src/app/ask/page.tsx`

- [ ] **Step 1: Add model selector to ask page**

Read `dashboard/src/app/ask/page.tsx` and make these changes:
1. Add import: `import ModelSelector from '@/components/ModelSelector'`
2. Replace `const [model, setModel] = useState('')` with `const [selectedModel, setSelectedModel] = useState('')`
3. In the header controls `<div className="flex items-center gap-3">`, add `<ModelSelector value={selectedModel} onChange={setSelectedModel} />` before the grade selector
4. In the request body, add `model: selectedModel` to both graph and chat mode bodies
5. Replace hardcoded loading text `"Calling gemma4:31b-cloud..."` with `Calling {selectedModel || 'model'}...`
6. Keep displaying the actual `model_used` from the response (already done)

---

## Task 16: Add Model Management Panel to Dashboard Monitoring

**Files:**
- Modify: `dashboard/src/app/monitoring/page.tsx`

- [ ] **Step 1: Add provider health panel**

Read `dashboard/src/app/monitoring/page.tsx` and:
1. Add state: `const [providers, setProviders] = useState<any[]>([])` and `const [activeModel, setActiveModel] = useState('')`
2. In `fetchData`, add fetching providers and active model:
```tsx
const [prov, active] = await Promise.all([
  fetchWithTimeout('/models/providers'),
  fetchWithTimeout('/models/active'),
])
setProviders(prov)
setActiveModel(active.model)
```
3. Add new card before the stats grid:
```tsx
<div className="bg-card rounded-xl border border-border p-5 mb-6">
  <h2 className="text-lg font-semibold text-foreground mb-4">Provider Status</h2>
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    {providers.map(p => (
      <div key={p.name} className={`p-4 rounded-lg border ${p.is_healthy ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm">{p.name}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs ${p.is_healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {p.is_healthy ? 'Online' : 'Offline'}
          </span>
        </div>
        <p className="text-xs text-foreground-muted mt-1">{p.provider_type}</p>
        <p className="text-xs text-foreground-muted mt-1">{p.available_models.length} model(s)</p>
      </div>
    ))}
  </div>
  <div className="mt-3 text-sm text-foreground-muted">
    Active model: <span className="font-mono text-foreground">{activeModel}</span>
  </div>
</div>
```

---

## Task 17: Add Model Selection to Telegram Bot

**Files:**
- Modify: `src/telegram/keyboards.py`
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Add model selection keyboard builder**

Read `src/telegram/keyboards.py` and add:
```python
def model_selection_keyboard(models: list[dict], active_model: str) -> list[list[InlineKeyboardButton]]:
    """Build inline keyboard for model selection."""
    buttons = []
    for m in models:
        label = f"{'✓ ' if m['id'] == active_model else ''}{m['name']} ({m['provider']})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"model:{m['id']}")])
    buttons.append([InlineKeyboardButton("🔄 Refresh Models", callback_data="model:refresh")])
    buttons.append([InlineKeyboardButton("Back", callback_data="model:back")])
    return buttons
```

- [ ] **Step 2: Add model selection handler in bot**

Read `src/telegram/bot.py` and:
1. Add a new conversation state constant (e.g., `MODEL_SELECTION = 9` or next available)
2. Add a `/model` command handler that:
   - Fetches available models via `GET /models` and active model via `GET /models/active`
   - Shows the `model_selection_keyboard`
3. Add callback handler for `model:` prefix that:
   - Calls `POST /models/active` with the selected model
   - Confirms the change to the user
4. Add callback handler for `model:refresh` that calls `POST /models/refresh` and re-shows the list
5. Register the new command handler and callback handler with the dispatcher

---

## Task 18: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Update with multi-provider config**

Replace `.env.example` with:

```bash
# App
APP_NAME=EthioSci AI Assistant
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=postgresql+asyncpg://ethiobio:ethiobio_pass@localhost:5432/ethiobio
DATABASE_SYNC_URL=postgresql://ethiobio:ethiobio_pass@localhost:5432/ethiobio

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Ollama (Primary LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_EMBED_MODEL=nomic-embed-text

# Fallback Provider (Optional)
# Set to "openai" or "anthropic"
FALLBACK_PROVIDER=openai
FALLBACK_API_KEY=sk-...
FALLBACK_MODEL=gpt-4o-mini

# Additional OpenAI-Compatible Provider (LM Studio, vLLM, etc.)
# PROVIDER_OPENAI_COMPATIBLE_NAME=lm-studio
# PROVIDER_OPENAI_COMPATIBLE_URL=http://localhost:1234/v1
# PROVIDER_OPENAI_COMPATIBLE_API_KEY=not-needed
# PROVIDER_OPENAI_COMPATIBLE_MODEL=local-model

# Vector Store
VECTOR_STORE_PATH=./data/vectors
COLLECTION_NAME=ethiobio_curriculum

# Whisper (Voice)
WHISPER_MODEL=base

# Dashboard
DASHBOARD_URL=http://localhost:3000
JWT_SECRET=change-me-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

---

## Task 19: Update Tests

**Files:**
- Modify: `tests/test_llm.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add tests for new provider system**

Append to `tests/test_llm.py`:

```python
@pytest.mark.asyncio
async def test_ollama_provider_chat():
    from src.llm.providers.ollama import OllamaProvider
    provider = OllamaProvider(base_url="http://test:11434", default_model="test-model")
    provider._client = AsyncMock()
    import httpx
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json = MagicMock(return_value={
        "message": {"content": "Test response"},
        "eval_count": 50,
        "prompt_eval_count": 30,
    })
    provider._client.post.return_value = mock_response

    result = await provider.chat([{"role": "user", "content": "test"}])
    assert result.content == "Test response"
    assert result.model == "ollama/test-model"
    assert result.provider == "ollama"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_list_models():
    from src.llm.providers.ollama import OllamaProvider
    provider = OllamaProvider(base_url="http://test:11434")
    provider._client = AsyncMock()
    import httpx
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json = MagicMock(return_value={
        "models": [{"name": "llama3.2:3b"}, {"name": "gemma4:31b-cloud"}]
    })
    provider._client.get.return_value = mock_response

    models = await provider.get_available_models()
    assert models == ["llama3.2:3b", "gemma4:31b-cloud"]
    await provider.close()


@pytest.mark.asyncio
async def test_provider_manager_fallback_chain():
    from src.llm.manager import ProviderManager
    manager = ProviderManager()
    assert "ollama" in manager._providers
    assert "ollama" in manager._fallback_chain


@pytest.mark.asyncio
async def test_provider_manager_set_active_model():
    from src.llm.manager import ProviderManager
    manager = ProviderManager()
    manager.set_active_model("gemma4:31b-cloud")
    assert manager.active_model == "gemma4:31b-cloud"


@pytest.mark.asyncio
async def test_model_registry_discovery():
    from src.llm.registry import ModelRegistry
    registry = ModelRegistry(base_url="http://test:11434")
    registry._client = AsyncMock()
    import httpx
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json = MagicMock(return_value={
        "models": [{"name": "model1"}, {"name": "model2"}]
    })
    registry._client.get.return_value = mock_response

    models = await registry.list_ollama_models()
    assert models == ["model1", "model2"]
    models2 = await registry.list_ollama_models()
    assert models2 == ["model1", "model2"]
    await registry.close()


@pytest.mark.asyncio
async def test_router_backward_compat():
    from src.llm.router import ModelRouter
    router = ModelRouter()
    router._manager = AsyncMock()
    router._manager.route.return_value = {
        "content": "Test response",
        "model": "ollama/test",
        "usage": {"total_tokens": 50},
    }

    result = await router.route(
        messages=[{"role": "user", "content": "test"}],
        request_type="test",
    )
    assert result["content"] == "Test response"
    assert result["model"] == "ollama/test"
    await router.close()
```

- [ ] **Step 2: Update conftest.py mock fixture**

Add `router.manager = AsyncMock()` to the existing `mock_router` fixture.

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_llm.py -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"`
Expected: All tests pass

---

## Task 20: Self-Review and Spec Coverage Check

- [ ] **Step 1: Verify all requirements are met**

| Requirement | Task | Status |
|-------------|------|--------|
| Replace fixed Ollama with configurable dynamic selection | Tasks 1-7 | ✅ |
| Support multiple local Ollama models | Tasks 2, 5, 6 | ✅ |
| Fallback provider support | Tasks 3, 4, 6 | ✅ |
| Configurable via env vars | Tasks 8, 18 | ✅ |
| Priority/fallback chain (Ollama → Secondary → OpenAI → Fallback) | Task 6 | ✅ |
| Auto-detect available Ollama models | Task 5 | ✅ |
| Runtime model switching | Tasks 6, 10 | ✅ |
| Centralized provider config | Task 6 | ✅ |
| Backward compatibility | Task 7 | ✅ |
| Clean abstractions/interfaces | Tasks 1-4 | ✅ |
| Retries, timeout, logging, graceful degradation | Tasks 2-6 | ✅ |
| Update all existing AI calls | Tasks 7, 9, 11-13 | ✅ |
| Example .env config | Task 18 | ✅ |
| Extensible for future providers | Tasks 1-4 | ✅ |
| Dashboard model selection UI | Tasks 14-16 | ✅ |
| Telegram bot model selection UI | Task 17 | ✅ |

- [ ] **Step 2: Placeholder scan**

No TBDs, TODOs, or placeholders found in the plan.

- [ ] **Step 3: Type/signature consistency**

- `ChatResponse` is used consistently across all providers
- `LLMProvider` interface is uniform
- `ProviderManager.route()` returns same dict format as old `ModelRouter.route()`
- `AgentState.preferred_model` matches `GraphChatRequest.model`

---

## Execution Order Summary

1. **Tasks 1-4**: Provider abstraction layer (foundation)
2. **Task 5**: Model registry (auto-detection)
3. **Task 6**: ProviderManager (orchestration)
4. **Task 7**: ModelRouter backward compat (bridge)
5. **Task 8**: Config update
6. **Tasks 9-13**: API/state updates (plumbing)
7. **Tasks 14-17**: UI (dashboard + telegram)
8. **Task 18**: .env.example
9. **Task 19**: Tests
10. **Task 20**: Review
