import structlog
from anthropic import AsyncAnthropic
from anthropic.types import TextBlock

from src.config import settings
from src.llm.providers.base import ChatResponse, LLMProvider, ProviderInfo, UsageInfo

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
        system_msg: str | None = None
        chat_messages: list[dict] = messages
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]["content"]
            chat_messages = messages[1:]

        kwargs: dict = {
            "model": self._model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)
        content = ""
        if response.content:
            first_block = response.content[0]
            if isinstance(first_block, TextBlock):
                content = first_block.text
        usage: UsageInfo = {
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
