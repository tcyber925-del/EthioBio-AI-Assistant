from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.core.learning_intelligence.models import (
    GamificationSummary,
    LearnerSnapshot,
)
from src.core.learning_intelligence.recommendation.services import (
    RecommendationService,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _mock_snapshot_service(returns: LearnerSnapshot):
    svc = MagicMock()
    svc.get_snapshot = AsyncMock(return_value=returns)
    return svc


def _mock_cache(data: list[dict] | None = None):
    cache = MagicMock()
    cache.get = AsyncMock(return_value=data)
    cache.set = AsyncMock()
    return cache


class TestRecommendationService:
    async def test_cache_hit_returns_cached(self):
        cached = {
            "recommendations": [
                {
                    "id": "rec_test_0",
                    "action_type": "review_topic",
                    "topic": "Genetics",
                    "priority_score": 0.5,
                    "reason": "test",
                    "explanation": "test",
                    "generated_at": "2026-06-01T00:00:00",
                    "metadata": {},
                }
            ]
        }
        cache = _mock_cache(cached)
        svc = RecommendationService(
            snapshot_service=_mock_snapshot_service(
                LearnerSnapshot(user_id=USER_ID, generated_at=NOW),
            ),
            cache=cache,
        )
        result = await svc.get_recommendations(MagicMock(), USER_ID)
        assert len(result) == 1
        assert result[0].topic == "Genetics"
        assert result[0].action_type == "review_topic"

    async def test_cache_miss_generates_and_caches(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            weak_topics=["Genetics"],
            mastery_by_topic={"Genetics": {"severity": "critical"}},
            gamification=GamificationSummary(current_streak=5, recent_activity_score=0.8),
        )
        cache = _mock_cache(None)
        svc = RecommendationService(
            snapshot_service=_mock_snapshot_service(snap),
            cache=cache,
        )
        result = await svc.get_recommendations(MagicMock(), USER_ID)
        assert len(result) >= 1
        assert cache.set.called

    async def test_cache_miss_with_empty_snapshot(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            gamification=GamificationSummary(current_streak=5, recent_activity_score=0.8),
        )
        cache = _mock_cache(None)
        svc = RecommendationService(
            snapshot_service=_mock_snapshot_service(snap),
            cache=cache,
        )
        result = await svc.get_recommendations(MagicMock(), USER_ID)
        assert result == []
        assert cache.set.called
