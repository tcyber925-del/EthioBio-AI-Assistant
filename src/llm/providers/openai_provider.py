import structlog
from openai import AsyncOpenAI

from src.config import settings
from src.llm.providers.base import ChatResponse, LLMProvider, ProviderInfo, UsageInfo

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
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
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
