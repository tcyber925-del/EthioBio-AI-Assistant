from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
    RecoverySummary,
    ReviewSummary,
)
from src.core.learning_intelligence.readiness.mastery_stability import (
    MasteryStabilityPredictor,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


class TestMasteryStabilityPredictor:
    def test_empty_when_no_mastery(self):
        snap = LearnerSnapshot(user_id=USER_ID, generated_at=NOW)
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert result == {}

    def test_high_mastery_high_stability(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 95.0}},
            ability_by_topic={"Genetics": {"ability_score": 1.5, "uncertainty": 0.5}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=NOW - timedelta(days=3),
                    days_overdue=3,
                ),
            ],
            active_recovery_plans=[
                RecoverySummary(
                    topic="Genetics",
                    progress_pct=100.0,
                    completed_tasks=5,
                    total_tasks=5,
                    status="active",
                ),
            ],
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert result["Genetics"].stability_band == "Stable"

    def test_low_mastery_volatile(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 20.0}},
            ability_by_topic={"Genetics": {"ability_score": -1.0, "uncertainty": 3.0}},
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert result["Genetics"].stability_band == "Volatile"

    def test_moderate_stability_band(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 65.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.0, "uncertainty": 1.5}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=NOW - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert result["Genetics"].stability_band == "Moderate"

    def test_review_history_boosts_stability(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 60.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.5, "uncertainty": 1.0}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=NOW - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
        )
        predictor = MasteryStabilityPredictor()
        with_review = predictor.predict_stability(snap)["Genetics"].stability_score

        snap2 = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 60.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.5, "uncertainty": 1.0}},
        )
        without = predictor.predict_stability(snap2)["Genetics"].stability_score
        assert with_review >= without

    def test_recovery_progress_boosts_stability(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 50.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.0, "uncertainty": 2.0}},
            active_recovery_plans=[
                RecoverySummary(
                    topic="Genetics",
                    progress_pct=100.0,
                    completed_tasks=5,
                    total_tasks=5,
                    status="active",
                ),
            ],
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert result["Genetics"].stability_score > 0

    def test_values_clamped_zero_to_one(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 100.0}},
            ability_by_topic={"Genetics": {"ability_score": 5.0, "uncertainty": 0.0}},
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert 0.0 <= result["Genetics"].stability_score <= 1.0

    def test_multiple_topics(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 90.0},
                "Cell Biology": {"average_score": 30.0},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 1.5, "uncertainty": 0.5},
                "Cell Biology": {"ability_score": -1.0, "uncertainty": 3.0},
            },
        )
        predictor = MasteryStabilityPredictor()
        result = predictor.predict_stability(snap)
        assert len(result) == 2
        assert result["Genetics"].stability_score > result["Cell Biology"].stability_score
