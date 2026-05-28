from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEvent

logger = structlog.get_logger()


class EventLogger:
    async def log(
        self, user_id: UUID, event_type: str,
        topic: str | None = None, metadata: dict | None = None,
        db: AsyncSession | None = None,
    ) -> MemoryEvent | None:
        if db is None:
            logger.warning("memory_event_skipped_no_db", event_type=event_type)
            return None

        event = MemoryEvent(
            user_id=user_id,
            event_type=event_type,
            topic=topic,
            event_metadata=metadata or {},
        )
        db.add(event)
        await db.flush()
        return event
