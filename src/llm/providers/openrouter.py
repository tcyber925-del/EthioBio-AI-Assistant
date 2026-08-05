from collections.abc import AsyncGenerator

import httpx
import structlog
from openai import AsyncOpenAI

from src.config import settings
from src.llm.providers.base import ChatResponse, UsageInfo
from src.llm.providers.openai_provider import OpenAIProvider

logger = structlog.get_logger()


class OpenRouterProvider(OpenAIProvider):
    _OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

    def __init__(self):
        self._name = "openrouter"
        self._api_key = settings.openrouter_api_key or ""
        self._model = settings.openrouter_default_model or "openai/gpt-4o"
        self._base_url = settings.openrouter_base_url
        self._client: AsyncOpenAI | None = None
        self._healthy: bool | None = None
        self._available_models: list[str] | None = None
        self._extra_headers = {
            "HTTP-Referer": "https://ethiobio.ai",
            "X-Title": "EthioBio AI Assistant",
        }

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
            extra_headers=self._extra_headers,
        )
        content = response.choices[0].message.content or ""
        usage: UsageInfo = {"total_tokens": response.usage.total_tokens if response.usage else 0}
        return ChatResponse(
            content=content,
            model=f"{self._name}/{self._model}",
            usage=usage,
            provider=self._name,
        )

    async def generate_embedding(self, text: str) -> list[float]:
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=settings.openrouter_embed_model,
            input=texts,
            encoding_format="float",
            extra_headers=self._extra_headers,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers=self._extra_headers,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def is_available(self) -> bool:
        available = bool(self._api_key)
        self._healthy = available
        return available

    async def get_available_models(self) -> list[str]:
        if self._available_models is not None:
            return self._available_models
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self._OPENROUTER_MODELS_URL)
                if resp.is_success:
                    data = resp.json()
                    free_models = [
                        m["id"]
                        for m in data.get("data", [])
                        if m.get("pricing", {}).get("prompt") == "0"
                    ]
                    self._available_models = sorted(free_models)
                    logger.info(
                        "openrouter_models_discovered",
                        total=len(data.get("data", [])),
                        free=len(self._available_models),
                    )
                    return self._available_models
        except Exception as e:
            logger.warning("openrouter_models_fetch_failed", error=str(e))
        self._available_models = []
        return self._available_models

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
