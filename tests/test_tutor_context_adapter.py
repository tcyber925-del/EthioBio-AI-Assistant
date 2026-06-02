"""Tests for TutorContextAdapter."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.learning_intelligence.models import (
    EducationalMemorySummary,
    GamificationSummary,
    LearnerSnapshot,
)
from src.core.learning_intelligence.tutor.learner_profile_builder import (
    BuildProfileResult,
)
from src.core.learning_intelligence.tutor.tutor_context_adapter import (
    TutorContextAdapter,
    format_context_block,
)
from src.core.learning_intelligence.tutor.tutor_context_package import (
    TutorContextPackage,
)


def _make_mock_adapter_deps():
    snapshot = LearnerSnapshot(
        user_id=uuid4(), generated_at=__import__("datetime").datetime.now(),
        educational_memory=EducationalMemorySummary(),
        gamification=GamificationSummary(),
    )
    snapshot_svc = AsyncMock()
    snapshot_svc.get_snapshot = AsyncMock(return_value=snapshot)

    profile_result = BuildProfileResult(
        difficulty_level="BEGINNER",
        profile_block="## Learner Profile\n- Weak Topics: Genetics",
    )
    profile_builder = MagicMock()
    profile_builder.build_profile = MagicMock(return_value=profile_result)

    recommendation_svc = AsyncMock()
    recommendation_svc.get_recommendations = AsyncMock(return_value=[])

    strategy_selector = MagicMock()
    strategy_selector.select = MagicMock(return_value="DIRECT_EXPLANATION")

    return snapshot_svc, profile_builder, recommendation_svc, strategy_selector


@pytest.mark.asyncio
async def test_build_returns_package():
    deps = _make_mock_adapter_deps()
    adapter = TutorContextAdapter(*deps)

    user_id = uuid4()
    package = await adapter.build(MagicMock(), user_id, current_topic="Genetics")

    assert isinstance(package, TutorContextPackage)
    assert deps[0].get_snapshot.called
    assert deps[1].build_profile.called
    assert deps[2].get_recommendations.called
    assert deps[3].select.called


@pytest.mark.asyncio
async def test_build_sets_formatted_block():
    deps = _make_mock_adapter_deps()
    adapter = TutorContextAdapter(*deps)

    package = await adapter.build(MagicMock(), uuid4())
    assert isinstance(package.formatted_block, str)
    assert len(package.formatted_block) > 0
    assert "## Learner Profile" in package.formatted_block


@pytest.mark.asyncio
async def test_build_passes_current_topic_to_profile_builder():
    deps = _make_mock_adapter_deps()
    adapter = TutorContextAdapter(*deps)

    await adapter.build(MagicMock(), uuid4(), current_topic="Cell Biology")
    args, _ = deps[1].build_profile.call_args
    assert args[1] == "Cell Biology"


@pytest.mark.asyncio
async def test_build_limits_recommendations_to_three():
    snapshot_svc, profile_builder, recommendation_svc, strategy_selector = _make_mock_adapter_deps()

    from src.core.learning_intelligence.recommendation.models import LearningRecommendation
    from datetime import datetime, timezone

    recs = [
        MagicMock(spec=LearningRecommendation, reason=f"Rec {i}",
                  action_type="review_topic", topic="Bio")
        for i in range(7)
    ]
    recommendation_svc.get_recommendations = AsyncMock(return_value=recs)

    adapter = TutorContextAdapter(snapshot_svc, profile_builder, recommendation_svc, strategy_selector)
    package = await adapter.build(MagicMock(), uuid4())
    assert len(package.top_recommendations) <= 3


def test_format_context_block_includes_profile():
    block = format_context_block(
        profile_block="## Learner Profile\n- Weak Topics: Genetics",
        recommendations=[],
        strategy="",
    )
    assert "## Learner Profile" in block
    assert "Weak Topics: Genetics" in block
    assert "## Learning Recommendations" not in block


def test_format_context_block_includes_recommendations():
    block = format_context_block(
        profile_block="## Learner Profile",
        recommendations=[
            {"reason": "Review Genetics", "action_type": "review_topic"},
            {"reason": "Take a quiz on Cell Biology", "action_type": "take_quiz"},
        ],
        strategy="",
    )
    assert "## Learning Recommendations" in block
    assert "Review Genetics" in block
    assert "Take a quiz on Cell Biology" in block


def test_format_context_block_includes_strategy():
    block = format_context_block(
        profile_block="## Learner Profile",
        recommendations=[],
        strategy="CONFIDENCE_BUILDING",
    )
    assert "## Teaching Strategy" in block
    assert "low confidence" in block.lower()


def test_format_context_block_includes_all_sections():
    block = format_context_block(
        profile_block="## Learner Profile\n- Difficulty Level: BEGINNER",
        recommendations=[
            {"reason": "Review Genetics", "action_type": "review_topic"},
        ],
        strategy="MISCONCEPTION_REMEDIATION",
    )
    assert "## Learner Profile" in block
    assert "## Learning Recommendations" in block
    assert "## Teaching Strategy" in block
