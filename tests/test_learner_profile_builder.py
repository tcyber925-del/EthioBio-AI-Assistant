"""Tests for LearnerProfileBuilder."""

from datetime import datetime, timezone
from uuid import UUID

from src.core.learning_intelligence.models import (
    EducationalMemorySummary,
    GamificationSummary,
    LearnerSnapshot,
    MisconceptionSummary,
)
from src.core.learning_intelligence.tutor import (
    BuildProfileResult,
    LearnerProfileBuilder,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _snapshot(**overrides) -> LearnerSnapshot:
    defaults = dict(
        user_id=USER_ID,
        generated_at=NOW,
        mastery_by_topic={},
        ability_by_topic={},
        weak_topics=[],
        strong_topics=[],
        misconceptions=[],
        active_recovery_plans=[],
        due_reviews=[],
        educational_memory=EducationalMemorySummary(),
        gamification=GamificationSummary(),
        learning_goals=[],
    )
    defaults.update(overrides)
    return LearnerSnapshot(**defaults)


class TestBuildProfileResult:
    def test_dataclass_fields(self):
        result = BuildProfileResult(
            difficulty_level="BEGINNER",
            profile_block="## Learner Profile\n- Test",
            known_misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="wrong_answer", frequency=3),
            ],
        )
        assert result.difficulty_level == "BEGINNER"
        assert result.profile_block == "## Learner Profile\n- Test"
        assert len(result.known_misconceptions) == 1
        assert result.known_misconceptions[0].topic == "Genetics"

    def test_empty_misconceptions_default(self):
        result = BuildProfileResult(
            difficulty_level="PROFICIENT",
            profile_block="## Learner Profile",
        )
        assert result.known_misconceptions == []


class TestLearnerProfileBuilder:
    def test_build_profile_returns_result(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot()
        result = builder.build_profile(snapshot)
        assert isinstance(result, BuildProfileResult)
        assert result.difficulty_level in ("BEGINNER", "DEVELOPING", "PROFICIENT", "ADVANCED")
        assert "## Learner Profile" in result.profile_block

    def test_beginner_when_critical_severity(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            mastery_by_topic={"Genetics": {"severity": "critical", "average_score": 0.3}},
            weak_topics=["Genetics"],
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "BEGINNER"

    def test_beginner_when_low_confidence(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.2),
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "BEGINNER"

    def test_beginner_when_low_ability(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            ability_by_topic={"Genetics": {"ability_score": -1.5}},
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "BEGINNER"

    def test_developing_when_moderate_severity(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            mastery_by_topic={"Cell Biology": {"severity": "moderate", "average_score": 0.55}},
            weak_topics=["Cell Biology"],
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "DEVELOPING"

    def test_developing_when_mid_confidence(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.45),
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "DEVELOPING"

    def test_developing_when_mid_ability(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            ability_by_topic={"Genetics": {"ability_score": -0.5}},
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "DEVELOPING"

    def test_proficient_when_no_weak_topics_and_good_confidence(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            weak_topics=[],
            strong_topics=["Cell Biology"],
            mastery_by_topic={"Cell Biology": {"severity": "good", "average_score": 0.8}},
            ability_by_topic={"Cell Biology": {"ability_score": 0.5}},
            educational_memory=EducationalMemorySummary(confidence=0.7),
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "PROFICIENT"

    def test_advanced_when_no_weak_topics_and_high_confidence(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            weak_topics=[],
            strong_topics=["Cell Biology"],
            mastery_by_topic={"Cell Biology": {"severity": "good", "average_score": 0.95}},
            ability_by_topic={"Cell Biology": {"ability_score": 1.5}},
            educational_memory=EducationalMemorySummary(confidence=0.95),
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "ADVANCED"

    def test_beginner_takes_priority_over_proficient(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            weak_topics=[],
            strong_topics=["Cell Biology"],
            mastery_by_topic={"Cell Biology": {"severity": "good", "average_score": 0.8}},
            ability_by_topic={"Cell Biology": {"ability_score": 0.5}},
            educational_memory=EducationalMemorySummary(confidence=0.2),
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "BEGINNER"

    def test_beginner_default_when_no_data(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(),
            ability_by_topic={},
            weak_topics=[],
        )
        result = builder.build_profile(snapshot)
        assert result.difficulty_level == "BEGINNER"

    def test_profile_block_includes_weak_and_strong_topics(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            weak_topics=["Genetics"],
            strong_topics=["Cell Biology"],
            mastery_by_topic={
                "Genetics": {"severity": "moderate", "average_score": 0.55},
                "Cell Biology": {"severity": "good", "average_score": 0.85},
            },
        )
        result = builder.build_profile(snapshot)
        assert "Weak Topics: Genetics" in result.profile_block
        assert "Strong Topics: Cell Biology" in result.profile_block
        assert "Difficulty Level: DEVELOPING" in result.profile_block

    def test_profile_block_with_no_data(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot()
        result = builder.build_profile(snapshot)
        assert "No mastery data available" in result.profile_block

    def test_profile_block_includes_confidence(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            educational_memory=EducationalMemorySummary(confidence=0.75),
        )
        result = builder.build_profile(snapshot)
        assert "Confidence: 0.75" in result.profile_block

    def test_profile_block_includes_ability_estimates(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            ability_by_topic={
                "Genetics": {"ability_score": -0.3},
                "Cell Biology": {"ability_score": 1.2},
            },
        )
        result = builder.build_profile(snapshot)
        assert "Ability Estimates" in result.profile_block
        assert "Genetics: -0.30" in result.profile_block
        assert "Cell Biology: 1.20" in result.profile_block

    def test_misconception_detected_for_current_topic(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=3),
            ],
        )
        result = builder.build_profile(snapshot, current_topic="Genetics")
        assert len(result.known_misconceptions) == 1
        assert result.known_misconceptions[0].pattern_type == "dominant_gene"

    def test_misconception_not_included_below_frequency_threshold(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=1),
            ],
        )
        result = builder.build_profile(snapshot, current_topic="Genetics")
        assert len(result.known_misconceptions) == 0

    def test_misconception_ignored_for_different_topic(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Cell Biology", pattern_type="organelle", frequency=3),
            ],
        )
        result = builder.build_profile(snapshot, current_topic="Genetics")
        assert len(result.known_misconceptions) == 0

    def test_no_current_topic_returns_empty_misconceptions(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=3),
            ],
        )
        result = builder.build_profile(snapshot)
        assert len(result.known_misconceptions) == 0

    def test_known_misconception_section_in_profile_block(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot(
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="dominant_gene", frequency=3),
            ],
        )
        result = builder.build_profile(snapshot, current_topic="Genetics")
        assert "## Known Misconception" in result.profile_block
        assert "Pattern: dominant_gene" in result.profile_block
        assert "Frequency: 3" in result.profile_block

    def test_known_misconception_section_omitted_when_none(self):
        builder = LearnerProfileBuilder()
        snapshot = _snapshot()
        result = builder.build_profile(snapshot, current_topic="Genetics")
        assert "## Known Misconception" not in result.profile_block
