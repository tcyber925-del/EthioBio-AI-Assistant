from abc import ABC, abstractmethod
from typing import Optional

from .types import SpeechProviderInfo, SynthesisResult, TranscriptResult


class SpeechProvider(ABC):

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ) -> TranscriptResult:
        ...

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        raise NotImplementedError(f"{self.name} does not support TTS")

    @abstractmethod
    async def is_available(self) -> bool:
        ...

    async def check_health(self) -> bool:
        try:
            return await self.is_available()
        except Exception:
            return False

    @abstractmethod
    def get_info(self) -> SpeechProviderInfo:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
