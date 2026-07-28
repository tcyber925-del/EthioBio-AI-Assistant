from typing import Optional

import httpx
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import SpeechProviderInfo, TranscriptResult

logger = structlog.get_logger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_STT_MODEL = "whisper-large-v3-turbo"


class GroqSTTProvider(SpeechProvider):
    """Speech-to-text provider using Groq's Whisper large-v3-turbo.

    Uses the OpenAI-compatible transcription endpoint. Free tier allows
    ~8 audio-hours/day. Supports Amharic (am), English (en), and
    Amharic/English code-switching (omit language for auto-detect).
    """

    @property
    def name(self) -> str:
        return "groq"

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ) -> TranscriptResult:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY not configured")

        data: dict = {"model": GROQ_STT_MODEL}
        if language:
            data["language"] = language

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{GROQ_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": ("audio.ogg", audio, mime_type)},
                data=data,
            )

        if response.status_code != 200:
            logger.error("groq_stt_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Groq STT failed: {response.status_code} {response.text}")

        result = response.json()
        detected_language = result.get("language", language or "am")
        return TranscriptResult(
            text=result["text"],
            language=detected_language,
        )

    async def is_available(self) -> bool:
        return bool(settings.groq_api_key)

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="groq",
            provider_type="openai-compatible",
            supported_languages=["am", "en"],
            stt_supported=True,
            tts_supported=False,
            is_healthy=bool(settings.groq_api_key),
        )
