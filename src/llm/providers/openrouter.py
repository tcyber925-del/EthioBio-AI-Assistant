import structlog
from openai import AsyncOpenAI

from src.config import settings
from src.llm.providers.base import ChatResponse, UsageInfo
from src.llm.providers.openai_provider import OpenAIProvider

logger = structlog.get_logger()


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter API provider — routes through openrouter.ai with required headers."""

    def __init__(self):
        self._name = "openrouter"
        self._api_key = settings.openrouter_api_key or ""
        self._model = settings.openrouter_default_model or "openai/gpt-4o"
        self._base_url = settings.openrouter_base_url
        self._client: AsyncOpenAI | None = None
        self._healthy: bool | None = None
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

    async def is_available(self) -> bool:
        available = bool(self._api_key)
        self._healthy = available
        return available

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
