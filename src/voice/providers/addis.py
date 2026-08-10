"""Addis AI voice provider (addis-whisper STT + Addis Voices 2 TTS).

Requires ADDIS_API_KEY. REST API at https://api.addisassistant.com
(see docs/research/addis-ai-voice-integration.md):
- STT: POST /api/v2/stt (multipart; 60s/10MB limits; WAV/MP3/M4A/WebM;
  language_code is REQUIRED — addis-whisper has no auto-detect)
- TTS: POST /api/v1/voice/generations -> 201 with inline data.audio
  (base64 data URL) or signed audio_url (full clips, no partial
  streaming; idempotent via client_request_id)
Addis Voices 2 voices are Amharic/Afan Oromo only; English synthesis
raises NotImplementedError so the registry falls back to other providers.
"""

import base64
import json
import re
import uuid
from typing import Optional

import httpx
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import (
    SpeechProviderInfo,
    SynthesisResult,
    TranscriptResult,
    detect_transcript_language,
    normalize_language_code,
)

logger = structlog.get_logger(__name__)

ADDIS_STT_ENDPOINT = "/api/v2/stt"
ADDIS_TTS_ENDPOINT = "/api/v1/voice/generations"

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)")

# Voices 2 supports Amharic (am) and Afan Oromo (om); English TTS falls
# back to other providers via NotImplementedError.
TTS_LANGUAGES = frozenset({"am"})


class AddisProvider(SpeechProvider):
    """Speech-to-text (addis-whisper) and text-to-speech (Addis Voices 2)."""

    @property
    def name(self) -> str:
        return "addis"

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ) -> TranscriptResult:
        if not settings.addis_api_key:
            raise RuntimeError("ADDIS_API_KEY not configured")

        # addis-whisper cannot auto-detect (verified live: omitting
        # language_code returns 400), but the "am" hint is universal-safe:
        # Amharic speech comes back in Ethiopic script, English speech
        # comes back as correct English text (verified live both ways;
        # the "en" hint romanizes Amharic, so it is never safe).
        language_code = normalize_language_code(language)
        auto_detected = language_code not in ("am", "en")
        if auto_detected:
            language_code = "am"

        request_data = {"language_code": language_code}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.addis_base_url}{ADDIS_STT_ENDPOINT}",
                headers={"x-api-key": settings.addis_api_key},
                files={"audio": ("audio.wav", audio, mime_type)},
                data={"request_data": json.dumps(request_data)},
            )

        if response.status_code != 200:
            logger.error("addis_stt_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Addis STT failed: {response.status_code} {response.text}")

        result = response.json()
        data = result.get("data") or {}
        usage = data.get("usage_metadata") or {}
        duration = _parse_billed_duration(usage.get("totalBilledDuration"))
        text = data.get("transcription", "")
        return TranscriptResult(
            text=text,
            # Explicit am/en keeps the caller-declared code; the default
            # "am" hint gets a script-sniffed tag so downstream knows the
            # actual language spoken.
            language=detect_transcript_language(text) if auto_detected else language_code,
            language_confidence=float(result.get("confidence") or 0.0),
            duration_seconds=duration,
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        if not settings.addis_api_key:
            raise RuntimeError("ADDIS_API_KEY not configured")
        if language not in TTS_LANGUAGES:
            raise NotImplementedError(
                f"Addis Voices 2 supports Amharic only ({language or 'unspecified'} requested)"
            )

        voice_id = voice or settings.addis_tts_voice_am
        body = {
            "text": text,
            "voice_id": voice_id,
            "language": language,
            "output_format": settings.addis_tts_output_format,
            "client_request_id": str(uuid.uuid4()),
        }
        headers = {"x-api-key": settings.addis_api_key}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.addis_base_url}{ADDIS_TTS_ENDPOINT}",
                headers=headers,
                json=body,
            )

        if not (200 <= response.status_code < 300):
            logger.error("addis_tts_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Addis TTS failed: {response.status_code} {response.text}")

        data = response.json().get("data") or {}
        duration = float(data.get("duration_seconds") or 0.0)

        inline = data.get("audio") or ""
        if inline.startswith("data:"):
            # Fast path: first response carries the clip inline as a
            # base64 data URL (e.g. data:audio/mpeg;base64,<...>).
            _, _, encoded = inline.partition(",")
            return SynthesisResult(
                audio_bytes=base64.b64decode(encoded),
                format="mp3",
                duration_seconds=duration,
            )

        audio_url = data.get("audio_url")
        if not audio_url:
            raise RuntimeError(f"Addis TTS returned no audio: {response.text}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            audio_response = await client.get(audio_url)
        if audio_response.status_code != 200:
            logger.error(
                "addis_tts_audio_fetch_failed",
                status=audio_response.status_code,
                url=audio_url,
            )
            raise RuntimeError(
                f"Addis TTS audio fetch failed: {audio_response.status_code}"
            )

        return SynthesisResult(
            audio_bytes=audio_response.content,
            format="mp3",
            duration_seconds=duration,
        )

    async def is_available(self) -> bool:
        return bool(settings.addis_api_key)

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="addis",
            provider_type="addis",
            supported_languages=["am", "en"],
            stt_supported=True,
            tts_supported=True,
            is_healthy=bool(settings.addis_api_key),
        )


def _parse_billed_duration(value: object) -> float:
    """Parse a billed duration string like "15s" into seconds."""
    if value is None:
        return 0.0
    match = _DURATION_RE.search(str(value))
    if not match:
        return 0.0
    return float(match.group(1))
