from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog

from src.config import settings
from src.llm.providers.base import ChatResponse, LLMProvider, ProviderInfo, UsageInfo

logger = structlog.get_logger()


class AddisAIProvider(LLMProvider):
    """Addis AI provider for African language models (Amharic, Afaan Oromo)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
    ):
        self.base_url = (base_url or getattr(settings, "addis_ai_base_url", "https://api.addisassistant.com")).rstrip("/")
        self.api_key = api_key or getattr(settings, "addis_ai_api_key", "")
        self._default_model = default_model or getattr(settings, "addis_ai_chat_model", "Addis-፩-አሌፍ")
        self._available_models: list[str] | None = None
        self._healthy: bool | None = None

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        } if self.api_key else {"Content-Type": "application/json"}

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers=headers,
        )

    @property
    def name(self) -> str:
        return "addis-ai"

    def _resolve_model(self, messages: list[dict]) -> str:
        """Resolve model from system message or use default."""
        model = self._default_model
        for msg in messages:
            if msg.get("role") == "system" and msg.get("content", "").startswith("__model__:"):
                model = msg["content"].split(":", 1)[1]
                break
        return model

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        model = self._resolve_model(messages)

        # Map model names to API model identifiers
        model_map = {
            "Addis-፩-አሌፍ": "Addis-፩-አሌፍ",
            "addis-alef": "Addis-፩-አሌፍ",
            "Addis-፩-አሌፍ-v2": "Addis-፩-አሌፍ",
        }
        api_model = model_map.get(model, model)

        payload = {
            "model": api_model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await self._client.post(f"{self.base_url}/v1/chat/completions", json=payload)
        response.raise_for_status()
        result = response.json()

        choice = result.get("choices", [{}])[0]
        usage = result.get("usage", {})

        return ChatResponse(
            content=choice.get("message", {}).get("content", ""),
            model=f"addis-ai/{api_model}",
            usage=UsageInfo(
                total_tokens=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            ),
            provider="addis-ai",
        )

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        model = self._resolve_model(messages)

        model_map = {
            "Addis-፩-አሌፍ": "Addis-፩-አሌፍ",
            "addis-alef": "Addis-፩-አሌፍ",
            "Addis-፩-አሌፍ-v2": "Addis-፩-አሌፍ",
        }
        api_model = model_map.get(model, model)

        payload = {
            "model": api_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with self._client.stream(
            "POST", f"{self.base_url}/v1/chat/completions", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def is_available(self) -> bool:
        return await self.check_health()

    async def get_available_models(self) -> list[str]:
        if self._available_models is not None:
            return self._available_models
        try:
            # Addis AI doesn't have a standard /models endpoint yet
            # Return known models
            self._available_models = [
                "Addis-፩-አሌፍ",  # Main LLM
                "አሌፍ-Audio-AM",  # TTS Amharic
                "አሌፍ-Audio-OM",  # TTS Afaan Oromo
                "addis-whisper",  # STT
                "አሌፍ-1.2-realtime-audio",  # Realtime
            ]
            self._healthy = True
            return self._available_models
        except Exception:
            pass
        self._healthy = False
        return []

    async def check_health(self) -> bool:
        if not self.api_key:
            self._healthy = False
            return False
        try:
            # Use a simple models list call or chat completion to check health
            resp = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "Addis-፩-አሌፍ",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=10.0,
            )
            self._healthy = resp.is_success
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="addis-ai",
            provider_type="addis-ai",
            base_url=self.base_url,
            available_models=self._available_models or [],
            is_healthy=self._healthy or False,
            is_default=False,
        )

    async def close(self):
        await self._client.aclose()