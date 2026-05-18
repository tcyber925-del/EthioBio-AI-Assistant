# src/llm/router.py
import re
import time
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ModelRoutingLog
from src.llm.manager import ProviderManager
from src.llm.registry import ModelRegistry

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
        if re.search(
            r'\b(?:according to|based on|the curriculum states|reference)\b',
            content_lower,
        ):
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
