from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
    RecoverySummary,
    ReviewSummary,
)
from src.core.learning_intelligence.readiness.forgetting_risk import (
    ForgettingRiskPredictor,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


class TestForgettingRiskPredictor:
    def test_empty_when_no_mastery(self):
        snap = LearnerSnapshot(user_id=USER_ID, generated_at=NOW)
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert result == {}

    def test_no_review_data_no_recovery(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 85.0}},
        )
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert "Genetics" in result
        r = result["Genetics"]
        assert r.forgetting_risk <= 0.99
        assert r.forgetting_risk >= 0.01
        assert r.days_overdue == 0
        assert r.ease_factor == 2.5
        assert r.review_count == 0
        assert "no_review_data" in r.contributing_factors

    def test_no_review_data_low_mastery_higher_risk(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 30.0}},
        )
        predictor = ForgettingRiskPredictor()
        high = predictor.predict_forgetting(snap)["Genetics"].forgetting_risk

        snap2 = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 90.0}},
        )
        low = predictor.predict_forgetting(snap2)["Genetics"].forgetting_risk
        assert high > low

    def test_with_review_due_increasing_risk(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=NOW - timedelta(days=10),
                    days_overdue=10,
                ),
            ],
        )
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert result["Genetics"].days_overdue == 10
        assert "overdue_review" in result["Genetics"].contributing_factors
        assert "has_review_data" in result["Genetics"].contributing_factors

    def test_recovery_plan_reduces_no_review_risk(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 50.0}},
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
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert "has_recovery_plan" in result["Genetics"].contributing_factors

    def test_values_clamped(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 100.0}},
        )
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert 0.01 <= result["Genetics"].forgetting_risk <= 0.99

    def test_multiple_topics(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 90.0},
                "Cell Biology": {"average_score": 40.0},
            },
        )
        predictor = ForgettingRiskPredictor()
        result = predictor.predict_forgetting(snap)
        assert len(result) == 2
        assert result["Genetics"].forgetting_risk < result["Cell Biology"].forgetting_risk
