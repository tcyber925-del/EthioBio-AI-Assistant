from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.core.learning_intelligence.readiness.models.readiness_profile import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.school.school_service import SchoolService
from src.database.models import ClassGroup, School

USER_ID = uuid4()
TEACHER_ID = uuid4()
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


def _class_group(
    class_id: UUID | None = None,
    name: str = "Class A",
    teacher_id: UUID | None = None,
    students: list | None = None,
) -> ClassGroup:
    cg = MagicMock(spec=ClassGroup)
    cg.id = class_id or uuid4()
    cg.name = name
    cg.teacher_id = teacher_id or TEACHER_ID
    cg.students = students or []
    return cg


def _school(school_id: UUID | None = None, class_groups: list | None = None) -> School:
    s = MagicMock(spec=School)
    s.id = school_id or uuid4()
    s.name = "Test School"
    s.class_groups = class_groups or []
    return s


class TestBuildSchoolProfile:
    def test_empty_classes_returns_empty(self):
        service = SchoolService()
        school = _school()
        profile = service._build_school_profile(school, [])
        assert profile.total_students == 0
        assert profile.total_classrooms == 0
        assert profile.total_teachers == 0

    def test_empty_removed_from_input(self):
        service = SchoolService()
        school = _school()
        profile = service._build_school_profile(school, [])
        assert profile.total_students == 0
        assert profile.avg_health == 0.0

    def test_averages_across_all_classes(self):
        service = SchoolService()
        school = _school()
        cg = _class_group(students=[MagicMock() for _ in range(2)])
        profiles = [
            _profile(overall_readiness=80.0, readiness_band="Strong"),
            _profile(overall_readiness=60.0, readiness_band="Ready"),
        ]
        profile = service._build_school_profile(school, [(cg, profiles)])
        assert profile.avg_health == 70.0

    def test_health_distribution_counts_bands(self):
        service = SchoolService()
        school = _school()
        cg = _class_group(students=[MagicMock() for _ in range(5)])
        profiles = [
            _profile(overall_readiness=85.0, readiness_band="Strong"),
            _profile(overall_readiness=75.0, readiness_band="Ready"),
            _profile(overall_readiness=75.0, readiness_band="Ready"),
            _profile(overall_readiness=45.0, readiness_band="Developing"),
            _profile(overall_readiness=20.0, readiness_band="Critical"),
        ]
        profile = service._build_school_profile(school, [(cg, profiles)])
        assert profile.health_distribution == {
            "Strong": 1,
            "Ready": 2,
            "Developing": 1,
            "Critical": 1,
        }
        assert profile.total_students == 5

    def test_teacher_metrics_per_teacher(self):
        service = SchoolService()
        school = _school()
        tid1 = uuid4()
        tid2 = uuid4()
        cg1 = _class_group(teacher_id=tid1, students=[MagicMock()])
        cg2 = _class_group(teacher_id=tid1, students=[MagicMock()])
        cg3 = _class_group(teacher_id=tid2, students=[MagicMock()])
        p1 = _profile(overall_readiness=70.0)
        p2 = _profile(overall_readiness=50.0)
        p3 = _profile(overall_readiness=90.0)
        profile = service._build_school_profile(
            school,
            [
                (cg1, [p1]),
                (cg2, [p2]),
                (cg3, [p3]),
            ],
        )
        assert profile.total_teachers == 2
        tm1 = [m for m in profile.teacher_metrics if m.teacher_id == tid1][0]
        assert tm1.classroom_count == 2
        assert tm1.avg_student_readiness == 60.0

    def test_at_risk_classrooms_flagged(self):
        service = SchoolService()
        school = _school()
        cg_low = _class_group(name="Low", students=[MagicMock()])
        cg_high = _class_group(name="High", students=[MagicMock()])
        low_profiles = [_profile(overall_readiness=30.0, readiness_band="Critical")]
        high_profiles = [_profile(overall_readiness=85.0, readiness_band="Strong")]
        profile = service._build_school_profile(
            school,
            [
                (cg_low, low_profiles),
                (cg_high, high_profiles),
            ],
        )
        assert len(profile.at_risk_classrooms) == 1
        assert profile.at_risk_classrooms[0]["name"] == "Low"

    def test_no_students_returns_zero_health(self):
        service = SchoolService()
        school = _school()
        cg = _class_group(students=[])
        profile = service._build_school_profile(school, [(cg, [])])
        assert profile.avg_health == 0.0
        assert profile.total_students == 0


class TestSafeFetch:
    async def test_safe_fetch_returns_readiness(self):
        mock_readiness = MagicMock()
        mock_readiness.get_readiness = AsyncMock()
        mock_readiness.get_readiness.return_value = _profile(user_id=USER_ID)

        service = SchoolService(readiness_service=mock_readiness)
        result = await service._safe_fetch_readiness(AsyncMock(), USER_ID)
        assert result is not None
        assert result.overall_readiness == 70.0

    async def test_safe_fetch_graceful_on_error(self):
        mock_readiness = MagicMock()
        mock_readiness.get_readiness = AsyncMock()
        mock_readiness.get_readiness.side_effect = ValueError("DB error")

        service = SchoolService(readiness_service=mock_readiness)
        result = await service._safe_fetch_readiness(AsyncMock(), uuid4())
        assert result is None


class TestEmptyProfile:
    def test_empty_profile_returns_defaults(self):
        service = SchoolService()
        profile = service._empty_profile(school_id=uuid4())
        assert profile.total_students == 0
        assert profile.total_teachers == 0
        assert profile.total_classrooms == 0
        assert profile.avg_health == 0.0
        assert profile.at_risk_classrooms == []
        assert profile.teacher_metrics == []
