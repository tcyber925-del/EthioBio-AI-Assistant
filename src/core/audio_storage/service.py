import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.models import AudioRecording
from src.observability.voice_metrics import record_recording_cleanup, record_recording_created

logger = structlog.get_logger(__name__)


class AudioStorageService:
    """Persists audio recordings to the filesystem and records metadata in the DB.

    Retention is enforced via ``expires_at`` — records older than
    ``settings.audio_retention_days`` are considered expired.
    """

    def __init__(self, base_path: Optional[str] = None):
        self._base_path = Path(base_path or settings.audio_storage_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        audio_bytes: bytes,
        transcript: str,
        session: AsyncSession,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        language: str = "am",
        mime_type: str = "audio/ogg",
        duration_seconds: float = 0.0,
        direction: str = "user",
        modality: str = "voice",
    ) -> AudioRecording:
        record_id = uuid.uuid4()
        file_name = f"{record_id}.{_ext_from_mime(mime_type)}"
        user_dir = self._user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / file_name

        file_path.write_bytes(audio_bytes)

        retention = settings.audio_retention_days
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=retention) if retention > 0 else None
        )

        recording = AudioRecording(
            id=record_id,
            user_id=uuid.UUID(user_id) if user_id else None,
            session_id=uuid.UUID(session_id) if session_id else None,
            storage_path=str(file_path.relative_to(self._base_path)),
            transcript=transcript,
            duration_seconds=duration_seconds,
            mime_type=mime_type,
            file_size_bytes=len(audio_bytes),
            language=language,
            direction=direction,
            modality=modality,
            expires_at=expires_at,
        )
        session.add(recording)
        record_recording_created(direction, modality)
        return recording

    async def get_by_user(
        self,
        user_id: str,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[AudioRecording]:
        result = await session.execute(
            select(AudioRecording)
            .where(AudioRecording.user_id == uuid.UUID(user_id))
            .order_by(AudioRecording.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_session(
        self,
        session_id: str,
        session: AsyncSession,
    ) -> list[AudioRecording]:
        result = await session.execute(
            select(AudioRecording)
            .where(AudioRecording.session_id == uuid.UUID(session_id))
            .order_by(AudioRecording.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_audio_path(self, recording: AudioRecording) -> Path:
        return self._base_path / recording.storage_path

    async def cleanup_expired(self, session: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(AudioRecording).where(AudioRecording.expires_at < now)
        )
        recordings = list(result.scalars().all())
        count = 0
        for rec in recordings:
            path = self._base_path / rec.storage_path
            if path.exists():
                path.unlink()
            await session.delete(rec)
            count += 1
        if count:
            logger.info("audio_cleanup_expired", count=count)
            record_recording_cleanup(count)
        return count

    def _user_dir(self, user_id: Optional[str]) -> Path:
        return self._base_path / (user_id or "anonymous")

    def full_path(self, recording: AudioRecording) -> Path:
        return self._base_path / recording.storage_path


def _ext_from_mime(mime_type: str) -> str:
    return {"audio/ogg": "ogg", "audio/mp3": "mp3", "audio/wav": "wav", "audio/mpeg": "mp3"}.get(
        mime_type, "ogg"
    )
