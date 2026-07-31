from dataclasses import dataclass, field
from typing import Dict, Optional

# Whisper returns full language names (e.g. "english", "amharic") and
# Azure returns locale tags (e.g. "en-US", "am-ET"). Map both to the
# 2-letter codes used across the pipeline (LanguageEnum: en/am/both).
_WHISPER_LANGUAGE_NAMES: dict[str, str] = {
    "english": "en",
    "amharic": "am",
    "both": "both",
}

_KNOWN_CODES = frozenset({"en", "am", "both"})


def normalize_language_code(language: Optional[str]) -> Optional[str]:
    """Normalize a provider-reported language to an en/am/both code.

    Returns None when no usable code can be derived, letting callers fall
    back to their own default (usually "en").
    """
    if not language:
        return None
    code = language.strip().lower()
    if code in _KNOWN_CODES:
        return code
    base = code.split("-")[0].split("_")[0]
    if base in _KNOWN_CODES:
        return base
    return _WHISPER_LANGUAGE_NAMES.get(code)


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
