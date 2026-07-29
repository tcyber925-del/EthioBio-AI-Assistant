from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import structlog

from src.voice.streaming.buffer import AudioBuffer

logger = structlog.get_logger(__name__)


@dataclass
class VoiceStreamSession:
    stream_session_id: str
    buffer: AudioBuffer = field(default_factory=lambda: AudioBuffer(max_chunks=200))
    language: str = "am"
    last_partial: str = ""
    chunk_count: int = 0
    chunks_since_transcribe: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VoiceStreamManager:
    def __init__(self, ttl_seconds: int = 300):
        self._sessions: dict[str, VoiceStreamSession] = {}
        self._ttl = ttl_seconds

    def get_or_create(self, stream_session_id: str, language: str = "am") -> VoiceStreamSession:
        existing = self._sessions.get(stream_session_id)
        now = datetime.now(timezone.utc)
        if existing:
            elapsed = (now - existing.last_activity).total_seconds()
            if elapsed < self._ttl:
                existing.last_activity = now
                return existing
            logger.info("stream_session_expired", session_id=stream_session_id, elapsed=elapsed)
        session = VoiceStreamSession(stream_session_id=stream_session_id, language=language)
        self._sessions[stream_session_id] = session
        logger.debug("stream_session_created", session_id=stream_session_id)
        return session

    def get(self, stream_session_id: str) -> Optional[VoiceStreamSession]:
        return self._sessions.get(stream_session_id)

    def remove(self, stream_session_id: str) -> None:
        self._sessions.pop(stream_session_id, None)

    def clear_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [
            k
            for k, v in self._sessions.items()
            if (now - v.last_activity).total_seconds() > self._ttl
        ]
        for k in expired:
            self._sessions.pop(k, None)
        if expired:
            logger.info("cleared_expired_stream_sessions", count=len(expired))
        return len(expired)

    @property
    def active_count(self) -> int:
        return len(self._sessions)
