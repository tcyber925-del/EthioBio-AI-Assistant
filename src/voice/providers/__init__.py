from .addis import AddisProvider
from .azure import AzureSTTProvider
from .base import SpeechProvider
from .edge_tts import EdgeTTSProvider
from .groq import GroqSTTProvider
from .registry import SpeechProviderRegistry
from .types import SpeechProviderInfo, SynthesisResult, TranscriptResult

speech_registry = SpeechProviderRegistry()

__all__ = [
    "AddisProvider",
    "AzureSTTProvider",
    "EdgeTTSProvider",
    "GroqSTTProvider",
    "SpeechProvider",
    "SpeechProviderInfo",
    "SpeechProviderRegistry",
    "SynthesisResult",
    "TranscriptResult",
    "speech_registry",
]
