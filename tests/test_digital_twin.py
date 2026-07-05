from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.digital_twin.builder import TwinBuilder, _compute_confidence
from src.database.models import (
    MemoryEducationalSummary,
    MemoryEvent,
    SpacedRepetitionSchedule,
    StudentAbility,
    StudentDigitalTwin,
    TopicMasteryHistory,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    execute_result.scalars.return_value.all.return_value = []
    session.execute.return_value = execute_result
    session.get.return_value = None
    return session


class TestTwinBuilder:
    @pytest.mark.asyncio
    async def test_rebuild_creates_new_twin(self, mock_session):
        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(uuid4())
        assert isinstance(twin, StudentDigitalTwin)

    @pytest.mark.asyncio
    async def test_rebuild_updates_existing_twin(self, mock_session):
        user_id = uuid4()
        existing = StudentDigitalTwin(user_id=user_id, overall_health="healthy")
        mock_session.get.return_value = existing

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        assert twin.user_id == user_id
        assert twin.overall_health == "critical"

    @pytest.mark.asyncio
    async def test_rebuild_with_ability_data(self, mock_session):
        user_id = uuid4()
        ability = MagicMock(spec=StudentAbility)
        ability.topic = "Cell Biology"
        ability.ability_score = 0.75
        ability.attempt_count = 5

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        ability_q = MagicMock()
        ability_q.scalars.return_value.all.return_value = [ability]

        mock_session.execute.side_effect = [ability_q, empty, empty, empty, empty, empty]

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        knowledge = twin.knowledge_state or {}
        assert knowledge.get("overall") == 0.75
        assert "Cell Biology" in knowledge.get("topics", {})

    @pytest.mark.asyncio
    async def test_rebuild_with_mastery_data(self, mock_session):
        user_id = uuid4()
        mastery = MagicMock(spec=TopicMasteryHistory)
        mastery.topic = "Genetics"
        mastery.average_score = 0.85
        mastery.recorded_at = datetime.now(timezone.utc)

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        mastery_q = MagicMock()
        mastery_q.scalars.return_value.all.return_value = [mastery]

        mock_session.execute.side_effect = [
            empty,       # _build_knowledge
            mastery_q,   # _build_mastery
            empty,       # _build_misconceptions
            empty,       # _build_retention
            empty,       # _build_readiness
            empty,       # _build_intervention
        ]

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        mastery_state = twin.mastery_state or {}
        assert mastery_state.get("overall") == 0.85

    @pytest.mark.asyncio
    async def test_build_retention_without_dates(self, mock_session):
        user_id = uuid4()
        srs = MagicMock(spec=SpacedRepetitionSchedule)
        srs.topic = "Cell Biology"
        srs.mastery_score = 0.9
        srs.interval_days = 7
        srs.review_count = 10
        srs.last_reviewed_at = None

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        retention_q = MagicMock()
        retention_q.scalars.return_value.all.return_value = [srs]

        mock_session.execute.side_effect = [
            empty,        # _build_knowledge
            empty,        # _build_mastery
            empty,        # _build_misconceptions
            retention_q,  # _build_retention
            empty,        # _build_readiness
            empty,        # _build_intervention
        ]

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        retention = twin.retention_state or {}
        topics = retention.get("topics", {})
        assert "Cell Biology" in topics
        assert topics["Cell Biology"]["forgetting_risk"] == "high"

    @pytest.mark.asyncio
    async def test_build_misconceptions(self, mock_session):
        user_id = uuid4()
        summary = MagicMock(spec=MemoryEducationalSummary)
        summary.topic = "Photosynthesis"
        summary.key_misconceptions = [
            {"topic": "Photosynthesis", "pattern": "Thinks plants eat soil"}
        ]
        summary.created_at = datetime.now(timezone.utc)

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        mc_q = MagicMock()
        mc_q.scalars.return_value.all.return_value = [summary]

        mock_session.execute.side_effect = [
            empty,  # _build_knowledge
            empty,  # _build_mastery
            mc_q,   # _build_misconceptions
            empty,  # _build_retention
            empty,  # _build_readiness
            empty,  # _build_intervention
        ]

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        mc = twin.misconception_state or {}
        assert mc.get("total_active", 0) >= 1

    @pytest.mark.asyncio
    async def test_build_intervention_counts(self, mock_session):
        user_id = uuid4()
        event = MagicMock(spec=MemoryEvent)
        event.event_type = "intervention"
        event.event_metadata = {"status": "completed"}

        empty = MagicMock()
        empty.scalars.return_value.all.return_value = []

        ev_q = MagicMock()
        ev_q.scalars.return_value.all.return_value = [event]

        mock_session.execute.side_effect = [
            empty,  # _build_knowledge
            empty,  # _build_mastery
            empty,  # _build_misconceptions
            empty,  # _build_retention
            empty,  # _build_readiness
            ev_q,   # _build_intervention
        ]

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)
        intervention = twin.intervention_state or {}
        assert intervention.get("completed_count", 0) == 1

    def test_compute_confidence_all_populated(self):
        dims = [
            {"overall": 0.8, "topics": {"Bio": 0.8}},
            {"overall": 0.9, "topics": {"Bio": 0.9}},
            {"total_active": 2, "topics": {"Bio": ["confuses mitosis and meiosis"]}},
            {"overall": 0.7, "topics": {"Bio": 0.7}},
            {"overall": 0.6, "topics": {"Bio": 0.6}},
            {"active_count": 1, "completed_count": 2, "total": 3},
        ]
        result = _compute_confidence(dims)
        assert isinstance(result, float)
        assert result > 0.0

    def test_compute_confidence_empty(self):
        assert _compute_confidence([]) == 0.0
        assert _compute_confidence([None, None]) == 0.0

    @pytest.mark.asyncio
    async def test_rebuild_populates_all_dimensions(self, mock_session):
        user_id = uuid4()
        ability = MagicMock(spec=StudentAbility)
        ability.topic = "Bio"
        ability.ability_score = 0.8
        ability.attempt_count = 3

        mastery = MagicMock(spec=TopicMasteryHistory)
        mastery.topic = "Bio"
        mastery.average_score = 0.85
        mastery.recorded_at = datetime.now(timezone.utc)

        srs = MagicMock(spec=SpacedRepetitionSchedule)
        srs.topic = "Bio"
        srs.mastery_score = 0.9
        srs.interval_days = 7
        srs.review_count = 3
        srs.last_reviewed_at = datetime.now(timezone.utc)

        summary = MagicMock(spec=MemoryEducationalSummary)
        summary.topic = "Bio"
        summary.key_misconceptions = [{"topic": "Bio", "pattern": "confuses mitosis and meiosis"}]
        summary.created_at = datetime.now(timezone.utc)

        event = MagicMock(spec=MemoryEvent)
        event.event_type = "intervention"
        event.event_metadata = {"status": "completed"}
        event.created_at = datetime.now(timezone.utc)

        calls = [
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [ability]),
            ),
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [mastery]),
            ),
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [summary]),
            ),
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [srs]),
            ),
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [ability]),
            ),
            MagicMock(
                scalars=lambda *a, **kw: MagicMock(all=lambda: [event]),
            ),
        ]
        mock_session.execute.side_effect = calls

        builder = TwinBuilder(mock_session)
        twin = await builder.rebuild(user_id)

        assert twin.knowledge_state
        assert twin.mastery_state
        assert twin.misconception_state is not None
        assert twin.retention_state
        assert twin.readiness_state
        assert twin.intervention_state is not None
        assert twin.overall_health == "healthy"
        assert twin.confidence > 0.0
