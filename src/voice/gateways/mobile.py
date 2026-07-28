"""MobileVoiceAdapter — adapter for Expo (React Native) voice integration.

v2 contract:
  Input:  tuple[bytes, dict] — (audio_bytes, metadata dict)
          metadata keys:
            - stt_language (str, default "en")
            - topic (str, optional)
            - grade_level (int, optional)
            - socratic_mode (bool, default false)
            - hint_level (int, default 0)
            - reveal_answer (bool, default false)
            - offline_queue_id (str, optional — set when retried from offline queue)
            - device_id (str, optional)
            - audio_format (str, default "wav") — codec hint for provider dispatch

  Output: dict — structured response for mobile client:
            - answer (str)
            - session_id (str)
            - xp_awarded (int)
            - level_up (bool)
            - new_level (int)
            - language (str)
            - tts_audio_url (str, optional) — pre-signed URL for TTS playback
            - needs_offline_retry (bool) — true if gateway should requeue

  Session:  Keyed by user_id (not device_id) for cross-gateway continuity.
            Mobile client sends user_id in metadata on every request.

  Offline:  Client stores failed requests in AsyncStorage.
            On reconnect, replays them through this adapter.
            Gateway sets needs_offline_retry=false on success,
            true on transient failure.

  Streaming: Partial STT results (interim transcripts) are handled
             client-side via on-device ASR (expo-speech-recognition)
             and sent as separate text-only ConversationRequest
             with modality="text" and interim=true in metadata.
             Only final transcripts are sent as voice modality.

  Push:     TTS audio delivery uses push notification with audio URL
            when user is offline / app backgrounded.
            Gateway returns tts_audio_url when push delivery is requested
            (push_token in metadata).

v3 stretch: native WebRTC for duplex audio, local VAD on device.
"""

from __future__ import annotations

from src.schemas.conversation import ConversationRequest, ConversationResponse

from .base import BaseVoiceAdapter


class MobileVoiceAdapter(BaseVoiceAdapter[tuple[bytes, dict], dict]):
    """Adapter between Expo mobile app and ConversationService.

    Converts raw audio bytes + metadata dict to ConversationRequest
    and ConversationResponse back to a structured mobile-appropriate dict.
    """

    def build_request(self, gateway_input: tuple[bytes, dict]) -> ConversationRequest:
        _audio_bytes, meta = gateway_input
        return ConversationRequest(
            user_id=meta.get("user_id", ""),
            conversation_id="",
            session_id=meta.get("session_id", ""),
            transcript="",  # STT happens server-side from audio bytes
            language=meta.get("stt_language", "en"),
            modality="voice",
            metadata={
                "topic": meta.get("topic", ""),
                "grade_level": meta.get("grade_level", ""),
                "socratic_mode": meta.get("socratic_mode", False),
                "hint_level": meta.get("hint_level", 0),
                "reveal_answer": meta.get("reveal_answer", False),
                "audio_format": meta.get("audio_format", "wav"),
                "device_id": meta.get("device_id", ""),
                "offline_queue_id": meta.get("offline_queue_id", ""),
                "stt_provider": "registry",
                "gateway": "mobile",
            },
        )

    def extract_response(self, response_data: ConversationResponse) -> dict:
        meta = response_data.metadata or {}
        return {
            "answer": response_data.answer,
            "session_id": response_data.session_id,
            "xp_awarded": meta.get("xp_awarded", 0),
            "level_up": meta.get("level_up", False),
            "new_level": meta.get("new_level", 0),
            "language": response_data.language,
            "tts_audio_url": meta.get("tts_audio_url", ""),
            "needs_offline_retry": False,
        }
