import io
from typing import Optional

import edge_tts
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import SpeechProviderInfo, SynthesisResult

logger = structlog.get_logger(__name__)


def _voice_for(language: Optional[str]) -> str:
    """Map a clamped am/en language code to the configured edge-tts voice."""
    if language == "am":
        return settings.edge_tts_am_voice
    return settings.edge_tts_en_voice


class EdgeTTSProvider(SpeechProvider):
    """Text-to-speech provider using Microsoft Edge's online TTS service.

    Free, no API key required. Supports Amharic (am-ET-AmehaNeural)
    and English (en-US-AriaNeural) voices, both env-configurable.
    """

    @property
    def name(self) -> str:
        return "edge-tts"

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ):
        raise NotImplementedError("EdgeTTSProvider does not support STT")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        voice_name = voice or _voice_for(language)
        communicate = edge_tts.Communicate(
            text,
            voice_name,
            rate=settings.edge_tts_rate,
            pitch=settings.edge_tts_pitch,
            volume=settings.edge_tts_volume,
        )
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        audio_bytes = buffer.getvalue()
        return SynthesisResult(
            audio_bytes=audio_bytes,
            format="mp3",
            duration_seconds=_estimate_duration(audio_bytes),
        )

    async def is_available(self) -> bool:
        try:
            communicate = edge_tts.Communicate("test", settings.edge_tts_en_voice)
            async for _ in communicate.stream():
                break
            return True
        except Exception:
            return False

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="edge-tts",
            provider_type="edge",
            supported_languages=["am", "en"],
            stt_supported=False,
            tts_supported=True,
            is_healthy=True,
        )


def _estimate_duration(audio_bytes: bytes) -> float:
    """Rough estimate: ~16 KB/s for MP3 speech at 128 kbps."""
    return len(audio_bytes) / (16 * 1024)
