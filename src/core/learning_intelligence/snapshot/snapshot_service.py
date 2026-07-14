from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.snapshot.cache_manager import CacheManager
from src.core.learning_intelligence.snapshot.snapshot_builder import SnapshotBuilder

logger = structlog.get_logger()

CACHE_HIT = "snapshot_cache_hit"
CACHE_MISS = "snapshot_cache_miss"
GENERATION_STARTED = "snapshot_generation_started"
GENERATION_COMPLETED = "snapshot_generation_completed"
GENERATION_FAILED = "snapshot_generation_failed"


class SnapshotService:
    def __init__(
        self,
        builder: SnapshotBuilder | None = None,
        cache: CacheManager | None = None,
    ):
        self._builder = builder or SnapshotBuilder()
        self._cache = cache or CacheManager()

    async def get_snapshot(
        self,
        session: AsyncSession,
        user_id: str | UUID,
    ) -> LearnerSnapshot:
        user_id_str = str(user_id)
        cached = await self._cache.get(user_id_str)
        if cached is not None:
            logger.info(CACHE_HIT, user_id=user_id)
            return LearnerSnapshot(**cached)

        logger.info(CACHE_MISS, user_id=user_id)
        logger.info(GENERATION_STARTED, user_id=user_id)

        snapshot = await self._builder.build(session, user_id)

        await self._cache.set(
            user_id_str,
            snapshot.model_dump(mode="json"),
        )

        logger.info(GENERATION_COMPLETED, user_id=user_id, degraded=snapshot.degraded)
        return snapshot
