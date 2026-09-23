import httpx
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import (
    SpeechProviderInfo,
    SynthesisResult,
    TranscriptResult,
    resolve_tts_language,
)

logger = structlog.get_logger(__name__)

# Voice catalog - maps to Addis Voices 2 voice IDs
_ADDIS_VOICES = {
    # Amharic voices
    "am-hamen": {"name": "Hamen", "language": "am", "gender": "male", "style": "conversational"},
    "am-yohannes": {"name": "Yohannes", "language": "am", "gender": "male", "style": "narration"},
    "am-tesfa": {"name": "Tesfa", "language": "am", "gender": "male", "style": "commercial"},
    "am-muaz": {"name": "Muaz", "language": "am", "gender": "male", "style": "commercial"},
    "am-roba": {"name": "Roba", "language": "am", "gender": "male", "style": "commercial"},
    "am-nejat": {"name": "Nejat", "language": "am", "gender": "female", "style": "conversational"},
    "am-loza": {"name": "Loza", "language": "am", "gender": "female", "style": "narration"},
    "am-nahom": {"name": "Nahom", "language": "am", "gender": "male", "style": "narration"},
    "am-simon": {"name": "Simon", "language": "am", "gender": "male", "style": "commercial"},
    "am-amanuel": {"name": "Amanuel", "language": "am", "gender": "male", "style": "narration"},
    "am-tewodros": {"name": "Tewodros", "language": "am", "gender": "male", "style": "commercial"},
    "am-kaleb": {"name": "Kaleb", "language": "am", "gender": "male", "style": "narration"},
    "am-dawit": {"name": "Dawit", "language": "am", "gender": "male", "style": "narration"},
    "am-meron": {"name": "Meron", "language": "am", "gender": "female", "style": "narration"},
    "am-makda": {"name": "Makda", "language": "am", "gender": "female", "style": "news"},
    "am-feven": {"name": "Feven", "language": "am", "gender": "female", "style": "conversational"},
    "am-melat": {"name": "Melat", "language": "am", "gender": "female", "style": "conversational"},
    "am-dibora": {"name": "Dibora", "language": "am", "gender": "female", "style": "educational"},
    "am-sara": {"name": "Sara", "language": "am", "gender": "female", "style": "narration"},
    # Afaan Oromo voices
    "om-hamen": {"name": "Hamen", "language": "om", "gender": "male", "style": "conversational"},
    "om-yohannes": {"name": "Yohannes", "language": "om", "gender": "male", "style": "narration"},
    "om-tesfa": {"name": "Tesfa", "language": "om", "gender": "male", "style": "commercial"},
    "om-muaz": {"name": "Muaz", "language": "om", "gender": "male", "style": "commercial"},
    "om-roba": {"name": "Roba", "language": "om", "gender": "male", "style": "commercial"},
    "om-nejat": {"name": "Nejat", "language": "om", "gender": "female", "style": "conversational"},
    "om-loza": {"name": "Loza", "language": "om", "gender": "female", "style": "narration"},
    "om-nahom": {"name": "Nahom", "language": "om", "gender": "male", "style": "narration"},
}


def _default_voice_for(language: str) -> str:
    """Get default voice ID for a language."""
    if language == "am":
        return "am-hamen"  # Default Amharic voice
    if language == "om":
        return "om-hamen"  # Default Afaan Oromo voice
    return "am-hamen"  # fallback


class AddisAIProvider(SpeechProvider):
    """Addis AI provider for TTS (Addis Voices 2) and STT (addis-whisper)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = (base_url or getattr(settings, "addis_ai_base_url", "https://api.addisassistant.com")).rstrip("/")
        self.api_key = api_key or getattr(settings, "addis_ai_api_key", "")
        self._healthy: bool | None = None

        if not self.api_key:
            logger.warning("addis_ai_provider_missing_api_key")
            self._client = None
        else:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

    @property
    def name(self) -> str:
        return "addis-ai"

    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
        mime_type: str = "audio/ogg",
    ) -> TranscriptResult:
        """Transcribe audio using addis-whisper model."""
        if not self._client:
            raise RuntimeError("Addis AI provider not configured (missing API key)")

        # Map language to language_code expected by API
        lang_code = "am" if (language and language.startswith("am")) else "om"

        # Prepare multipart form data
        files = {
            "audio": ("audio.ogg", audio, mime_type),
            "request_data": (None, '{"language_code": "' + lang_code + '"}', "application/json"),
        }

        headers = {"x-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0), headers=headers) as client:
            response = await client.post(
                f"{self.base_url}/v1/audio/transcriptions",
                files=files,
            )
            response.raise_for_status()
            result = response.json()

        data = result.get("data", {})
        return TranscriptResult(
            text=data.get("transcription", ""),
            language=lang_code,
            language_confidence=result.get("confidence", 0.9),
            duration_seconds=data.get("usage_metadata", {}).get("totalBilledDuration", 0),
        )

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        language: str | None = None,
    ) -> SynthesisResult:
        """Synthesize speech using Addis Voices 2."""
        if not self._client:
            raise RuntimeError("Addis AI provider not configured (missing API key)")

        # Resolve language - use the resolver from types
        tts_language = resolve_tts_language(language, text)

        # Map to Addis AI language code
        lang_code = "am" if tts_language == "am" else "om"

        # Get voice ID - use provided voice or default for language
        if voice and voice in _ADDIS_VOICES:
            voice_id = voice
        else:
            voice_id = _default_voice_for(lang_code)

        payload = {
            "model": "Addis Voices 2",
            "input": text,
            "voice": voice_id,
            "language": lang_code,
        }

        response = await self._client.post(
            f"{self.base_url}/v1/audio/speech",
            json=payload,
        )
        response.raise_for_status()

        # Response is audio bytes
        audio_bytes = response.content
        return SynthesisResult(
            audio_bytes=audio_bytes,
            format="mp3",
            duration_seconds=len(audio_bytes) / (16 * 1024),  # rough estimate
        )

    async def is_available(self) -> bool:
        return await self.check_health()

    async def check_health(self) -> bool:
        if not self._client or not self.api_key:
            self._healthy = False
            return False
        try:
            # Try to list voices as a health check
            resp = await self._client.get(f"{self.base_url}/v1/voices", timeout=10.0)
            self._healthy = resp.is_success
            return self._healthy
        except Exception:
            self._healthy = False
            return False

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="addis-ai",
            provider_type="addis-ai",
            supported_languages=["am", "om", "en"],
            stt_supported=True,
            tts_supported=True,
            is_healthy=self._healthy or False,
            is_default=False,
        )

    async def list_voices(self, language: str | None = None) -> list[dict]:
        """List available voices from the catalog."""
        voices = []
        for voice_id, info in _ADDIS_VOICES.items():
            if language is None or info["language"] == language:
                voices.append({"id": voice_id, **info})
        return voices

    async def close(self):
        if self._client:
            await self._client.aclose()