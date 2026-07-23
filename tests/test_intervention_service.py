from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.intervention.service import InterventionService
from src.core.learning_intelligence.readiness.models.intervention import Intervention
from src.schemas.intervention import InterventionCreate, InterventionUpdate


@pytest.fixture
def service():
    return InterventionService()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def make_assignment(**overrides):
    now = datetime.now(timezone.utc)
    attrs = {
        "id": uuid4(),
        "user_id": uuid4(),
        "classroom_id": None,
        "teacher_id": None,
        "intervention_type": "REVIEW_TOPIC",
        "topic": "Cell Biology",
        "status": "planned",
        "priority": 0.8,
        "estimated_impact": 60.0,
        "effectiveness_score": None,
        "notes": "Needs review",
        "assigned_at": now,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    attrs.update(overrides)
    return MagicMock(**attrs)


class TestInterventionServiceCreate:
    async def test_creates_with_initial_status(self, service, mock_session):
        data = InterventionCreate(
            user_id=uuid4(),
            intervention_type="REVIEW_TOPIC",
            topic="Cell Biology",
            priority=0.8,
            estimated_impact=60.0,
            notes="Needs review",
        )
        result = await service.create(data, mock_session)

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    async def test_passes_all_fields(self, service, mock_session):
        user_id = uuid4()
        data = InterventionCreate(
            user_id=user_id,
            intervention_type="TUTOR_SESSION",
            topic="Mitosis",
            priority=0.9,
            estimated_impact=85.0,
            notes="Urgent",
        )
        await service.create(data, mock_session)

        added_record = mock_session.add.call_args[0][0]
        assert added_record.user_id == user_id
        assert added_record.intervention_type == "TUTOR_SESSION"
        assert added_record.topic == "Mitosis"
        assert added_record.priority == 0.9
        assert added_record.estimated_impact == 85.0
        assert added_record.notes == "Urgent"


class TestInterventionServiceUpdate:
    async def test_status_active_sets_started_at(self, service, mock_session):
        record = make_assignment(status="planned", started_at=None)
        mock_session.get = AsyncMock(return_value=record)

        data = InterventionUpdate(status="active")
        result = await service.update(str(record.id), data, mock_session)

        assert result.status == "active"
        assert result.started_at is not None
        mock_session.flush.assert_awaited()

    async def test_status_completed_sets_completed_at(self, service, mock_session):
        record = make_assignment(status="active", completed_at=None)
        mock_session.get = AsyncMock(return_value=record)

        data = InterventionUpdate(status="completed")
        result = await service.update(str(record.id), data, mock_session)

        assert result.status == "completed"
        assert result.completed_at is not None

    async def test_effectiveness_score_auto_completes(self, service, mock_session):
        record = make_assignment(status="active", completed_at=None)
        mock_session.get = AsyncMock(return_value=record)

        data = InterventionUpdate(effectiveness_score=72.5)
        result = await service.update(str(record.id), data, mock_session)

        assert result.status == "completed"
        assert result.completed_at is not None
        assert result.effectiveness_score == 72.5

    async def test_status_cancelled(self, service, mock_session):
        record = make_assignment(status="planned")
        mock_session.get = AsyncMock(return_value=record)

        data = InterventionUpdate(status="cancelled")
        result = await service.update(str(record.id), data, mock_session)

        assert result.status == "cancelled"

    async def test_notes_updated(self, service, mock_session):
        record = make_assignment(notes="Old note")
        mock_session.get = AsyncMock(return_value=record)

        data = InterventionUpdate(notes="Updated note")
        result = await service.update(str(record.id), data, mock_session)

        assert result.notes == "Updated note"

    async def test_returns_none_for_missing_id(self, service, mock_session):
        mock_session.get = AsyncMock(return_value=None)

        data = InterventionUpdate(status="completed")
        result = await service.update("nonexistent", data, mock_session)

        assert result is None


class TestInterventionServiceGet:
    async def test_returns_record_when_found(self, service, mock_session):
        record = make_assignment()
        mock_session.get = AsyncMock(return_value=record)

        result = await service.get(str(record.id), mock_session)

        assert result is record

    async def test_returns_none_when_missing(self, service, mock_session):
        mock_session.get = AsyncMock(return_value=None)

        result = await service.get("nonexistent", mock_session)

        assert result is None


class TestInterventionServiceComputeEffectiveness:
    async def test_returns_none_when_record_missing(self, service, mock_session):
        mock_session.get = AsyncMock(return_value=None)

        result = await service.compute_effectiveness("nonexistent", mock_session)

        assert result is None

    async def test_returns_none_when_no_topic(self, service, mock_session):
        record = make_assignment(topic=None)
        mock_session.get = AsyncMock(return_value=record)

        result = await service.compute_effectiveness(str(record.id), mock_session)

        assert result is None

    async def _make_effectiveness_mocks(self, before_score, after_score, record):
        """Helper: set up execute mocks for weighted effectiveness computation."""
        before = MagicMock(average_score=before_score) if before_score is not None else None
        after = MagicMock(average_score=after_score) if after_score is not None else None

        mastery_before = MagicMock()
        mastery_before.scalar_one_or_none.return_value = before
        mastery_after = MagicMock()
        mastery_after.scalar_one_or_none.return_value = after

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        fetch_result = MagicMock()
        fetch_result.fetchone.return_value = MagicMock(before_stab=None, after_stab=None)
        scalar_result = MagicMock()
        scalar_result.scalar.return_value = None

        confidence_row = MagicMock()
        confidence_row.one_or_none.return_value = (0, None, None)

        from unittest.mock import AsyncMock

        # ensure we have enough slots for all execute calls from helpers + kb store
        catch_all = MagicMock()
        catch_all.scalar_one_or_none.return_value = None
        catch_all.scalar.return_value = None
        catch_all.fetchone.return_value = None
        catch_all.one_or_none.return_value = None

        mock_exec = AsyncMock()
        mock_exec.side_effect = [
            mastery_before,  # _get_mastery_change: before
            mastery_after,  # _get_mastery_change: after
            scalar_result,  # _get_readiness_change: before (wrapped, fails -> 0.0)
            scalar_result,  # _get_readiness_change: after (wrapped, fails -> 0.0)
            fetch_result,  # _get_retention_change: stability (wrapped, fails -> 0.0)
            count_result,  # _get_misconception_reduction: before_count
            count_result,  # _get_misconception_reduction: after_count
            *([catch_all] * 10),  # kb store + confidence + any extras
        ]
        return mock_exec

    async def test_computes_positive_gain(self, service, mock_session):
        record = make_assignment(topic="Cell Biology")
        mock_session.get = AsyncMock(return_value=record)
        mock_session.execute = await self._make_effectiveness_mocks(40.0, 75.0, record)

        score = await service.compute_effectiveness(str(record.id), mock_session)

        assert score == pytest.approx(35.0 * 0.35, rel=0.01)
        assert record.effectiveness_score is not None
        assert record.status == "completed"
        assert record.completed_at is not None

    async def test_clamps_score_to_100(self, service, mock_session):
        record = make_assignment(topic="Genetics")
        mock_session.get = AsyncMock(return_value=record)
        mock_session.execute = await self._make_effectiveness_mocks(10.0, 200.0, record)

        score = await service.compute_effectiveness(str(record.id), mock_session)

        assert score <= 100.0

    async def test_clamps_score_to_zero(self, service, mock_session):
        record = make_assignment(topic="Physics")
        mock_session.get = AsyncMock(return_value=record)
        mock_session.execute = await self._make_effectiveness_mocks(80.0, 30.0, record)

        score = await service.compute_effectiveness(str(record.id), mock_session)

        assert score == 0.0

    async def test_returns_none_when_no_before_record(self, service, mock_session):
        record = make_assignment(topic="Chemistry")
        mock_session.get = AsyncMock(return_value=record)
        mock_session.execute = await self._make_effectiveness_mocks(None, 90.0, record)

        score = await service.compute_effectiveness(str(record.id), mock_session)

        assert score is None

    async def test_returns_none_when_no_after_record(self, service, mock_session):
        record = make_assignment(topic="Biology")
        mock_session.get = AsyncMock(return_value=record)
        mock_session.execute = await self._make_effectiveness_mocks(50.0, None, record)

        score = await service.compute_effectiveness(str(record.id), mock_session)

        assert score is None


class TestInterventionServicePersistPlanned:
    async def test_creates_records_from_intervention_objects(self, service, mock_session):
        user_id = uuid4()
        interventions = [
            Intervention(
                topic="Cell Biology",
                priority=0.8,
                action_type="REVIEW_TOPIC",
                estimated_impact=60.0,
                reason="Low mastery score",
            ),
            Intervention(
                topic="Genetics",
                priority=0.6,
                action_type="TAKE_QUIZ",
                estimated_impact=40.0,
                reason="Needs practice",
            ),
        ]

        results = await service.persist_planned(interventions, user_id, mock_session)

        assert len(results) == 2
        assert mock_session.add.call_count == 2
        mock_session.flush.assert_awaited_once()

    async def test_sets_fields_correctly(self, service, mock_session):
        user_id = uuid4()
        interventions = [
            Intervention(
                topic="Mitosis",
                priority=0.9,
                action_type="TUTOR_SESSION",
                estimated_impact=80.0,
                reason="Struggling with cell division",
            ),
        ]

        await service.persist_planned(interventions, user_id, mock_session)

        added = mock_session.add.call_args[0][0]
        assert added.user_id == user_id
        assert added.intervention_type == "TUTOR_SESSION"
        assert added.topic == "Mitosis"
        assert added.priority == 0.9
        assert added.estimated_impact == 80.0
        assert added.notes == "Struggling with cell division"

    async def test_empty_list_returns_empty(self, service, mock_session):
        results = await service.persist_planned([], uuid4(), mock_session)

        assert results == []
        mock_session.add.assert_not_called()


class TestInterventionServiceGetAnalytics:
    async def test_returns_zero_for_no_records(self, service, mock_session):
        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_proxy)

        result = await service.get_analytics(mock_session)

        assert result["total_interventions"] == 0
        assert result["completed_count"] == 0
        assert result["active_count"] == 0
        assert result["completion_rate"] == 0.0
        assert result["average_effectiveness"] == 0.0

    async def test_computes_correct_aggregations(self, service, mock_session):
        r1 = make_assignment(
            status="completed",
            intervention_type="REVIEW_TOPIC",
            topic="Bio",
            effectiveness_score=70.0,
        )
        r2 = make_assignment(
            status="completed",
            intervention_type="REVIEW_TOPIC",
            topic="Bio",
            effectiveness_score=90.0,
        )
        r3 = make_assignment(status="active", intervention_type="TAKE_QUIZ")
        r4 = make_assignment(status="planned", intervention_type="TUTOR_SESSION")
        records = [r1, r2, r3, r4]
        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=result_proxy)

        result = await service.get_analytics(mock_session)

        assert result["total_interventions"] == 4
        assert result["completed_count"] == 2
        assert result["active_count"] == 1
        assert result["completion_rate"] == 50.0
        assert result["average_effectiveness"] == 80.0

    async def test_effectiveness_by_type_and_topic(self, service, mock_session):
        r1 = make_assignment(
            status="completed",
            intervention_type="REVIEW_TOPIC",
            topic="Bio",
            effectiveness_score=70.0,
        )
        r2 = make_assignment(
            status="completed",
            intervention_type="REVIEW_TOPIC",
            topic="Genetics",
            effectiveness_score=90.0,
        )
        r3 = make_assignment(
            status="completed",
            intervention_type="TAKE_QUIZ",
            topic="Bio",
            effectiveness_score=80.0,
        )
        records = [r1, r2, r3]
        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = records
        mock_session.execute = AsyncMock(return_value=result_proxy)

        result = await service.get_analytics(mock_session)

        assert result["effectiveness_by_type"]["REVIEW_TOPIC"] == 80.0
        assert result["effectiveness_by_type"]["TAKE_QUIZ"] == 80.0
        assert result["effectiveness_by_topic"]["Bio"] == 75.0
        assert result["effectiveness_by_topic"]["Genetics"] == 90.0

    async def test_filters_by_user_id(self, service, mock_session):
        user_id = uuid4()
        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_proxy)

        await service.get_analytics(mock_session, user_id=user_id)

        call_stmt = mock_session.execute.call_args[0][0]
        param = call_stmt.whereclause.right.value
        assert param == user_id
