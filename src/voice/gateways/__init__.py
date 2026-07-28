from .base import BaseVoiceAdapter
from .mobile import MobileVoiceAdapter
from .telegram import TelegramTextAdapter, TelegramVoiceAdapter
from .web import WebVoiceAdapter

__all__ = [
    "BaseVoiceAdapter",
    "MobileVoiceAdapter",
    "TelegramTextAdapter",
    "TelegramVoiceAdapter",
    "WebVoiceAdapter",
]
