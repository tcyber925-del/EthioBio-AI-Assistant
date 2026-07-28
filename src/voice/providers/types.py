from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str
    language_confidence: float = 0.0
    duration_seconds: float = 0.0
    segments: Optional[list[Dict]] = None


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    format: str = "ogg"
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class SpeechProviderInfo:
    name: str
    provider_type: str
    supported_languages: list[str] = field(default_factory=list)
    stt_supported: bool = False
    tts_supported: bool = False
    is_healthy: bool = False
    is_default: bool = False
