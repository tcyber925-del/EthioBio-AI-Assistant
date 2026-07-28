from __future__ import annotations

from typing import Any

from telegram.ext import ContextTypes

from src.schemas.conversation import ConversationRequest, ConversationResponse

from .base import BaseVoiceAdapter

VOICE_SESSION_KEY = "voice_session_id"


class TelegramTextAdapter(BaseVoiceAdapter[str, str]):
    """Adapter for Telegram text queries (/ask command).

    Input: raw question string from the user
    Output: raw answer text (gateway formats it with i18n/keyboards)
    """

    def __init__(self, context: ContextTypes.DEFAULT_TYPE):
        self._context = context
        self._ud = context.user_data

    def build_request(self, question: str) -> ConversationRequest:
        metadata = self._build_metadata()
        return ConversationRequest(
            user_id="",
            conversation_id="",
            session_id=self._ud.get(VOICE_SESSION_KEY, ""),
            transcript=question,
            language=self._ud.get("language", "en"),
            modality="text",
            metadata=metadata,
        )

    def extract_response(self, response_data: ConversationResponse) -> str:
        self._ud[VOICE_SESSION_KEY] = response_data.session_id
        return response_data.answer

    def _build_metadata(self) -> dict[str, Any]:
        return {
            "topic": self._ud.get("tutor_grade") or self._ud.get("grade_level"),
            "grade_level": self._ud.get("grade_level"),
            "socratic_mode": self._ud.get("socratic_mode", False),
            "hint_level": self._ud.get("hint_level", 0),
            "reveal_answer": self._ud.get("reveal_answer", False),
        }


class TelegramVoiceAdapter(BaseVoiceAdapter[tuple[bytes, str], str]):
    """Adapter for Telegram voice messages.

    Input: (audio_bytes, transcript_text) tuple
    Output: raw answer text (gateway formats with i18n/keyboards)
    """

    def __init__(self, context: ContextTypes.DEFAULT_TYPE, language: str):
        self._context = context
        self._ud = context.user_data
        self._language = language

    def build_request(self, gateway_input: tuple[bytes, str]) -> ConversationRequest:
        _audio_bytes, transcript_text = gateway_input
        metadata = self._build_metadata(transcript_language=self._language)
        return ConversationRequest(
            user_id="",
            conversation_id="",
            session_id=self._ud.get(VOICE_SESSION_KEY, ""),
            transcript=transcript_text,
            language=self._language,
            modality="voice",
            metadata=metadata,
        )

    def extract_response(self, response_data: ConversationResponse) -> str:
        self._ud[VOICE_SESSION_KEY] = response_data.session_id
        return response_data.answer

    def _build_metadata(self, transcript_language: str) -> dict[str, Any]:
        return {
            "grade_level": self._ud.get("grade_level") or self._ud.get("tutor_grade"),
            "topic": self._ud.get("topic"),
            "socratic_mode": self._ud.get("socratic_mode", False),
            "hint_level": self._ud.get("hint_level", 0),
            "reveal_answer": self._ud.get("reveal_answer", False),
            "stt_language": transcript_language,
            "stt_provider": "registry",
        }
