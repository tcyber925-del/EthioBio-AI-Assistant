from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.readiness import ReadinessService
from src.core.learning_intelligence.recommendation.models import (
    LearningRecommendation,
)
from src.core.learning_intelligence.recommendation.services.engine import (
    RecommendationEngine,
)
from src.core.learning_intelligence.snapshot.cache_manager import CacheManager
from src.core.learning_intelligence.snapshot.snapshot_service import (
    SnapshotService,
)

logger = structlog.get_logger()

CACHE_HIT = "recommendation_cache_hit"
CACHE_MISS = "recommendation_cache_miss"


class RecommendationService:
    CACHE_KEY_PREFIX = "recommendations:"

    def __init__(
        self,
        snapshot_service: SnapshotService | None = None,
        engine: RecommendationEngine | None = None,
        cache: CacheManager | None = None,
        readiness_service: ReadinessService | None = None,
    ):
        self._snapshot_service = snapshot_service or SnapshotService()
        self._engine = engine or RecommendationEngine()
        self._cache = cache or CacheManager()
        self._cache.KEY_PREFIX = "recommendations:"
        self._readiness_service = readiness_service or ReadinessService()

    async def get_recommendations(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> list[LearningRecommendation]:
        user_id_str = str(user_id)
        cached = await self._cache.get(user_id_str)
        if cached is not None:
            logger.info(CACHE_HIT, user_id=user_id)
            raw_list = cached.get("recommendations", [])
            return [LearningRecommendation(**r) for r in raw_list]

        logger.info(CACHE_MISS, user_id=user_id)
        snapshot = await self._snapshot_service.get_snapshot(session, user_id)

        readiness_profile = None
        try:
            readiness_profile = await self._readiness_service.get_readiness(
                session,
                user_id,
            )
        except Exception:
            logger.warning("readiness_fetch_failed", user_id=user_id)

        recommendations = await self._engine.generate(
            snapshot,
            user_id,
            readiness_profile=readiness_profile,
            session=session,
        )

        await self._cache.set(
            user_id_str,
            {"recommendations": [r.model_dump(mode="json") for r in recommendations]},
        )

        return recommendations
