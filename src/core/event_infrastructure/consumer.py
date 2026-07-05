import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime

import structlog
from redis.asyncio import Redis

from src.core.event_infrastructure.models import PipelineEvent

logger = structlog.get_logger()


class StreamConsumer(ABC):
    def __init__(
        self,
        redis_url: str,
        group_name: str,
        consumer_name: str,
        stream_name: str = "knowledge:processing",
        max_retries: int = 3,
        dead_letter_stream: str = "knowledge:dead-letter",
    ):
        self._redis_url = redis_url
        self._group_name = group_name
        self._consumer_name = consumer_name
        self._stream_name = stream_name
        self._max_retries = max_retries
        self._dead_letter_stream = dead_letter_stream
        self._redis: Redis | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._redis = await Redis.from_url(self._redis_url, decode_responses=True)
        try:
            await self._redis.xgroup_create(
                self._stream_name, self._group_name, id="0", mkstream=True
            )
            logger.info(
                "consumer_group_created",
                stream=self._stream_name,
                group=self._group_name,
            )
        except Exception:
            logger.info(
                "consumer_group_exists",
                stream=self._stream_name,
                group=self._group_name,
            )

        logger.info(
            "consumer_started",
            stream=self._stream_name,
            group=self._group_name,
            consumer=self._consumer_name,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        logger.info(
            "consumer_stopping",
            stream=self._stream_name,
            consumer=self._consumer_name,
        )

    @abstractmethod
    async def process(self, event: PipelineEvent) -> None:
        ...

    async def run_forever(self) -> None:
        if self._redis is None:
            raise RuntimeError("Consumer not started. Call start() first.")

        await self._process_pending()

        while not self._stop_event.is_set():
            try:
                results = await self._redis.xreadgroup(
                    group=self._group_name,
                    consumer=self._consumer_name,
                    streams={self._stream_name: ">"},
                    count=10,
                    block=5000,
                )

                if not results:
                    continue

                for _, messages in results:
                    for msg_id, msg_data in messages:
                        await self._handle_message(msg_id, msg_data)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(
                    "consumer_loop_error",
                    stream=self._stream_name,
                    consumer=self._consumer_name,
                )

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        logger.info(
            "consumer_stopped",
            stream=self._stream_name,
            consumer=self._consumer_name,
        )

    @property
    def _r(self) -> Redis:
        assert self._redis is not None
        return self._redis

    async def _process_pending(self) -> None:
        pending = await self._r.xpending_range(
            self._stream_name, self._group_name, min="-", max="+", count=100
        )
        for entry in pending:
            entry_id = entry["message_id"]
            delivery_count = entry["times_delivered"]
            if delivery_count >= self._max_retries:
                await self._move_to_dead_letter(entry_id, None)
            else:
                try:
                    raw = await self._r.xrange(self._stream_name, min=entry_id, max=entry_id, count=1)
                    msg_data = raw[0][1] if raw else {}
                    await self._handle_message(entry_id, msg_data)
                except Exception:
                    logger.exception(
                        "pending_message_failed",
                        entry_id=entry_id,
                        delivery_count=delivery_count,
                    )

    async def _handle_message(self, msg_id: str, msg_data: dict) -> None:
        try:
            event = self._deserialize_event(msg_data)
            await self.process(event)
            await self._r.xack(self._stream_name, self._group_name, msg_id)
            logger.info(
                "event_processed",
                entry_id=msg_id,
                event_type=event.event_type,
                ko_id=event.ko_id,
            )
        except Exception:
            logger.exception(
                "event_processing_failed",
                entry_id=msg_id,
                consumer=self._consumer_name,
            )
            await self._handle_failure(msg_id, msg_data)

    async def _handle_failure(self, msg_id: str, msg_data: dict) -> None:
        pending_info = await self._r.xpending_range(
            self._stream_name, self._group_name, min=msg_id, max=msg_id, count=1
        )
        delivery_count = 1
        if pending_info and pending_info[0]["message_id"] == msg_id:
            delivery_count = pending_info[0]["times_delivered"]

        if delivery_count >= self._max_retries:
            await self._move_to_dead_letter(msg_id, msg_data)
        else:
            logger.warning(
                "event_queued_for_retry",
                entry_id=msg_id,
                delivery_count=delivery_count,
                max_retries=self._max_retries,
            )

    async def _move_to_dead_letter(self, msg_id: str, msg_data: dict | None) -> None:
        dead_data = {
            "original_stream": self._stream_name,
            "original_message_id": msg_id,
            "consumer_group": self._group_name,
            "consumer": self._consumer_name,
        }
        if msg_data:
            dead_data["payload"] = json.dumps(msg_data)
        await self._r.xadd(self._dead_letter_stream, dead_data)
        await self._r.xack(self._stream_name, self._group_name, msg_id)
        logger.warning(
            "event_moved_to_dead_letter",
            original_entry_id=msg_id,
            dead_letter_stream=self._dead_letter_stream,
        )

    def _deserialize_event(self, msg_data: dict) -> PipelineEvent:
        raw = dict(msg_data)
        occurred_at_str = raw.pop("occurred_at", None)
        if occurred_at_str:
            raw["occurred_at"] = datetime.fromisoformat(occurred_at_str)
        return PipelineEvent(**raw)
