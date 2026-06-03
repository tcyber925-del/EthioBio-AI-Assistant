from datetime import datetime, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
    MisconceptionSummary,
)
from src.core.learning_intelligence.readiness.intervention_planner import (
    InterventionPlanner,
)
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    ForgettingRisk,
    StabilityScore,
    TopicReadiness,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _make_profile(
    risk_topics: list[str],
    topic_scores: dict[str, float],
) -> ExamReadinessProfile:
    return ExamReadinessProfile(
        user_id=USER_ID,
        generated_at=NOW,
        overall_readiness=sum(topic_scores.values()) / len(topic_scores) if topic_scores else 0.0,
        readiness_band="Developing",
        topic_readiness=[
            TopicReadiness(
                topic=t,
                readiness_score=s,
                risk_level="HIGH" if t in risk_topics else "LOW",
                risk_factors=[],
                review_status="current",
            )
            for t, s in topic_scores.items()
        ],
        risk_topics=risk_topics,
        confidence_score=0.8,
    )


def _forgetting_risks(
    data: dict[str, float],
) -> dict[str, ForgettingRisk]:
    return {
        t: ForgettingRisk(topic=t, forgetting_risk=r, contributing_factors=["no_review_data"])
        for t, r in data.items()
    }


def _stabilities(
    data: dict[str, float],
) -> dict[str, StabilityScore]:
    return {
        t: StabilityScore(
            topic=t,
            stability_score=s,
            stability_band="Stable" if s >= 0.7 else "Moderate" if s >= 0.4 else "Volatile",
        )
        for t, s in data.items()
    }


class TestInterventionPlanner:
    def test_empty_when_no_topics(self):
        snap = LearnerSnapshot(user_id=USER_ID, generated_at=NOW)
        planner = InterventionPlanner()
        profile = _make_profile([], {})
        result = planner.plan(snap, profile, {}, {})
        assert result == []

    def test_intervention_for_risk_topic(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 40.0}},
        )
        planner = InterventionPlanner()
        profile = _make_profile(["Genetics"], {"Genetics": 40.0})
        result = planner.plan(
            snap, profile,
            _forgetting_risks({"Genetics": 0.5}),
            _stabilities({"Genetics": 0.5}),
        )
        assert len(result) >= 1
        assert result[0].topic == "Genetics"
        assert result[0].action_type == "REVIEW_TOPIC"

    def test_intervention_revise_misconception(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 40.0}},
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="confusion", frequency=3),
            ],
        )
        planner = InterventionPlanner()
        profile = _make_profile(["Genetics"], {"Genetics": 40.0})
        result = planner.plan(
            snap, profile,
            _forgetting_risks({"Genetics": 0.5}),
            _stabilities({"Genetics": 0.5}),
        )
        assert any(i.action_type == "REVISE_MISCONCEPTION" for i in result)

    def test_intervention_for_high_forgetting(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 80.0}},
        )
        planner = InterventionPlanner()
        profile = _make_profile([], {"Genetics": 80.0})
        result = planner.plan(
            snap, profile,
            _forgetting_risks({"Genetics": 0.8}),
            _stabilities({"Genetics": 0.7}),
        )
        assert any(i.action_type == "REVIEW_TOPIC" for i in result)
        assert any("forgetting" in i.reason.lower() for i in result)

    def test_intervention_for_low_stability(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 60.0}},
        )
        planner = InterventionPlanner()
        profile = _make_profile([], {"Genetics": 60.0})
        result = planner.plan(
            snap, profile,
            _forgetting_risks({"Genetics": 0.3}),
            _stabilities({"Genetics": 0.2}),
        )
        assert any(i.action_type == "REVIEW_TOPIC" for i in result)
        assert any("Unstable" in i.reason for i in result)

    def test_sorted_by_priority_descending(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 30.0},
                "Cell Bio": {"average_score": 70.0},
                "Ecology": {"average_score": 90.0},
            },
        )
        planner = InterventionPlanner()
        profile = _make_profile(
            ["Genetics"],
            {"Genetics": 30.0, "Cell Bio": 70.0, "Ecology": 90.0},
        )
        forgetting = _forgetting_risks({"Genetics": 0.7, "Cell Bio": 0.3, "Ecology": 0.1})
        stabilities = _stabilities({"Genetics": 0.2, "Cell Bio": 0.6, "Ecology": 0.9})
        result = planner.plan(snap, profile, forgetting, stabilities)
        priorities = [i.priority for i in result]
        assert priorities == sorted(priorities, reverse=True)

    def test_impact_calculation(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 50.0}},
        )
        planner = InterventionPlanner()
        profile = _make_profile(["Genetics"], {"Genetics": 50.0})
        result = planner.plan(
            snap, profile,
            _forgetting_risks({"Genetics": 0.3}),
            _stabilities({"Genetics": 0.5}),
        )
        for intervention in result:
            assert intervention.estimated_impact > 0
