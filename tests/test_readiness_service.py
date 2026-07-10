from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
    MisconceptionSummary,
    ReviewSummary,
)
from src.core.learning_intelligence.readiness import ReadinessService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _mock_snapshot_service(returns: LearnerSnapshot):
    svc = MagicMock()
    svc.get_snapshot = AsyncMock(return_value=returns)
    return svc


class TestReadinessService:
    async def test_empty_state_when_no_mastery(self):
        snap = LearnerSnapshot(user_id=USER_ID, generated_at=NOW)
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.overall_readiness == 0.0
        assert profile.readiness_band == "Critical"
        assert profile.topic_readiness == []
        assert profile.risk_topics == []

    async def test_computes_readiness_from_mastery(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 85.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert len(profile.topic_readiness) == 1
        assert profile.topic_readiness[0].topic == "Genetics"
        assert profile.topic_readiness[0].readiness_score == 85.0
        assert profile.overall_readiness == 85.0
        assert profile.readiness_band == "Strong"

    async def test_default_score_when_no_average_score(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].readiness_score == 50.0

    async def test_overdue_review_risk_factor(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=datetime.now(timezone.utc) - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        tr = profile.topic_readiness[0]
        assert "overdue_review" in tr.risk_factors
        assert tr.review_status == "overdue"

    async def test_active_misconception_risk_factor(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="confusion", frequency=3),
            ],
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert "active_misconception" in profile.topic_readiness[0].risk_factors

    async def test_low_ability_risk_factor_when_ability_below_threshold(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.2, "uncertainty": 1.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert "low_ability" in profile.topic_readiness[0].risk_factors

    async def test_low_ability_risk_factor_when_uncertainty_high(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.5, "uncertainty": 2.5}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert "low_ability" in profile.topic_readiness[0].risk_factors

    async def test_risk_level_low_with_zero_factors(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].risk_level == "LOW"

    async def test_risk_level_moderate_with_one_factor(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.2, "uncertainty": 1.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].risk_level == "MODERATE"

    async def test_risk_level_high_with_two_factors(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.2, "uncertainty": 1.0}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=datetime.now(timezone.utc) - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].risk_level == "HIGH"

    async def test_risk_level_critical_with_three_factors(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
            ability_by_topic={"Genetics": {"ability_score": 0.2, "uncertainty": 1.0}},
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=datetime.now(timezone.utc) - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
            misconceptions=[
                MisconceptionSummary(topic="Genetics", pattern_type="confusion", frequency=3),
            ],
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].risk_level == "CRITICAL"

    async def test_overall_readiness_averages_topics(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 90.0},
                "Cell Biology": {"average_score": 70.0},
            },
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.overall_readiness == 80.0

    async def test_readiness_band_critical_below_40(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 30.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.readiness_band == "Critical"

    async def test_readiness_band_developing_40_to_59(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 50.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.readiness_band == "Developing"

    async def test_readiness_band_ready_60_to_79(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.readiness_band == "Ready"

    async def test_readiness_band_strong_80_plus(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 90.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.readiness_band == "Strong"

    async def test_risk_topics_contains_high_and_critical(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 70.0},
                "Cell Biology": {"average_score": 50.0},
            },
            ability_by_topic={
                "Genetics": {"ability_score": 0.2, "uncertainty": 1.0},
                "Cell Biology": {"ability_score": 0.2, "uncertainty": 1.0},
            },
            due_reviews=[
                ReviewSummary(
                    topic="Genetics",
                    next_review_at=datetime.now(timezone.utc) - timedelta(days=1),
                    days_overdue=1,
                ),
                ReviewSummary(
                    topic="Cell Biology",
                    next_review_at=datetime.now(timezone.utc) - timedelta(days=1),
                    days_overdue=1,
                ),
            ],
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert "Genetics" in profile.risk_topics
        assert "Cell Biology" in profile.risk_topics

    async def test_risk_topics_excludes_low_and_moderate(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={
                "Genetics": {"average_score": 70.0},  # 0 factors -> LOW
                "Cell Biology": {"average_score": 50.0},
            },
            ability_by_topic={
                "Cell Biology": {"ability_score": 0.2, "uncertainty": 1.0},  # 1 factor -> MODERATE
            },
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert "Genetics" not in profile.risk_topics
        assert "Cell Biology" not in profile.risk_topics

    async def test_review_status_current_when_not_overdue(self):
        snap = LearnerSnapshot(
            user_id=USER_ID,
            generated_at=NOW,
            mastery_by_topic={"Genetics": {"average_score": 70.0}},
        )
        svc = ReadinessService(
            snapshot_service=_mock_snapshot_service(snap),
        )
        profile = await svc.get_readiness(MagicMock(), USER_ID)
        assert profile.topic_readiness[0].review_status == "current"
