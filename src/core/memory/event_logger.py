from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEvent

logger = structlog.get_logger()

SCHEMA_REGISTRY: dict[str, dict[str, Any]] = {
    "session_started": {
        "required_fields": [],
        "optional_fields": ["mode", "topic"],
        "metadata_schema": {"mode": str, "topic": str},
    },
    "quiz_completed": {
        "required_fields": ["score", "total_questions"],
        "optional_fields": ["topic", "questions_attempted", "time_spent"],
        "metadata_schema": {"score": (int, float), "total_questions": int},
    },
    "lesson_viewed": {
        "required_fields": ["topic"],
        "optional_fields": ["lesson_id", "duration_seconds", "completed"],
        "metadata_schema": {"topic": str, "lesson_id": str, "duration_seconds": (int, float)},
    },
    "recovery_task_done": {
        "required_fields": ["task_id", "plan_id"],
        "optional_fields": ["topic"],
        "metadata_schema": {"task_id": str, "plan_id": str},
    },
    "misconception_detected": {
        "required_fields": ["misconception", "topic"],
        "optional_fields": ["severity", "correction"],
        "metadata_schema": {"misconception": str, "topic": str},
    },
    "xp_awarded": {
        "required_fields": ["amount", "source"],
        "optional_fields": ["new_total", "level"],
        "metadata_schema": {"amount": (int, float), "source": str},
    },
    "streak_updated": {
        "required_fields": ["current_streak", "longest_streak"],
        "optional_fields": ["streak_type"],
        "metadata_schema": {"current_streak": int, "longest_streak": int},
    },
    "achievement_unlocked": {
        "required_fields": ["achievement_id", "title"],
        "optional_fields": ["icon", "description"],
        "metadata_schema": {"achievement_id": str, "title": str},
    },
}


class EventValidationError(ValueError): ...


class EventLogger:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        for event_type in SCHEMA_REGISTRY:
            self.subscribe(event_type, handler)

    async def log(
        self,
        user_id: UUID,
        event_type: str,
        topic: str | None = None,
        metadata: dict | None = None,
        db: AsyncSession | None = None,
    ) -> MemoryEvent | None:
        if db is None:
            logger.warning("memory_event_skipped_no_db", event_type=event_type)
            return None

        meta = metadata or {}
        if event_type in SCHEMA_REGISTRY:
            self._validate(event_type, meta)

        event = MemoryEvent(
            user_id=user_id,
            event_type=event_type,
            topic=topic,
            event_metadata=meta,
        )
        db.add(event)
        await db.flush()

        await self._notify(event_type, user_id, meta, event.id)
        return event

    def _validate(self, event_type: str, metadata: dict) -> None:
        schema = SCHEMA_REGISTRY.get(event_type)
        if not schema:
            return
        for field in schema["required_fields"]:
            if field not in metadata or metadata[field] is None:
                raise EventValidationError(f"Event '{event_type}' missing required field: {field}")
        for field, raw in metadata.items():
            expected = schema["metadata_schema"].get(field)
            if expected is None:
                continue
            allowed = expected if isinstance(expected, tuple) else (expected,)
            if not isinstance(raw, allowed):
                raise EventValidationError(
                    f"Event '{event_type}' field '{field}' expected {allowed}, got {type(raw).__name__}"  # noqa: E501
                )

    async def _notify(self, event_type: str, user_id: UUID, metadata: dict, event_id: UUID) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        for handler in handlers:
            try:
                result = handler(event_type, user_id, metadata, str(event_id))
                if iscoroutinefunction(handler):
                    await result
            except Exception:
                logger.exception("subscriber_error", event_type=event_type)
