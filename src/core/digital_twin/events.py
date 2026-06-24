from uuid import UUID

import structlog

from src.core.digital_twin.builder import TwinBuilder
from src.core.memory.event_logger import EventLogger

logger = structlog.get_logger()

TWIN_EVENT_TYPES = [
    "assessment_completed",
    "lesson_delivered",
    "intervention_completed",
    "intervention_assigned",
    "misconception_detected",
    "misconception_resolved",
]


async def twin_event_handler(
    event_type: str,
    user_id: UUID,
    metadata: dict | None = None,
    **kwargs,
):
    if event_type not in TWIN_EVENT_TYPES:
        return
    from src.database.session import async_session_factory
    async with async_session_factory() as session:
        try:
            builder = TwinBuilder(session)
            state = await builder.rebuild(user_id)
            logger.info(
                "twin_rebuilt",
                user_id=str(user_id),
                event_type=event_type,
                health=state.get("overall_health"),
            )
        except Exception:
            logger.exception(
                "twin_rebuild_failed",
                user_id=str(user_id),
                event_type=event_type,
            )


def register_twin_subscribers(event_logger: EventLogger):
    for event_type in TWIN_EVENT_TYPES:
        event_logger.subscribe(event_type, twin_event_handler)
    logger.info("twin_subscribers_registered", count=len(TWIN_EVENT_TYPES))
