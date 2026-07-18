from uuid import UUID, uuid4

import structlog

from src.core.digital_twin.builder import TwinBuilder
from src.core.event_infrastructure.consumer import StreamConsumer
from src.core.event_infrastructure.models import PipelineEvent
from src.database.session import async_session_factory

logger = structlog.get_logger()


class DigitalTwinEventConsumer(StreamConsumer):
    def __init__(
        self,
        redis_url: str,
        group_name: str = "digital-twin-workers",
        consumer_name: str | None = None,
        stream_name: str = "education:events",
    ):
        super().__init__(
            redis_url=redis_url,
            group_name=group_name,
            consumer_name=consumer_name or f"digital-twin-worker-{uuid4().hex[:8]}",
            stream_name=stream_name,
        )

    async def process(self, event: PipelineEvent) -> None:
        # Assuming the payload contains 'user_id' for educational events
        user_id_str = event.payload.get("user_id")

        # If user_id isn't in payload, we might fallback to checking ko_id if it's a user event
        if not user_id_str:
            user_id_str = event.ko_id

        try:
            user_id = UUID(str(user_id_str))
        except (ValueError, TypeError):
            logger.warning(
                "digital_twin_invalid_user_id",
                event_type=event.event_type,
                user_id_str=user_id_str,
            )
            return

        logger.info(
            "digital_twin_rebuild_triggered",
            user_id=str(user_id),
            event_type=event.event_type,
        )

        factory = async_session_factory()
        async with factory() as session:
            builder = TwinBuilder(session)
            await builder.rebuild(user_id)
            await session.commit()

        logger.info(
            "digital_twin_rebuild_completed",
            user_id=str(user_id),
        )
