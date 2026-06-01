from datetime import datetime, timezone

from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)
from src.core.learning_intelligence.recommendation.scoring import PriorityCalculator


def _rec(
    action_type: LearningActionType,
    topic: str | None = None,
    priority_score: float = 0.0,
) -> LearningRecommendation:
    return LearningRecommendation(
        id="test",
        action_type=action_type,
        topic=topic,
        priority_score=priority_score,
        generated_at=datetime.now(timezone.utc),
    )


class TestNormalize:
    def test_normalize_zero(self):
        assert PriorityCalculator.normalize(0) == 0.0

    def test_normalize_max_possible(self):
        assert PriorityCalculator.normalize(120) == 1.0

    def test_normalize_midpoint(self):
        assert PriorityCalculator.normalize(60) == 0.5

    def test_normalize_clamps_below_zero(self):
        assert PriorityCalculator.normalize(-10) == 0.0

    def test_normalize_clamps_above_one(self):
        assert PriorityCalculator.normalize(240) == 1.0


class TestDeduplicate:
    def test_deduplicate_same_action_topic_keeps_higher_score(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 40.0),
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 25.0),
        ]
        result = PriorityCalculator.deduplicate(recs)
        assert len(result) == 1
        assert result[0].priority_score == 40.0

    def test_deduplicate_different_action_types_both_kept(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 40.0),
            _rec(LearningActionType.TAKE_QUIZ, "Genetics", 25.0),
        ]
        result = PriorityCalculator.deduplicate(recs)
        assert len(result) == 2

    def test_deduplicate_different_topics_both_kept(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 40.0),
            _rec(LearningActionType.REVIEW_TOPIC, "Cell Biology", 25.0),
        ]
        result = PriorityCalculator.deduplicate(recs)
        assert len(result) == 2

    def test_deduplicate_none_topic_considered_distinct(self):
        recs = [
            _rec(LearningActionType.TAKE_QUIZ, None, 40.0),
            _rec(LearningActionType.TAKE_QUIZ, None, 25.0),
        ]
        result = PriorityCalculator.deduplicate(recs)
        assert len(result) == 1
        assert result[0].priority_score == 40.0

    def test_deduplicate_empty_list(self):
        assert PriorityCalculator.deduplicate([]) == []


class TestScoreAndSort:
    def test_score_and_sort_returns_top_5(self):
        topics = [f"T{i}" for i in range(10)]
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, t, float(120 - i * 10))
            for i, t in enumerate(topics)
        ]
        result = PriorityCalculator.score_and_sort(recs)
        assert len(result) == 5

    def test_score_and_sort_normalizes_scores(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 120.0),
            _rec(LearningActionType.TAKE_QUIZ, "Cell Biology", 60.0),
        ]
        result = PriorityCalculator.score_and_sort(recs)
        assert result[0].priority_score == 1.0
        assert result[1].priority_score == 0.5

    def test_score_and_sort_orders_descending(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "C", 30.0),
            _rec(LearningActionType.REVIEW_TOPIC, "A", 120.0),
            _rec(LearningActionType.REVIEW_TOPIC, "B", 60.0),
        ]
        result = PriorityCalculator.score_and_sort(recs)
        assert [r.topic for r in result] == ["A", "B", "C"]

    def test_score_and_sort_deduplicates(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 40.0),
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 25.0),
            _rec(LearningActionType.TAKE_QUIZ, "Cell Biology", 60.0),
        ]
        result = PriorityCalculator.score_and_sort(recs)
        assert len(result) == 2

    def test_score_and_sort_empty_list(self):
        assert PriorityCalculator.score_and_sort([]) == []

    def test_score_and_sort_fewer_than_5(self):
        recs = [
            _rec(LearningActionType.REVIEW_TOPIC, "Genetics", 40.0),
            _rec(LearningActionType.TAKE_QUIZ, "Cell Biology", 25.0),
        ]
        result = PriorityCalculator.score_and_sort(recs)
        assert len(result) == 2
