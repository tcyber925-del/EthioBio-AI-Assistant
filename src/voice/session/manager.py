from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class VoiceSession:
    session_id: UUID = field(default_factory=uuid4)
    user_id: Optional[int] = None
    topic: Optional[str] = None
    source_language: str = "am"
    target_language: str = "en"
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turn_count: int = 0
    last_provider: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class VoiceSessionManager:
    def __init__(self, ttl_seconds: int = 600):
        self._sessions: dict[str, VoiceSession] = {}
        self._ttl = ttl_seconds

    def get_or_create(self, key: str, user_id: Optional[int] = None) -> VoiceSession:
        existing = self._sessions.get(key)
        now = datetime.now(timezone.utc)
        if existing:
            elapsed = (now - existing.last_activity).total_seconds()
            if elapsed < self._ttl:
                existing.last_activity = now
                return existing
            logger.info("voice_session_expired", key=key, elapsed=elapsed)
        session = VoiceSession(user_id=user_id)
        self._sessions[key] = session
        logger.debug("voice_session_created", key=key, session_id=str(session.session_id))
        return session

    def get(self, key: str) -> Optional[VoiceSession]:
        return self._sessions.get(key)

    def touch(self, key: str) -> None:
        session = self._sessions.get(key)
        if session:
            session.last_activity = datetime.now(timezone.utc)
            session.turn_count += 1

    def remove(self, key: str) -> None:
        self._sessions.pop(key, None)

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
            logger.info("cleared_expired_voice_sessions", count=len(expired))
        return len(expired)

    @property
    def active_count(self) -> int:
        return len(self._sessions)
