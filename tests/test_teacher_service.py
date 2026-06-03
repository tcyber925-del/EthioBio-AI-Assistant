from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.core.learning_intelligence.readiness.models.intervention import (
    Intervention,
)
from src.core.learning_intelligence.readiness.models.readiness_profile import (
    ExamReadinessProfile,
    TopicReadiness,
)
from src.core.learning_intelligence.teacher.teacher_service import TeacherService

USER_ID = uuid4()
NOW = datetime.now(timezone.utc)


def _profile(
    user_id: UUID | None = None,
    overall_readiness: float = 70.0,
    readiness_band: str = "Ready",
    risk_topics: list[str] | None = None,
    topic_readiness: list | None = None,
    interventions: list | None = None,
) -> ExamReadinessProfile:
    return ExamReadinessProfile(
        user_id=user_id or uuid4(),
        generated_at=NOW,
        overall_readiness=overall_readiness,
        readiness_band=readiness_band,
        topic_readiness=topic_readiness or [],
        risk_topics=risk_topics or [],
        recommended_interventions=interventions or [],
    )


class TestBuildClassroomProfile:
    def test_empty_profiles_returns_empty_profile(self):
        service = TeacherService()
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=5,
            profiles=[],
        )
        assert profile.classroom_health == 0.0
        assert profile.total_students == 0
        assert profile.risk_students == []
        assert profile.intervention_candidates == []
        assert profile.mastery_heatmap == {}

    def test_averages_readiness_scores(self):
        service = TeacherService()
        profiles = [
            _profile(overall_readiness=80.0, readiness_band="Strong"),
            _profile(overall_readiness=60.0, readiness_band="Ready"),
            _profile(overall_readiness=40.0, readiness_band="Developing"),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=3,
            profiles=profiles,
        )
        assert profile.classroom_health == 60.0

    def test_readiness_distribution_counts_bands(self):
        service = TeacherService()
        profiles = [
            _profile(overall_readiness=85.0, readiness_band="Strong"),
            _profile(overall_readiness=75.0, readiness_band="Ready"),
            _profile(overall_readiness=75.0, readiness_band="Ready"),
            _profile(overall_readiness=45.0, readiness_band="Developing"),
            _profile(overall_readiness=20.0, readiness_band="Critical"),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=5,
            profiles=profiles,
        )
        assert profile.readiness_distribution == {
            "Strong": 1,
            "Ready": 2,
            "Developing": 1,
            "Critical": 1,
        }

    def test_risk_students_identified_by_low_readiness(self):
        service = TeacherService()
        profiles = [
            _profile(overall_readiness=30.0, readiness_band="Critical"),
            _profile(overall_readiness=70.0, readiness_band="Ready"),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=2,
            profiles=profiles,
        )
        assert len(profile.risk_students) == 1
        assert profile.risk_students[0].readiness_score == 30.0
        assert profile.risk_students[0].risk_level == "CRITICAL"

    def test_risk_students_identified_by_risk_topics(self):
        service = TeacherService()
        profiles = [
            _profile(
                overall_readiness=65.0,
                readiness_band="Ready",
                risk_topics=["genetics"],
            ),
            _profile(overall_readiness=90.0, readiness_band="Strong"),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=2,
            profiles=profiles,
        )
        assert len(profile.risk_students) == 1

    def test_interventions_collected_and_sorted(self):
        service = TeacherService()
        def intv(topic, priority, impact, reason):
            return Intervention(
                topic=topic, priority=priority,
                action_type="REVIEW_TOPIC",
                estimated_impact=impact, reason=reason,
            )
        ints_1 = [intv("genetics", 0.8, 30, "low mastery")]
        ints_2 = [intv("cell_division", 0.9, 40, "low score")]
        profiles = [
            _profile(overall_readiness=30.0, readiness_band="Critical", interventions=ints_1),
            _profile(overall_readiness=25.0, readiness_band="Critical", interventions=ints_2),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=2,
            profiles=profiles,
        )
        assert len(profile.intervention_candidates) == 2
        assert profile.intervention_candidates[0].priority == 0.9  # highest first
        assert profile.intervention_candidates[1].priority == 0.8

    def test_mastery_heatmap_averages_topic_scores(self):
        service = TeacherService()

        def tr(topic, score, level="LOW", factors=None):
            return TopicReadiness(
                topic=topic, readiness_score=score,
                risk_level=level, risk_factors=factors or [],
                review_status="current",
            )

        profiles = [
            _profile(
                overall_readiness=70.0,
                readiness_band="Ready",
                topic_readiness=[
                    tr("genetics", 80.0),
                    tr("ecology", 60.0),
                ],
            ),
            _profile(
                overall_readiness=50.0,
                readiness_band="Developing",
                topic_readiness=[
                    tr("genetics", 40.0, "HIGH", ["low_ability"]),
                    tr("ecology", 80.0),
                ],
            ),
        ]
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=2,
            profiles=profiles,
        )
        assert profile.mastery_heatmap["genetics"] == 60.0  # (80 + 40) / 2
        assert profile.mastery_heatmap["ecology"] == 70.0  # (60 + 80) / 2

    def test_empty_profile_on_no_students(self):
        service = TeacherService()
        profile = service._build_classroom_profile(
            classroom_id=uuid4(),
            student_count=0,
            profiles=[],
        )
        assert profile.classroom_health == 0.0
        assert profile.total_students == 0


class TestGetClassroomOverview:
    async def test_delegates_to_readiness_service(self):
        mock_readiness = MagicMock()
        mock_readiness.get_readiness = AsyncMock()
        mock_readiness.get_readiness.return_value = _profile(
            user_id=USER_ID,
            overall_readiness=70.0,
            readiness_band="Ready",
        )

        service = TeacherService(readiness_service=mock_readiness)
        mock_session = AsyncMock()

        result = await service._safe_fetch_readiness(mock_session, USER_ID)
        assert result is not None
        assert result.overall_readiness == 70.0

    async def test_safe_fetch_graceful_on_error(self):
        mock_readiness = MagicMock()
        mock_readiness.get_readiness = AsyncMock()
        mock_readiness.get_readiness.side_effect = ValueError("DB error")

        service = TeacherService(readiness_service=mock_readiness)
        result = await service._safe_fetch_readiness(
            AsyncMock(), uuid4()
        )
        assert result is None
