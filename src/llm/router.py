# src/llm/router.py
import re
import time
from collections.abc import AsyncGenerator
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.models import ModelRoutingLog
from src.llm.manager import ProviderManager
from src.llm.ollama_client import OllamaClient
from src.llm.registry import ModelRegistry
from src.observability.tracing import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_REQUEST_TEMPERATURE,
    GEN_AI_RESPONSE_FINISH_REASONS,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    tracer,
)

logger = structlog.get_logger()

try:
    import langsmith as _langsmith
except ImportError:  # pragma: no cover - langsmith optional
    _langsmith = None


def _llm_inputs(inputs: dict) -> dict:
    """Select JSON-safe inputs for the LangSmith trace (excludes the SQLAlchemy session).

    langsmith calls this with a single dict keyed by the wrapped function's
    parameter names (``self`` removed), e.g. {"messages", "request_type",
    "session", ...}.
    """
    return {
        "messages": inputs.get("messages", []),
        "request_type": inputs.get("request_type", "chat"),
    }


def _llm_outputs(outputs):
    if isinstance(outputs, dict):
        return {
            "model": outputs.get("model", ""),
            "usage": outputs.get("usage", {}),
            "confidence": outputs.get("confidence", 0.0),
        }
    return outputs


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
            "i'm not sure",
            "i don't know",
            "i am not sure",
            "i cannot",
            "i'm unable",
            "i don't have",
            "insufficient",
            "uncertain",
            "may not",
            "might be wrong",
            "could be incorrect",
        ]
        for phrase in uncertainty_indicators:
            if phrase in content_lower:
                return 0.3
        if len(response_content) < 20:
            return 0.4
        if re.search(
            r"\b(?:according to|based on|the curriculum states|reference)\b",
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
        preferred_model: str | None = None,
    ) -> dict:
        start_time = time.monotonic()
        fallback_triggered = False

        try:
            with tracer.start_as_current_span("chat llm") as span:
                span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
                span.set_attribute(GEN_AI_REQUEST_TEMPERATURE, temperature)

                result = await self._manager.route(
                    messages=messages,
                    request_type=request_type,
                    session=session,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    preferred_model=preferred_model,
                )

                model_name = result.get("model", "unknown")
                span.set_attribute(GEN_AI_REQUEST_MODEL, model_name)
                span.set_attribute(GEN_AI_PROVIDER_NAME, request_type)
                if "usage" in result:
                    usage = result["usage"]
                    span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, usage.get("prompt_tokens", 0))
                    span.set_attribute(
                        GEN_AI_USAGE_OUTPUT_TOKENS, usage.get("completion_tokens", 0)
                    )
                span.set_attribute(GEN_AI_RESPONSE_FINISH_REASONS, ["stop"])
                span.update_name(f"chat {model_name}")

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

    async def route_stream(
        self,
        messages: list[dict],
        request_type: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        preferred_model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response token by token through the provider chain."""
        try:
            async for token in self._manager.route_stream(
                messages=messages,
                request_type=request_type,
                temperature=temperature,
                max_tokens=max_tokens,
                preferred_model=preferred_model,
            ):
                yield token
        except Exception as e:
            logger.error("router_stream_error", error=str(e))
            raise

    async def check_health(self) -> bool:
        health = await self._manager.check_health()
        return health.get("ollama", {}).get("healthy", False)

    async def generate_embedding(self, text: str) -> list[float]:
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        try:
            return await provider.generate_embedding(text)
        except Exception:
            logger.warning("openrouter_embed_failed, falling back to Ollama", exc_info=True)
            client = OllamaClient()
            try:
                return await client.generate_embedding(text)
            finally:
                await client.close()

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        try:
            return await provider.generate_embeddings(list(texts))
        except Exception:
            logger.warning("openrouter_embed_batch_failed, falling back to Ollama", exc_info=True)
            results = []
            for text in texts:
                results.append(await self.generate_embedding(text))
            return results

    async def close(self):
        await self._manager.close()
        await self._registry.close()


if _langsmith is not None and settings.langsmith_tracing_enabled:
    ModelRouter.route = _langsmith.traceable(
        run_type="llm",
        name="chat_llm",
        process_inputs=_llm_inputs,
        process_outputs=_llm_outputs,
    )(ModelRouter.route)
