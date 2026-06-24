from collections.abc import Callable
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEvent

logger = structlog.get_logger()


class EventValidationError(ValueError):
    pass


class EventSchema:
    def __init__(
        self,
        event_type: str,
        description: str = "",
        required_fields: list[str] | None = None,
        optional_fields: list[str] | None = None,
        metadata_schema: dict[str, type | tuple[type, ...]] | None = None,
    ):
        self.event_type = event_type
        self.description = description
        self.required_fields = required_fields or []
        self.optional_fields = optional_fields or []
        self.metadata_schema = metadata_schema or {}

    def validate(self, metadata: dict | None) -> dict:
        data = metadata or {}

        for field in self.required_fields:
            if field not in data:
                raise EventValidationError(
                    f"Event '{self.event_type}' missing required field: {field}"
                )

        for key, value in data.items():
            if key in self.metadata_schema:
                expected_type = self.metadata_schema[key]
                if not isinstance(value, expected_type):
                    raise EventValidationError(
                        f"Event '{self.event_type}' field '{key}' expected "
                        f"{expected_type.__name__}, got {type(value).__name__}"
                    )

        return data


SCHEMA_REGISTRY: dict[str, EventSchema] = {
    "session_started": EventSchema(
        event_type="session_started",
        description="A tutoring session was started",
        required_fields=["tutoring_mode"],
        optional_fields=["grade_level"],
    ),
    "quiz_completed": EventSchema(
        event_type="quiz_completed",
        description="A quiz was completed",
        required_fields=["score", "total"],
        optional_fields=["topic", "time_spent"],
        metadata_schema={"score": (int, float), "total": int},
    ),
    "lesson_viewed": EventSchema(
        event_type="lesson_viewed",
        description="A lesson was viewed",
        required_fields=["lesson_id", "title"],
        optional_fields=["duration_seconds"],
        metadata_schema={"lesson_id": str},
    ),
    "recovery_task_done": EventSchema(
        event_type="recovery_task_done",
        description="A recovery task was completed",
        required_fields=["plan_id", "task_title"],
        optional_fields=["xp_awarded"],
        metadata_schema={"xp_awarded": int},
    ),
    "misconception_detected": EventSchema(
        event_type="misconception_detected",
        description="A misconception was detected in student response",
        required_fields=["topic"],
        optional_fields=["correction", "severity"],
    ),
    "misconception_resolved": EventSchema(
        event_type="misconception_resolved",
        description="A misconception was resolved",
        required_fields=["topic"],
        optional_fields=["pattern_id", "severity", "method"],
    ),
    "xp_awarded": EventSchema(
        event_type="xp_awarded",
        description="XP was awarded to a user",
        required_fields=["amount", "source"],
        optional_fields=["new_level"],
        metadata_schema={"amount": int},
    ),
    "streak_updated": EventSchema(
        event_type="streak_updated",
        description="User streak was updated",
        required_fields=["current_streak"],
        optional_fields=["longest_streak"],
        metadata_schema={"current_streak": int, "longest_streak": int},
    ),
    "achievement_unlocked": EventSchema(
        event_type="achievement_unlocked",
        description="An achievement was unlocked",
        required_fields=["achievement_id", "title"],
        metadata_schema={"achievement_id": str},
    ),
}

class EventLogger:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("subscriber_registered", event_type=event_type, handler=handler.__name__)

    def subscribe_all(self, handler: callable) -> None:
        for event_type in SCHEMA_REGISTRY:
            self.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: callable) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h is not handler
            ]

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

        try:
            validated = self._validate(event_type, metadata)
        except EventValidationError as e:
            logger.error("event_validation_failed", event_type=event_type, error=str(e))
            raise

        event = MemoryEvent(
            user_id=user_id,
            event_type=event_type,
            topic=topic,
            event_metadata=validated,
        )
        db.add(event)
        await db.flush()

        await self._notify_subscribers(event_type, user_id, validated, event.id)

        return event

    def _validate(self, event_type: str, metadata: dict | None) -> dict:
        schema = SCHEMA_REGISTRY.get(event_type)
        if schema:
            return schema.validate(metadata)
        logger.warning("unknown_event_type", event_type=event_type)
        return metadata or {}

    async def _notify_subscribers(
        self,
        event_type: str,
        user_id: UUID,
        metadata: dict,
        event_id: UUID,
    ) -> None:
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return
        for handler in handlers:
            try:
                if hasattr(handler, '__call__'):
                    result = handler(
                        event_type=event_type,
                        user_id=user_id,
                        metadata=metadata,
                        event_id=event_id,
                    )
                    if hasattr(result, '__await__'):
                        await result
            except Exception as e:
                logger.error(
                    "subscriber_error",
                    event_type=event_type,
                    handler=getattr(handler, '__name__', str(handler)),
                    error=str(e),
                )


event_logger = EventLogger()
