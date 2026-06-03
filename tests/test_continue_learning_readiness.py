from datetime import datetime, timezone
from uuid import uuid4

from src.core.learning_intelligence.continue_learning.service import (
    ContinueLearningService,
)
from src.core.learning_intelligence.models.continue_learning import LearningCard
from src.core.learning_intelligence.readiness.models.readiness_profile import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.recommendation.models.types import (
    LearningActionType,
)


def _card(
    topic: str | None,
    priority: float = 50.0,
) -> LearningCard:
    return LearningCard(
        id=str(uuid4()),
        title=f"Study {topic}" if topic else "Generic card",
        description="desc",
        action_type=LearningActionType.REVIEW_TOPIC,
        priority_score=priority,
        topic=topic,
    )


def _readiness_profile(risk_topics: list[str]) -> ExamReadinessProfile:
    return ExamReadinessProfile(
        user_id=uuid4(),
        generated_at=datetime.now(timezone.utc),
        overall_readiness=50.0,
        readiness_band="Developing",
        topic_readiness=[],
        risk_topics=risk_topics,
    )


class TestApplyReadinessBoost:
    def test_risk_topic_gets_priority_boost(self):
        cards = [_card("genetics", 70.0), _card("cell_biology", 50.0)]
        profile = _readiness_profile(["genetics"])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        genetics_card = next(c for c in cards if c.topic == "genetics")
        assert genetics_card.priority_score == 91.0  # 70 * 1.3
        assert genetics_card.exam_impact == "high"

    def test_non_risk_topic_unchanged(self):
        cards = [_card("genetics", 70.0), _card("cell_biology", 50.0)]
        profile = _readiness_profile(["genetics"])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        cell_card = next(c for c in cards if c.topic == "cell_biology")
        assert cell_card.priority_score == 50.0
        assert cell_card.exam_impact is None

    def test_card_without_topic_skipped(self):
        cards = [_card(None, 80.0)]
        profile = _readiness_profile(["genetics"])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        assert cards[0].priority_score == 80.0
        assert cards[0].exam_impact is None

    def test_boost_capped_at_100(self):
        cards = [_card("genetics", 80.0)]
        profile = _readiness_profile(["genetics"])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        assert cards[0].priority_score == 100.0  # 80 * 1.3 = 104, capped

    def test_sorting_puts_risk_topics_first(self):
        cards = [
            _card("cell_biology", 50.0),
            _card("genetics", 70.0),
            _card("ecology", 60.0),
        ]
        profile = _readiness_profile(["genetics", "ecology"])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        assert cards[0].topic == "genetics"  # 70*1.3 = 91
        assert cards[1].topic == "ecology"  # 60*1.3 = 78
        assert cards[2].topic == "cell_biology"  # 50 (unchanged)

    def test_no_risk_topics_no_change(self):
        cards = [_card("genetics", 70.0)]
        profile = _readiness_profile([])

        ContinueLearningService._apply_readiness_boost(cards, profile)

        assert cards[0].priority_score == 70.0
        assert cards[0].exam_impact is None

    def test_risk_set_uses_topic_not_title_or_id(self):
        cards = [
            _card("Genetics", 70.0),
            _card("Cell Biology", 50.0),
        ]
        profile = _readiness_profile(["genetics"])  # lowercase mismatch

        ContinueLearningService._apply_readiness_boost(cards, profile)

        assert cards[0].priority_score == 70.0  # not boosted — case mismatch
        assert cards[0].exam_impact is None
