import io
from typing import Optional

import edge_tts
import structlog

from .base import SpeechProvider
from .types import SpeechProviderInfo, SynthesisResult

logger = structlog.get_logger(__name__)

LANGUAGE_VOICES: dict[str, str] = {
    "am": "am-ET-AmehaNeural",
    "en": "en-US-JennyNeural",
}

FALLBACK_VOICE = "en-US-JennyNeural"


class EdgeTTSProvider(SpeechProvider):
    """Text-to-speech provider using Microsoft Edge's online TTS service.

    Free, no API key required. Supports Amharic (am-ET-AmehaNeural)
    and English (en-US-JennyNeural) voices.
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
        voice_name = voice or LANGUAGE_VOICES.get(language or "", FALLBACK_VOICE)
        communicate = edge_tts.Communicate(text, voice_name)
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
            communicate = edge_tts.Communicate("test", "en-US-JennyNeural")
            async for _ in communicate.stream():
                break
            return True
        except Exception:
            return False

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="edge-tts",
            provider_type="edge",
            supported_languages=list(LANGUAGE_VOICES),
            stt_supported=False,
            tts_supported=True,
            is_healthy=True,
        )


def _estimate_duration(audio_bytes: bytes) -> float:
    """Rough estimate: ~16 KB/s for MP3 speech at 128 kbps."""
    return len(audio_bytes) / (16 * 1024)
