
import structlog
from redis.asyncio import Redis

from src.core.event_infrastructure.models import PipelineEvent

logger = structlog.get_logger()


class RedisStreamProducer:
    def __init__(self, redis_url: str, stream_name: str = "knowledge:processing"):
        self._redis_url = redis_url
        self._stream_name = stream_name
        self._redis: Redis | None = None

    async def publish(self, event: PipelineEvent) -> str:
        if self._redis is None:
            self._redis = await Redis.from_url(self._redis_url, decode_responses=True)
            logger.info("redis_connection_opened", stream=self._stream_name)

        data = event.model_dump(mode="json")
        data["occurred_at"] = event.occurred_at.isoformat()
        entry_id = await self._redis.xadd(self._stream_name, data)
        logger.info(
            "event_published",
            stream=self._stream_name,
            entry_id=entry_id,
            event_type=event.event_type,
            ko_id=event.ko_id,
        )
        return entry_id

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("redis_connection_closed", stream=self._stream_name)
