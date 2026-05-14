import structlog
import re
from typing import Optional
from src.llm.ollama_client import OllamaClient
from src.llm.fallback import FallbackProvider
from src.database.models import ModelRoutingLog
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import time

logger = structlog.get_logger()


class ModelRouter:
    def __init__(self):
        self.ollama = OllamaClient()
        self.fallback = FallbackProvider()

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
        retrieval_hit = False
        fallback_triggered = False
        model_used = f"ollama/{self.ollama.model}"
        error = None

        try:
            response = await self.ollama.chat(messages, temperature=temperature, max_tokens=max_tokens)
            content = response["content"]
            confidence = self._estimate_confidence(content)

            if confidence < 0.5 and await self.fallback.is_available():
                logger.info("router_fallback_low_confidence", confidence=confidence)
                response = await self.fallback.chat(messages, temperature=temperature, max_tokens=max_tokens)
                model_used = f"fallback/{response['model']}"
                fallback_triggered = True

            latency = int((time.monotonic() - start_time) * 1000)

            if session:
                log_entry = ModelRoutingLog(
                    request_type=request_type,
                    model_used=model_used,
                    confidence=confidence,
                    latency_ms=latency,
                    retrieval_hit=retrieval_hit,
                    fallback_triggered=fallback_triggered,
                    prompt_version="v1.1",
                    success=True,
                )
                session.add(log_entry)

            logger.info("router_success", model=model_used, confidence=confidence, latency=latency)
            return {
                "content": response["content"],
                "model": model_used,
                "confidence": confidence,
                "usage": response.get("usage"),
            }

        except ConnectionError as e:
            if await self.fallback.is_available():
                logger.warning("router_ollama_down_using_fallback")
                response = await self.fallback.chat(messages, temperature=temperature, max_tokens=max_tokens)
                model_used = f"fallback/{response['model']}"
                fallback_triggered = True
                latency = int((time.monotonic() - start_time) * 1000)

                if session:
                    log_entry = ModelRoutingLog(
                        request_type=request_type,
                        model_used=model_used,
                        latency_ms=latency,
                        fallback_triggered=True,
                        prompt_version="v1.1",
                        success=True,
                    )
                    session.add(log_entry)

                return {
                    "content": response["content"],
                    "model": model_used,
                    "confidence": 0.7,
                    "usage": response.get("usage"),
                }
            error = str(e)
            raise

        except Exception as e:
            error = str(e)
            logger.error("router_error", error=error)
            latency = int((time.monotonic() - start_time) * 1000)
            if session:
                log_entry = ModelRoutingLog(
                    request_type=request_type,
                    model_used=model_used,
                    latency_ms=latency,
                    success=False,
                    error=error,
                    prompt_version="v1.1",
                )
                session.add(log_entry)
            raise

    async def check_health(self) -> bool:
        return await self.ollama.check_health()

    async def generate_embedding(self, text: str) -> list[float]:
        return await self.ollama.generate_embedding(text)

    async def close(self):
        await self.ollama.close()
