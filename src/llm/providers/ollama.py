import httpx
import structlog

from src.config import settings
from src.llm.providers.base import ChatResponse, LLMProvider, ProviderInfo, UsageInfo

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
            usage=UsageInfo(
                total_tokens=result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
            ),
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
