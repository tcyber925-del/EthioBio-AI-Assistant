"""Azure AI Speech provider for STT and TTS.

Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in config.
STT accepts PCM WAV audio. TTS uses SSML via the REST API.
"""

from typing import Optional

import httpx
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import SpeechProviderInfo, SynthesisResult, TranscriptResult

logger = structlog.get_logger(__name__)

AZURE_STT_ENDPOINT = "https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
AZURE_TTS_ENDPOINT = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

LANGUAGE_VOICES: dict[str, str] = {
    "am": "am-ET-AmehaNeural",
    "en": "en-US-JennyNeural",
}

FALLBACK_VOICE = "en-US-JennyNeural"


class AzureSTTProvider(SpeechProvider):

    @property
    def name(self) -> str:
        return "azure"

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/wav",
    ) -> TranscriptResult:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError("Azure Speech not configured")
        lang = language or "am-ET"
        url = AZURE_STT_ENDPOINT.format(region=settings.azure_speech_region)
        headers = {
            "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
            "Content-Type": mime_type,
        }
        params = {"language": lang, "format": "detailed"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, params=params, content=audio)
        if response.status_code != 200:
            logger.error("azure_stt_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Azure STT failed: {response.status_code} {response.text}")
        result = response.json()
        duration = result.get("Duration", 0)
        dur_secs = duration / 1_000_000 if duration else 0.0
        return TranscriptResult(
            text=result.get("DisplayText", ""),
            language=lang,
            duration_seconds=dur_secs,
        )

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise RuntimeError("Azure Speech not configured")
        voice_name = voice or LANGUAGE_VOICES.get(language or "", FALLBACK_VOICE)
        lang_tag = "am-ET" if language == "am" else "en-US"
        ssml = f"""<speak version='1.0' xml:lang='{lang_tag}'>
  <voice xml:lang='{lang_tag}' name='{voice_name}'>
    {self._escape_xml(text)}
  </voice>
</speak>"""
        url = AZURE_TTS_ENDPOINT.format(region=settings.azure_speech_region)
        headers = {
            "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=ssml)
        if response.status_code != 200:
            logger.error("azure_tts_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Azure TTS failed: {response.status_code} {response.text}")
        return SynthesisResult(
            audio_bytes=response.content,
            format="mp3",
        )

    async def is_available(self) -> bool:
        return bool(settings.azure_speech_key and settings.azure_speech_region)

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="azure",
            provider_type="azure",
            supported_languages=["am-ET", "en-US"],
            stt_supported=True,
            tts_supported=True,
            is_healthy=bool(settings.azure_speech_key and settings.azure_speech_region),
        )

    @staticmethod
    def _escape_xml(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
