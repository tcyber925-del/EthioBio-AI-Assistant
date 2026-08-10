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

# TTS output is only supported in Amharic and English. Anything else
# (None, "", "both", unsupported codes) must be clamped before synthesis.
_DEFAULT_TTS_LANGUAGE = "en"


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


def _contains_ethiopic(text: str) -> bool:
    """True if text contains Ethiopic (Ge'ez) script characters."""
    return any(
        0x1200 <= ord(char) <= 0x137F  # Ethiopic
        or 0x1380 <= ord(char) <= 0x139F  # Ethiopic Supplement
        or 0x2D80 <= ord(char) <= 0x2DDF  # Ethiopic Extended
        or 0xAB00 <= ord(char) <= 0xAB2F  # Ethiopic Extended-A
        for char in text
    )


def detect_transcript_language(text: str) -> str:
    """Best-effort language tag from a transcript's script.

    Returns "am" when the text contains Ethiopic script, otherwise "en".
    Used to label results when a provider was given no explicit
    language (e.g. addis-whisper's universal "am" hint).
    """
    return "am" if _contains_ethiopic(text) else "en"


def resolve_tts_language(language: Optional[str], text: str = "") -> str:
    """Clamp any TTS language input to a supported code: "am" or "en".

    TTS providers must never receive None/"both"/unsupported codes —
    Gemini auto-detects the text language and would speak any language,
    while edge-tts/Azure silently fall back to English voices.

    Resolution order:
    1. Explicit am/en (incl. locale tags and Whisper full names) wins.
    2. "both"/None/""/unsupported → sniff the text's script:
       any Ethiopic character → "am", otherwise "en".
    """
    code = normalize_language_code(language)
    if code == "am" or code == "en":
        return code
    if text and _contains_ethiopic(text):
        return "am"
    return _DEFAULT_TTS_LANGUAGE


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
