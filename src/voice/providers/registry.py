from typing import Optional

import structlog

from src.config import settings
from src.llm.circuit_breaker import CircuitBreaker
from src.observability.voice_metrics import (
    STTTimer,
    TTSTimer,
    record_provider_error,
    record_stt_request,
    record_tts_request,
)

from .azure import AzureSTTProvider
from .base import SpeechProvider
from .edge_tts import EdgeTTSProvider
from .gemini import GeminiTTSProvider
from .groq import GroqSTTProvider
from .types import (
    SpeechProviderInfo,
    SynthesisResult,
    TranscriptResult,
    resolve_tts_language,
)

logger = structlog.get_logger(__name__)


class SpeechProviderRegistry:
    """Config-driven registry for speech providers with automatic fallback.

    Mirrors the LLM ProviderManager pattern. Each provider has its own
    CircuitBreaker. The registry tries primary providers first, then
    falls back through the chain.
    """

    def __init__(self):
        self._stt_providers: dict[str, SpeechProvider] = {}
        self._tts_providers: dict[str, SpeechProvider] = {}
        self._stt_fallback_chain: list[str] = []
        self._tts_fallback_chain: list[str] = []
        self._breakers: dict[str, CircuitBreaker] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        if settings.groq_api_key:
            self._stt_providers["groq"] = GroqSTTProvider()
            self._stt_fallback_chain = ["groq"]
        if settings.azure_speech_key and settings.azure_speech_region:
            azure = AzureSTTProvider()
            self._stt_providers["azure"] = azure
            self._stt_fallback_chain.insert(0, "azure")
        if settings.gemini_api_key:
            self._tts_providers["gemini-tts"] = GeminiTTSProvider()
            self._tts_fallback_chain = ["gemini-tts", "edge-tts"]
        tts = EdgeTTSProvider()
        self._tts_providers["edge-tts"] = tts
        if not self._tts_fallback_chain:
            self._tts_fallback_chain = ["edge-tts"]
        if settings.azure_speech_key and settings.azure_speech_region:
            self._tts_providers["azure"] = AzureSTTProvider()
            self._tts_fallback_chain.insert(0, "azure")
        logger.info(
            "speech_providers_initialized",
            stt=list(self._stt_providers),
            tts=list(self._tts_providers),
        )

    def _get_breaker(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name)
        return self._breakers[name]

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/webm",
        preferred_provider: Optional[str] = None,
    ) -> TranscriptResult:
        ordered = self._stt_fallback_chain.copy()
        if preferred_provider and preferred_provider in ordered:
            ordered.remove(preferred_provider)
            ordered.insert(0, preferred_provider)

        last_error: Optional[Exception] = None
        for name in ordered:
            provider = self._stt_providers.get(name)
            if not provider:
                continue
            breaker = self._get_breaker(name)
            if not breaker.is_available:
                logger.warning("provider_breaker_open", provider=name)
                continue
            if not await provider.is_available():
                logger.warning("provider_not_available", provider=name)
                continue
            try:
                with STTTimer(name):
                    result = await provider.transcribe(
                        audio, language=language, mime_type=mime_type
                    )
                breaker.record_success()
                record_stt_request(name, language or "unknown", "ok")
                return result
            except Exception as e:
                breaker.record_failure()
                record_stt_request(name, language or "unknown", "error")
                record_provider_error(name, "stt")
                logger.warning("provider_failed", provider=name, error=str(e))
                last_error = e

        raise RuntimeError(
            f"All STT providers failed. Last error: {last_error}"
        ) from last_error

    async def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        ordered = self._tts_fallback_chain.copy()

        # Platform supports Amharic and English only. Clamp any input
        # (None/"both"/unsupported codes) so providers never auto-pick
        # a language outside those two.
        tts_language = resolve_tts_language(language, text)

        last_error: Optional[Exception] = None
        for name in ordered:
            provider = self._tts_providers.get(name)
            if not provider:
                continue
            breaker = self._get_breaker(name)
            if not breaker.is_available:
                continue
            if not await provider.is_available():
                continue
            try:
                with TTSTimer(name):
                    result = await provider.synthesize(text, language=tts_language)
                breaker.record_success()
                record_tts_request(name, "ok")
                return result
            except Exception as e:
                breaker.record_failure()
                record_tts_request(name, "error")
                record_provider_error(name, "tts")
                logger.warning("provider_tts_failed", provider=name, error=str(e))
                last_error = e

        raise RuntimeError(
            f"All TTS providers failed. Last error: {last_error}"
        ) from last_error

    def get_providers_info(self) -> list[SpeechProviderInfo]:
        infos: list[SpeechProviderInfo] = []
        for _name, provider in {**self._stt_providers, **self._tts_providers}.items():
            info = provider.get_info()
            infos.append(info)
        return infos

    def get_stt_providers(self) -> dict[str, SpeechProvider]:
        return dict(self._stt_providers)

    def get_tts_providers(self) -> dict[str, SpeechProvider]:
        return dict(self._tts_providers)

    def get_provider_status(self) -> dict:
        stt = []
        for name in self._stt_fallback_chain:
            provider = self._stt_providers.get(name)
            breaker = self._breakers.get(name)
            stt.append({
                "name": name,
                "type": "stt",
                "configured": provider is not None,
                "breaker": breaker.to_dict() if breaker else None,
            })
        tts = []
        for name in self._tts_fallback_chain:
            provider = self._tts_providers.get(name)
            breaker = self._breakers.get(name)
            tts.append({
                "name": name,
                "type": "tts",
                "configured": provider is not None,
                "breaker": breaker.to_dict() if breaker else None,
            })
        return {
            "stt": stt,
            "tts": tts,
            "stt_fallback_chain": self._stt_fallback_chain,
            "tts_fallback_chain": self._tts_fallback_chain,
        }
