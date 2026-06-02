"""Tests for AdaptiveStrategySelector."""

from datetime import datetime, timezone
from uuid import uuid4

from src.core.learning_intelligence.models import (
    EducationalMemorySummary,
    GamificationSummary,
    LearnerSnapshot,
    MisconceptionSummary,
    RecoverySummary,
)
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)
from src.core.learning_intelligence.tutor.adaptive_strategy_selector import (
    AdaptiveStrategySelector,
)
from src.core.learning_intelligence.tutor.learner_profile_builder import (
    BuildProfileResult,
)


def _snapshot(**overrides) -> LearnerSnapshot:
    defaults = dict(
        user_id=uuid4(), generated_at=datetime.now(timezone.utc),
        mastery_by_topic={}, ability_by_topic={}, weak_topics=[], strong_topics=[],
        misconceptions=[], active_recovery_plans=[], due_reviews=[],
        educational_memory=EducationalMemorySummary(),
        gamification=GamificationSummary(), learning_goals=[],
    )
    defaults.update(overrides)
    return LearnerSnapshot(**defaults)


def _profile(difficulty="BEGINNER", misconceptions=None) -> BuildProfileResult:
    return BuildProfileResult(
        difficulty_level=difficulty,
        profile_block="## Learner Profile",
        known_misconceptions=misconceptions or [],
    )


class TestAdaptiveStrategySelector:
    def test_defaults_to_direct_explanation(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot()
        profile = _profile()
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "DIRECT_EXPLANATION"

    def test_misconception_remediation_when_known_misconceptions_exist(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot()
        profile = _profile(misconceptions=[
            MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=3),
        ])
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "MISCONCEPTION_REMEDIATION"

    def test_confidence_building_when_low_confidence(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.2),
        )
        profile = _profile()
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "CONFIDENCE_BUILDING"

    def test_recovery_support_when_active_plans_exist(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            active_recovery_plans=[
                RecoverySummary(
                    topic="Cell Division", progress_pct=0.4,
                    completed_tasks=2, total_tasks=5, status="active",
                ),
            ],
            educational_memory=EducationalMemorySummary(confidence=0.8),
        )
        profile = _profile()
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "RECOVERY_SUPPORT"

    def test_exam_preparation_when_exam_recommendation(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot()
        profile = _profile()
        recommendations = [
            LearningRecommendation(
                id="rec_1", action_type=LearningActionType.EXAM_PRACTICE,
                topic="Biology", reason="Exam approaching",
                generated_at=datetime.now(timezone.utc),
            ),
        ]
        strategy = selector.select(profile, snapshot, recommendations)
        assert strategy == "EXAM_PREPARATION"

    def test_misconception_takes_priority_over_confidence(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.2),
        )
        profile = _profile(misconceptions=[
            MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=3),
        ])
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "MISCONCEPTION_REMEDIATION"

    def test_confidence_takes_priority_over_recovery(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.2),
            active_recovery_plans=[
                RecoverySummary(
                    topic="Cell Division", progress_pct=0.4,
                    completed_tasks=2, total_tasks=5, status="active",
                ),
            ],
        )
        profile = _profile()
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "CONFIDENCE_BUILDING"

    def test_recovery_takes_priority_over_exam(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            active_recovery_plans=[
                RecoverySummary(
                    topic="Cell Division", progress_pct=0.4,
                    completed_tasks=2, total_tasks=5, status="active",
                ),
            ],
            educational_memory=EducationalMemorySummary(confidence=0.8),
        )
        profile = _profile()
        recommendations = [
            LearningRecommendation(
                id="rec_1", action_type=LearningActionType.EXAM_PRACTICE,
                topic="Biology", reason="Exam approaching",
                generated_at=datetime.now(timezone.utc),
            ),
        ]
        strategy = selector.select(profile, snapshot, recommendations)
        assert strategy == "RECOVERY_SUPPORT"

    def test_confidence_not_low_when_none(self):
        selector = AdaptiveStrategySelector()
        snapshot = _snapshot(
            active_recovery_plans=[
                RecoverySummary(
                    topic="Cell Division", progress_pct=0.4,
                    completed_tasks=2, total_tasks=5, status="active",
                ),
            ],
        )
        profile = _profile()
        strategy = selector.select(profile, snapshot, [])
        assert strategy == "RECOVERY_SUPPORT"

    def test_strategy_instructions_are_not_empty(self):
        assert AdaptiveStrategySelector.STRATEGY_INSTRUCTIONS
        for name, instruction in AdaptiveStrategySelector.STRATEGY_INSTRUCTIONS.items():
            assert instruction, f"Empty instruction for {name}"
