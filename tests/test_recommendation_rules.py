from datetime import datetime, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    GamificationSummary,
    LearnerSnapshot,
    MisconceptionSummary,
    RecoverySummary,
    ReviewSummary,
)
from src.core.learning_intelligence.recommendation.models import LearningActionType
from src.core.learning_intelligence.recommendation.rules import (
    generate_engagement_recommendations,
    generate_mastery_recommendations,
    generate_misconception_recommendations,
    generate_recovery_recommendations,
    generate_review_recommendations,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _snapshot(**overrides) -> LearnerSnapshot:
    defaults = dict(
        user_id=USER_ID,
        generated_at=NOW,
        mastery_by_topic={},
        weak_topics=[],
        active_recovery_plans=[],
        due_reviews=[],
        misconceptions=[],
        gamification=GamificationSummary(),
    )
    defaults.update(overrides)
    return LearnerSnapshot(**defaults)


class TestMasteryRules:
    async def test_critical_topic_gets_40(self):
        snap = _snapshot(
            mastery_by_topic={"Genetics": {"severity": "critical"}},
            weak_topics=["Genetics"],
        )
        recs = await generate_mastery_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 40.0
        assert recs[0].action_type == LearningActionType.REVIEW_TOPIC
        assert recs[0].topic == "Genetics"

    async def test_moderate_topic_gets_25(self):
        snap = _snapshot(
            mastery_by_topic={"Cell Biology": {"severity": "moderate"}},
            weak_topics=["Cell Biology"],
        )
        recs = await generate_mastery_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 25.0
        assert "moderate" in recs[0].reason.lower()

    async def test_multiple_weak_topics(self):
        snap = _snapshot(
            mastery_by_topic={
                "Genetics": {"severity": "critical"},
                "Cell Biology": {"severity": "moderate"},
            },
            weak_topics=["Genetics", "Cell Biology"],
        )
        recs = await generate_mastery_recommendations(snap)
        assert len(recs) == 2

    async def test_no_weak_topics_returns_empty(self):
        recs = await generate_mastery_recommendations(_snapshot())
        assert recs == []


class TestRecoveryRules:
    async def test_active_plan_gets_15(self):
        snap = _snapshot(
            active_recovery_plans=[
                RecoverySummary(
                    topic="Genetics",
                    progress_pct=50.0,
                    completed_tasks=2,
                    total_tasks=4,
                    status="active",
                ),
            ],
        )
        recs = await generate_recovery_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 15.0
        assert recs[0].action_type == LearningActionType.COMPLETE_RECOVERY_TASK

    async def test_near_completion_bonus_25(self):
        snap = _snapshot(
            active_recovery_plans=[
                RecoverySummary(
                    topic="Genetics",
                    progress_pct=80.0,
                    completed_tasks=4,
                    total_tasks=5,
                    status="active",
                ),
            ],
        )
        recs = await generate_recovery_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 25.0

    async def test_no_plans_returns_empty(self):
        recs = await generate_recovery_recommendations(_snapshot())
        assert recs == []


class TestReviewRules:
    async def test_overdue_1_3_days_gets_10(self):
        snap = _snapshot(
            due_reviews=[ReviewSummary(topic="Genetics", next_review_at=NOW, days_overdue=2)],
        )
        recs = await generate_review_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 10.0
        assert recs[0].action_type == LearningActionType.REVIEW_TOPIC

    async def test_overdue_4_7_days_gets_20(self):
        snap = _snapshot(
            due_reviews=[ReviewSummary(topic="Genetics", next_review_at=NOW, days_overdue=5)],
        )
        recs = await generate_review_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 20.0

    async def test_overdue_8plus_days_gets_30(self):
        snap = _snapshot(
            due_reviews=[ReviewSummary(topic="Genetics", next_review_at=NOW, days_overdue=10)],
        )
        recs = await generate_review_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 30.0

    async def test_no_due_reviews_returns_empty(self):
        recs = await generate_review_recommendations(_snapshot())
        assert recs == []


class TestMisconceptionRules:
    async def test_frequent_misconception_gets_20(self):
        snap = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="confusion", frequency=3),
            ],
        )
        recs = await generate_misconception_recommendations(snap)
        assert len(recs) == 1
        assert recs[0].priority_score == 20.0
        assert recs[0].action_type == LearningActionType.REVISE_MISCONCEPTION

    async def test_low_frequency_skipped(self):
        snap = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="confusion", frequency=1),
            ],
        )
        recs = await generate_misconception_recommendations(snap)
        assert recs == []

    async def test_no_misconceptions_returns_empty(self):
        recs = await generate_misconception_recommendations(_snapshot())
        assert recs == []


class TestEngagementRules:
    async def test_streak_at_risk_gets_10(self):
        snap = _snapshot(gamification=GamificationSummary(current_streak=0))
        recs = await generate_engagement_recommendations(snap)
        scores = [
            r.priority_score for r in recs if r.action_type == LearningActionType.MAINTAIN_STREAK
        ]
        assert 10.0 in scores

    async def test_low_activity_gets_15(self):
        snap = _snapshot(
            gamification=GamificationSummary(current_streak=5, recent_activity_score=0.2),
        )
        recs = await generate_engagement_recommendations(snap)
        scores = [
            r.priority_score for r in recs if r.action_type == LearningActionType.MAINTAIN_STREAK
        ]
        assert 15.0 in scores

    async def test_healthy_learner_returns_empty(self):
        snap = _snapshot(
            gamification=GamificationSummary(current_streak=7, recent_activity_score=0.8),
        )
        recs = await generate_engagement_recommendations(snap)
        assert recs == []
