from datetime import datetime, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
)
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    ForgettingRisk,
    StabilityScore,
    TopicReadiness,
)
from src.core.learning_intelligence.readiness.projected_score import (
    ProjectedScoreCalculator,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _make_profile(
    overall: float = 80.0,
    topics: list[tuple[str, float, str]] | None = None,
) -> ExamReadinessProfile:
    if topics is None:
        topics = [("Genetics", overall, "LOW")]
    return ExamReadinessProfile(
        user_id=USER_ID,
        generated_at=NOW,
        overall_readiness=overall,
        readiness_band="Ready" if overall >= 60 else "Critical",
        topic_readiness=[
            TopicReadiness(
                topic=t,
                readiness_score=s,
                risk_level=r,
                risk_factors=[],
                review_status="current",
            )
            for t, s, r in topics
        ],
        risk_topics=[t for t, s, r in topics if r in ("HIGH", "CRITICAL")],
    )


def _forgetting_risks(data: dict[str, float]) -> dict[str, ForgettingRisk]:
    return {
        t: ForgettingRisk(topic=t, forgetting_risk=r, contributing_factors=["no_review_data"])
        for t, r in data.items()
    }


def _stabilities(data: dict[str, float]) -> dict[str, StabilityScore]:
    return {
        t: StabilityScore(
            topic=t,
            stability_score=s,
            stability_band="Stable" if s >= 0.7 else "Moderate" if s >= 0.4 else "Volatile",
        )
        for t, s in data.items()
    }


class TestProjectedScoreCalculator:
    def test_empty_state(self):
        snap = LearnerSnapshot(user_id=USER_ID, generated_at=NOW)
        calc = ProjectedScoreCalculator()
        profile = _make_profile(overall=0.0, topics=[])
        projected, confidence = calc.calculate(profile, {}, {}, snap)
        assert projected == 0.0
        assert confidence == 0.5

    def test_high_readiness_high_projected(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 90.0, "attempt_count": 5}},
            ability_by_topic={"Genetics": {"ability_score": 1.5, "uncertainty": 0.5}},
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(overall=90.0)
        projected, confidence = calc.calculate(
            profile,
            _forgetting_risks({"Genetics": 0.1}),
            _stabilities({"Genetics": 0.8}),
            snap,
        )
        assert projected >= 60.0
        assert 0.1 <= confidence <= 1.0

    def test_low_readiness_low_projected(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 30.0, "attempt_count": 1}},
            ability_by_topic={"Genetics": {"ability_score": -1.0, "uncertainty": 3.0}},
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(overall=30.0)
        projected, _ = calc.calculate(
            profile,
            _forgetting_risks({"Genetics": 0.7}),
            _stabilities({"Genetics": 0.2}),
            snap,
        )
        assert projected < 45.0

    def test_confidence_deducted_for_low_attempts(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 80.0, "attempt_count": 1},
                "Cell Bio": {"average_score": 80.0, "attempt_count": 2},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 0.5, "uncertainty": 1.0},
                "Cell Bio": {"ability_score": 0.5, "uncertainty": 1.0},
            },
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(
            overall=80.0,
            topics=[("Genetics", 80.0, "LOW"), ("Cell Bio", 80.0, "LOW")],
        )
        _, confidence = calc.calculate(profile, {}, {}, snap)
        assert confidence < 1.0
        assert confidence >= 0.1

    def test_confidence_deducted_for_high_uncertainty(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 80.0, "attempt_count": 5},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 0.0, "uncertainty": 2.5},
            },
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(overall=80.0)
        _, confidence = calc.calculate(profile, {}, {}, snap)
        assert confidence < 1.0

    def test_confidence_deducted_for_multiple_factors(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 80.0, "attempt_count": 1},
                "Cell Bio": {"average_score": 80.0, "attempt_count": 5},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 0.0, "uncertainty": 2.5},
                "Cell Bio": {"ability_score": 0.5, "uncertainty": 1.0},
            },
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(
            overall=80.0,
            topics=[("Genetics", 80.0, "LOW"), ("Cell Bio", 80.0, "LOW")],
        )
        _, confidence = calc.calculate(profile, {}, {}, snap)
        assert confidence < 1.0
        assert confidence >= 0.1

    def test_confidence_high_with_good_data(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 85.0, "attempt_count": 10},
                "Cell Bio": {"average_score": 90.0, "attempt_count": 8},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 1.0, "uncertainty": 0.5},
                "Cell Bio": {"ability_score": 1.2, "uncertainty": 0.3},
            },
        )
        calc = ProjectedScoreCalculator()
        profile = _make_profile(
            overall=85.0,
            topics=[("Genetics", 85.0, "LOW"), ("Cell Bio", 90.0, "LOW")],
        )
        _, confidence = calc.calculate(profile, {}, {}, snap)
        assert confidence == 1.0
