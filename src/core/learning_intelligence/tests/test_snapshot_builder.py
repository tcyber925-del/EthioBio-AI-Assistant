from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.learning_intelligence.models import (
    EducationalMemorySummary,
    GamificationSummary,
    LearnerSnapshot,
    MisconceptionSummary,
    RecoverySummary,
    ReviewSummary,
)
from src.core.learning_intelligence.snapshot.snapshot_builder import SnapshotBuilder


@pytest.fixture
def mock_session():
    return AsyncMock()


LOADER_NAMES = [
    "mastery",
    "ability",
    "misconceptions",
    "recovery",
    "reviews",
    "memory",
    "gamification",
]


def _make_loaders(
    loader_values: dict[str, dict | None | Exception],
) -> list[tuple[str, AsyncMock]]:
    loaders: list[tuple[str, AsyncMock]] = []
    for name, value in loader_values.items():
        mock = AsyncMock()
        if isinstance(value, Exception):
            mock.side_effect = value
        else:
            mock.return_value = value
        loaders.append((name, mock))
    return loaders


async def test_build_merges_all_loader_data(mock_session):
    user_id = uuid4()
    loaders = _make_loaders(
        {
            "mastery": {
                "mastery_by_topic": {"Cell Biology": {"average_score": 0.85}},
                "weak_topics": ["Genetics"],
                "strong_topics": ["Cell Biology"],
            },
            "ability": {
                "ability_by_topic": {"Cell Biology": {"ability_score": 1.2}},
            },
            "misconceptions": {
                "misconceptions": [
                    MisconceptionSummary(
                        topic="Genetics", pattern_type="dominant_gene", frequency=3
                    ),
                ],
            },
            "recovery": {
                "active_recovery_plans": [
                    RecoverySummary(
                        topic="Genetics",
                        progress_pct=40.0,
                        completed_tasks=2,
                        total_tasks=5,
                        status="active",
                    ),
                ],
            },
            "reviews": {
                "due_reviews": [
                    ReviewSummary(
                        topic="Cell Biology", next_review_at="2024-01-01", days_overdue=10
                    ),
                ],
            },
            "memory": {
                "educational_memory": EducationalMemorySummary(
                    understanding_level="intermediate",
                    confidence=0.8,
                    active_learning_goals=["Master mitosis"],
                    recent_topics=["Cell Biology"],
                ),
                "learning_goals": ["Master mitosis"],
            },
            "gamification": {
                "gamification": GamificationSummary(
                    current_streak=3,
                    longest_streak=10,
                    total_xp=500,
                    level=5,
                    recent_activity_score=0.6,
                ),
            },
        }
    )

    builder = SnapshotBuilder()
    builder.LOADERS = loaders

    snapshot = await builder.build(mock_session, user_id)

    assert isinstance(snapshot, LearnerSnapshot)
    assert snapshot.user_id == user_id
    assert snapshot.mastery_by_topic["Cell Biology"]["average_score"] == 0.85
    assert "Genetics" in snapshot.weak_topics
    assert "Cell Biology" in snapshot.strong_topics
    assert len(snapshot.misconceptions) == 1
    assert snapshot.misconceptions[0].pattern_type == "dominant_gene"
    assert len(snapshot.active_recovery_plans) == 1
    assert snapshot.active_recovery_plans[0].progress_pct == 40.0
    assert snapshot.gamification.total_xp == 500
    assert len(snapshot.learning_goals) == 1
    assert snapshot.learning_goals[0] == "Master mitosis"
    assert not snapshot.degraded


async def test_build_all_loaders_return_none_produces_empty_snapshot(mock_session):
    user_id = uuid4()
    loaders = _make_loaders(dict.fromkeys(LOADER_NAMES, None))

    builder = SnapshotBuilder()
    builder.LOADERS = loaders

    snapshot = await builder.build(mock_session, user_id)

    assert isinstance(snapshot, LearnerSnapshot)
    assert snapshot.user_id == user_id
    assert snapshot.mastery_by_topic == {}
    assert snapshot.weak_topics == []
    assert snapshot.strong_topics == []
    assert snapshot.misconceptions == []
    assert snapshot.active_recovery_plans == []
    assert snapshot.due_reviews == []
    assert snapshot.gamification.total_xp == 0
    assert not snapshot.degraded


async def test_build_degraded_when_loader_raises(mock_session):
    user_id = uuid4()
    loaders = _make_loaders(
        {
            "mastery": Exception("DB timeout"),
            "ability": {
                "ability_by_topic": {"Cell Biology": {"ability_score": 1.2}},
            },
            "misconceptions": None,
            "recovery": None,
            "reviews": None,
            "memory": None,
            "gamification": None,
        }
    )

    builder = SnapshotBuilder()
    builder.LOADERS = loaders

    snapshot = await builder.build(mock_session, user_id)

    assert snapshot.degraded
    assert "mastery" in snapshot.degraded_sources
    assert snapshot.ability_by_topic["Cell Biology"]["ability_score"] == 1.2


async def test_build_partial_data_does_not_raise(mock_session):
    user_id = uuid4()
    loaders = _make_loaders(
        {
            "mastery": {
                "mastery_by_topic": {"Genetics": {"average_score": 0.45}},
                "weak_topics": ["Genetics"],
                "strong_topics": [],
            },
            "ability": Exception("Ability service down"),
            "misconceptions": None,
            "recovery": None,
            "reviews": None,
            "memory": None,
            "gamification": None,
        }
    )

    builder = SnapshotBuilder()
    builder.LOADERS = loaders

    snapshot = await builder.build(mock_session, user_id)

    assert snapshot.degraded
    assert "ability" in snapshot.degraded_sources
    assert snapshot.mastery_by_topic["Genetics"]["average_score"] == 0.45
    assert snapshot.ability_by_topic == {}
