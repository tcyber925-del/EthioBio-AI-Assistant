import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.core.event_infrastructure.models import PipelineEvent
from src.core.event_infrastructure.producer import RedisStreamProducer
from src.core.event_infrastructure.consumer import StreamConsumer


class TestEventInfrastructure:
    @pytest.mark.asyncio
    @patch("src.core.event_infrastructure.producer.Redis")
    async def test_producer_publish(self, mock_redis_class):
        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "12345-0"
        mock_redis_class.from_url = AsyncMock(return_value=mock_redis)

        producer = RedisStreamProducer(redis_url="redis://localhost:6379", stream_name="test:stream")
        event = PipelineEvent(
            ko_id="ko-uuid-123",
            event_type="KnowledgeRegistered",
            workspace_id="ws-uuid-1",
            occurred_at=datetime.now(timezone.utc),
            payload={"test": "payload"},
            correlation_id="corr-1",
        )

        entry_id = await producer.publish(event)
        assert entry_id == "12345-0"

        # Verify Redis interaction
        mock_redis.xadd.assert_called_once()
        args, kwargs = mock_redis.xadd.call_args
        assert args[0] == "test:stream"
        assert args[1]["ko_id"] == "ko-uuid-123"
        assert args[1]["event_type"] == "KnowledgeRegistered"

        await producer.close()
        mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.core.event_infrastructure.consumer.Redis")
    async def test_consumer_loop(self, mock_redis_class):
        mock_redis = AsyncMock()
        mock_redis_class.from_url = AsyncMock(return_value=mock_redis)

        # Mock xreadgroup to return one message then stop
        mock_redis.xreadgroup.side_effect = [
            [
                (
                    "test:stream",
                    [
                        (
                            "12345-0",
                            {
                                "ko_id": "ko-uuid-123",
                                "event_type": "KnowledgeRegistered",
                                "workspace_id": "ws-uuid-1",
                                "occurred_at": "2026-07-03T18:00:00+00:00",
                                "payload": {"test": "payload"},
                                "correlation_id": "corr-1",
                            },
                        )
                    ],
                )
            ],
            None,  # trigger empty block continue
        ]

        # Concrete implementation of StreamConsumer
        class TestConsumer(StreamConsumer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.processed_events = []

            async def process(self, event: PipelineEvent) -> None:
                self.processed_events.append(event)
                # Stop consumer after processing first message
                await self.stop()

        consumer = TestConsumer(
            redis_url="redis://localhost:6379",
            group_name="test_group",
            consumer_name="test_consumer",
            stream_name="test:stream",
        )

        await consumer.start()
        # Verify consumer group creation attempt
        mock_redis.xgroup_create.assert_called_once_with(
            "test:stream", "test_group", id="0", mkstream=True
        )

        # Run consumer in a task
        task = asyncio.create_task(consumer.run_forever())
        await asyncio.sleep(0.1)  # allow loop iteration
        await task

        assert len(consumer.processed_events) == 1
        assert consumer.processed_events[0].ko_id == "ko-uuid-123"
        assert consumer.processed_events[0].event_type == "KnowledgeRegistered"

        # Verify xack acknowledgment was called
        mock_redis.xack.assert_called_once_with("test:stream", "test_group", "12345-0")
