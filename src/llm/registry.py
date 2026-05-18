import httpx
import structlog

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
