from .audio import (
    AUDIO_FORMATS,
    MIME_TO_EXT,
    estimate_duration,
    format_name,
    guess_mime_from_bytes,
    validate_audio_size,
)
from .gateways import BaseVoiceAdapter, TelegramTextAdapter, TelegramVoiceAdapter, WebVoiceAdapter
from .providers import (
    AzureSTTProvider,
    EdgeTTSProvider,
    GroqSTTProvider,
    SpeechProvider,
    SpeechProviderRegistry,
    SynthesisResult,
    TranscriptResult,
)
from .session import VoiceSession, VoiceSessionManager
from .streaming import AudioBuffer, AudioChunk
from .vad import VADDetector, VADState

__all__ = [
    "AUDIO_FORMATS",
    "MIME_TO_EXT",
    "estimate_duration",
    "format_name",
    "guess_mime_from_bytes",
    "validate_audio_size",
    "BaseVoiceAdapter",
    "TelegramVoiceAdapter",
    "TelegramTextAdapter",
    "WebVoiceAdapter",
    "GroqSTTProvider",
    "EdgeTTSProvider",
    "AzureSTTProvider",
    "SpeechProviderRegistry",
    "SpeechProvider",
    "TranscriptResult",
    "SynthesisResult",
    "VoiceSession",
    "VoiceSessionManager",
    "AudioBuffer",
    "AudioChunk",
    "VADDetector",
    "VADState",
]
