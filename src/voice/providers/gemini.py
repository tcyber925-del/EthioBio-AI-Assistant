from typing import Optional

import structlog

from src.config import settings

from .base import SpeechProvider
from .types import SpeechProviderInfo, SynthesisResult

logger = structlog.get_logger(__name__)

LANGUAGE_VOICES: dict[str, str] = {
    "am": "Kore",
    "en": "Kore",
}

FALLBACK_VOICE = "Kore"

def _pick_model(language: str | None) -> str:
    if language and language.startswith("am"):
        return "gemini-3.1-flash-tts-preview"
    return "gemini-2.5-flash-tts"


class GeminiTTSProvider(SpeechProvider):
    @property
    def name(self) -> str:
        return "gemini-tts"

    async def transcribe(
        self, audio: bytes, language: str | None = None, mime_type: str = "audio/ogg"
    ):
        raise NotImplementedError("GeminiTTSProvider does not support STT")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        model = _pick_model(language)
        voice_name = voice or LANGUAGE_VOICES.get(language or "", FALLBACK_VOICE)

        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

        audio_bytes = response.candidates[0].content.parts[0].inline_data.data
        return SynthesisResult(
            audio_bytes=audio_bytes,
            format="ogg",
        )

    async def is_available(self) -> bool:
        return bool(settings.gemini_api_key)

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="gemini-tts",
            provider_type="google",
            supported_languages=["am", "en"],
            stt_supported=False,
            tts_supported=True,
            is_healthy=bool(settings.gemini_api_key),
        )
