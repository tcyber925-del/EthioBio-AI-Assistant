"""Tests for readiness recommendation rules."""

from datetime import datetime, timezone
from uuid import uuid4

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
)
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    TopicReadiness,
)
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
)
from src.core.learning_intelligence.recommendation.rules.readiness_rules import (
    generate_readiness_recommendations,
)


def _snapshot(**overrides) -> LearnerSnapshot:
    defaults = {
        "user_id": uuid4(),
        "generated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return LearnerSnapshot(**defaults)


def _readiness_profile(
    risk_topics: list[str],
    topic_scores: dict[str, float] | None = None,
) -> ExamReadinessProfile:
    if topic_scores is None:
        topic_scores = dict.fromkeys(risk_topics, 40.0) if risk_topics else {}
    return ExamReadinessProfile(
        user_id=uuid4(),
        generated_at=datetime.now(timezone.utc),
        overall_readiness=(sum(topic_scores.values()) / len(topic_scores) if topic_scores else 0.0),
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
    )


class TestReadinessRules:
    async def test_empty_when_no_readiness_profile(self):
        snap = _snapshot()
        result = await generate_readiness_recommendations(snap, None)
        assert result == []

    async def test_empty_when_no_risk_topics(self):
        snap = _snapshot()
        profile = _readiness_profile([])
        result = await generate_readiness_recommendations(snap, profile)
        assert result == []

    async def test_generates_review_for_risk_topic(self):
        snap = _snapshot()
        profile = _readiness_profile(["Genetics"], {"Genetics": 40.0})
        result = await generate_readiness_recommendations(snap, profile)
        assert len(result) == 1
        assert result[0].topic == "Genetics"
        assert result[0].action_type == LearningActionType.REVIEW_TOPIC

    async def test_priority_score_from_readiness(self):
        snap = _snapshot()
        profile = _readiness_profile(["Genetics"], {"Genetics": 30.0})
        result = await generate_readiness_recommendations(snap, profile)
        expected = (100.0 - 30.0) / 100.0 * 40.0
        assert result[0].priority_score == expected

    async def test_lower_readiness_higher_score(self):
        snap = _snapshot()
        profile_low = _readiness_profile(["Genetics"], {"Genetics": 20.0})
        profile_high = _readiness_profile(["Genetics"], {"Genetics": 80.0})
        low_result = await generate_readiness_recommendations(snap, profile_low)
        high_result = await generate_readiness_recommendations(snap, profile_high)
        assert low_result[0].priority_score > high_result[0].priority_score

    async def test_multiple_risk_topics(self):
        snap = _snapshot()
        profile = _readiness_profile(
            ["Genetics", "Cell Bio"],
            {"Genetics": 30.0, "Cell Bio": 45.0},
        )
        result = await generate_readiness_recommendations(snap, profile)
        assert len(result) == 2
        topics = {r.topic for r in result}
        assert topics == {"Genetics", "Cell Bio"}

    async def test_explanation_includes_readiness(self):
        snap = _snapshot()
        profile = _readiness_profile(["Genetics"], {"Genetics": 35.0})
        result = await generate_readiness_recommendations(snap, profile)
        assert "35%" in result[0].explanation
        assert "high-risk" in result[0].explanation.lower()
