from uuid import uuid4

import structlog

from src.core.event_infrastructure.consumer import StreamConsumer
from src.core.event_infrastructure.models import PipelineEvent
from src.core.pipeline.service import PipelineOrchestrator
from src.core.storage.interface import StorageAdapter

logger = structlog.get_logger()


class PipelineStreamConsumer(StreamConsumer):
    def __init__(
        self,
        pipeline: PipelineOrchestrator,
        storage: StorageAdapter,
        redis_url: str,
        group_name: str = "pipeline-workers",
        consumer_name: str | None = None,
        stream_name: str = "knowledge:processing",
    ):
        super().__init__(
            redis_url=redis_url,
            group_name=group_name,
            consumer_name=consumer_name or f"pipeline-worker-{uuid4().hex[:8]}",
            stream_name=stream_name,
        )
        self._pipeline = pipeline
        self._storage = storage

    async def process(self, event: PipelineEvent) -> None:
        ko_id = event.ko_id
        storage_key = event.payload.get("storage_key", "")
        logger.info("pipeline_stream_event", ko_id=ko_id, storage_key=storage_key)

        file_path = await self._storage.retrieve(storage_key)
        result = await self._pipeline.run(ko_id, file_path)

        if result.success:
            logger.info("pipeline_stream_completed", ko_id=ko_id)
        else:
            logger.warning(
                "pipeline_stream_failed",
                ko_id=ko_id,
                stage=result.stage,
                error=result.error,
            )
