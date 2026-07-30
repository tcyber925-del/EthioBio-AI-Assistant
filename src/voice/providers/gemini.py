import struct
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

PCM_SAMPLE_RATE = 24000

def _pick_model(language: str | None) -> str:
    if language and language.startswith("am"):
        return "gemini-3.1-flash-tts-preview"
    return "gemini-2.5-flash-preview-tts"


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = PCM_SAMPLE_RATE) -> bytes:
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(pcm_bytes)
    header_size = 44

    header = struct.pack(
        "<4sI4s4sIHHIIHH",
        b"RIFF",
        header_size + data_size - 8,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
    )
    header += struct.pack("<4sI", b"data", data_size)
    return header + pcm_bytes


def _wrap_audio(data: bytes, mime_type: str) -> tuple[bytes, str]:
    if mime_type in ("audio/L16", "audio/pcm", "audio/L8"):
        return _pcm_to_wav(data, PCM_SAMPLE_RATE), "wav"
    if mime_type in ("audio/wav", "audio/wave"):
        return data, "wav"
    if mime_type == "audio/ogg":
        return data, "ogg"
    if mime_type == "audio/mpeg":
        return data, "mp3"
    return data, "wav"


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

        response = await client.aio.models.generate_content(
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

        candidates = response.candidates
        part = candidates[0].content.parts[0].inline_data  # type: ignore[index]
        audio_bytes, fmt = _wrap_audio(part.data, part.mime_type)
        return SynthesisResult(
            audio_bytes=audio_bytes,
            format=fmt,
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
