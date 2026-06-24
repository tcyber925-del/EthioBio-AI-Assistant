from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.summarizer import Summarizer
from src.database.models import MemorySession

logger = structlog.get_logger()

SESSION_INACTIVITY_TIMEOUT_MINUTES = 30


class SessionManager:
    async def get_or_create_active_session(
        self, user_id: UUID, topic: str | None = None,
        tutoring_mode: str = "direct", db: AsyncSession | None = None,
    ) -> MemorySession:
        if db is None:
            raise ValueError("Database session required")

        active = await self._find_active_session(user_id, db)
        if active:
            active.last_active_at = datetime.now(timezone.utc)
            if topic and not active.active_topic:
                active.active_topic = topic
            await db.flush()
            return active

        await self._close_expired_sessions(user_id, db)

        session = MemorySession(
            user_id=user_id,
            active_topic=topic,
            tutoring_mode=tutoring_mode,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)

        logger.info("memory_session_created",
                     user_id=str(user_id), session_id=str(session.session_id))
        return session

    async def _close_expired_sessions(self, user_id: UUID, db: AsyncSession) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_INACTIVITY_TIMEOUT_MINUTES)
        result = await db.execute(
            select(MemorySession)
            .where(
                MemorySession.user_id == user_id,
                MemorySession.last_active_at < cutoff,
                MemorySession.summary.is_(None),
            )
        )
        expired = result.scalars().all()
        for session in expired:
            await self.close_session(session.session_id, db)

    async def heartbeat(self, session_id: UUID, db: AsyncSession) -> MemorySession | None:
        session = await db.get(MemorySession, session_id)
        if session:
            session.last_active_at = datetime.now(timezone.utc)
            await db.flush()
        return session

    async def close_session(
        self, session_id: UUID, db: AsyncSession,
        conversation_context: str | None = None,
    ) -> MemorySession | None:
        session = await db.get(MemorySession, session_id)
        if not session:
            return None

        summarizer = Summarizer()
        summary = await summarizer.summarize_session(
            session, conversation_context=conversation_context, db=db,
        )
        if not summary and session.summary is None:
            session.summary = ""
        await db.flush()
        logger.info("memory_session_closed", session_id=str(session_id))
        return session

    def get_messages(self, session: MemorySession) -> list[dict]:
        ctx = session.educational_context
        if not isinstance(ctx, dict):
            return []
        messages = ctx.get("messages")
        if isinstance(messages, list):
            return messages
        recent = ctx.get("recent_turns")
        if isinstance(recent, list):
            return recent
        return []

    def set_messages(self, session: MemorySession, messages: list[dict]) -> None:
        if not isinstance(session.educational_context, dict):
            session.educational_context = {}
        session.educational_context["messages"] = messages

    async def get_active_session_for_user(
        self, user_id: UUID, db: AsyncSession,
    ) -> MemorySession | None:
        return await self._find_active_session(user_id, db)

    async def _find_active_session(self, user_id: UUID, db: AsyncSession) -> MemorySession | None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_INACTIVITY_TIMEOUT_MINUTES)
        result = await db.execute(
            select(MemorySession)
            .where(
                MemorySession.user_id == user_id,
                MemorySession.last_active_at >= cutoff,
                MemorySession.summary.is_(None),
            )
            .order_by(MemorySession.last_active_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
