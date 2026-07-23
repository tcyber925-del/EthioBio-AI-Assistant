from datetime import datetime, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    GamificationSummary,
    LearnerSnapshot,
    ReviewSummary,
)
from src.core.learning_intelligence.recommendation.models import LearningActionType
from src.core.learning_intelligence.recommendation.services import (
    RecommendationEngine,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _snapshot(**overrides) -> LearnerSnapshot:
    defaults = {
        "user_id": USER_ID,
        "generated_at": NOW,
        "mastery_by_topic": {},
        "weak_topics": [],
        "active_recovery_plans": [],
        "due_reviews": [],
        "misconceptions": [],
        "gamification": GamificationSummary(
            current_streak=5,
            recent_activity_score=0.8,
        ),
    }
    defaults.update(overrides)
    return LearnerSnapshot(**defaults)


class TestRecommendationEngine:
    async def test_empty_snapshot_returns_empty(self):
        engine = RecommendationEngine()
        result = await engine.generate(_snapshot(), USER_ID)
        assert result == []

    async def test_single_rule_fires(self):
        snap = _snapshot(
            weak_topics=["Genetics"],
            mastery_by_topic={"Genetics": {"severity": "critical"}},
        )
        engine = RecommendationEngine()
        result = await engine.generate(snap, USER_ID)
        assert len(result) >= 1
        assert result[0].action_type == LearningActionType.REVIEW_TOPIC
        assert result[0].topic == "Genetics"

    async def test_multiple_rules_combined(self):
        snap = _snapshot(
            weak_topics=["Genetics"],
            mastery_by_topic={"Genetics": {"severity": "critical"}},
            due_reviews=[
                ReviewSummary(topic="Cell Biology", next_review_at=NOW, days_overdue=5),
            ],
        )
        engine = RecommendationEngine()
        result = await engine.generate(snap, USER_ID)
        assert len(result) == 2
        topics = {r.topic for r in result}
        assert "Genetics" in topics
        assert "Cell Biology" in topics

    async def test_ids_assigned_correctly(self):
        snap = _snapshot(
            weak_topics=["Genetics"],
            mastery_by_topic={"Genetics": {"severity": "critical"}},
        )
        engine = RecommendationEngine()
        result = await engine.generate(snap, USER_ID)
        assert result[0].id == f"rec_{str(USER_ID)[:8]}_0"

    async def test_top5_limit_enforced(self):
        snap = _snapshot(
            weak_topics=[f"T{i}" for i in range(20)],
            mastery_by_topic={f"T{i}": {"severity": "critical"} for i in range(20)},
        )
        engine = RecommendationEngine()
        result = await engine.generate(snap, USER_ID)
        assert len(result) <= 5
