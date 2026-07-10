from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.weak_topic_detection import (
    calculate_confidence,
    calculate_severity,
    get_weak_topics,
    record_mastery_history,
)
from src.schemas.recovery import (
    MisconceptionInfo,
    WeakTopicDetail,
    WeakTopicsResponse,
)


def test_calculate_severity_critical():
    assert calculate_severity(30) == "critical"
    assert calculate_severity(0) == "critical"
    assert calculate_severity(39.9) == "critical"


def test_calculate_severity_moderate():
    assert calculate_severity(40) == "moderate"
    assert calculate_severity(50) == "moderate"
    assert calculate_severity(59.9) == "moderate"


def test_calculate_severity_mild():
    assert calculate_severity(60) == "mild"
    assert calculate_severity(70) == "mild"
    assert calculate_severity(79.9) == "mild"


def test_calculate_severity_good():
    assert calculate_severity(80) == "good"
    assert calculate_severity(95) == "good"
    assert calculate_severity(100) == "good"


def test_calculate_confidence():
    assert calculate_confidence(0) == 0.0
    assert calculate_confidence(1) == pytest.approx(0.333, 0.01)
    assert calculate_confidence(3) == 1.0
    assert calculate_confidence(10) == 1.0


def test_misconception_info_schema():
    info = MisconceptionInfo(
        pattern_type="wrong_answer",
        description="Student answers 'mitosis' instead of 'meiosis'",
        frequency=3,
    )
    assert info.pattern_type == "wrong_answer"
    assert info.frequency == 3


def test_weak_topic_detail_schema():
    detail = WeakTopicDetail(
        topic="Cell Biology",
        unit="Unit 3",
        grade_level=10,
        average_score=45.0,
        attempt_count=2,
        severity="moderate",
        confidence=0.67,
    )
    assert detail.topic == "Cell Biology"
    assert detail.severity == "moderate"
    assert detail.average_score == 45.0
    assert detail.confidence == 0.67
    assert detail.misconceptions == []


def test_weak_topic_detail_with_misconceptions():
    misc = MisconceptionInfo(
        pattern_type="wrong_answer",
        description="Common error",
        frequency=2,
    )
    detail = WeakTopicDetail(
        topic="Genetics",
        grade_level=11,
        average_score=35.0,
        severity="critical",
        misconceptions=[misc],
    )
    assert len(detail.misconceptions) == 1
    assert detail.misconceptions[0].description == "Common error"


def test_weak_topics_response_schema():
    from uuid import UUID

    detail = WeakTopicDetail(
        topic="Cell Biology",
        grade_level=10,
        average_score=45.0,
        severity="moderate",
    )
    uid = UUID("00000000-0000-0000-0000-000000000001")
    resp = WeakTopicsResponse(
        user_id=uid,
        weak_topics=[detail],
        total_weak_topics=1,
    )
    assert resp.user_id == uid
    assert resp.total_weak_topics == 1
    assert len(resp.weak_topics) == 1


def test_weak_topics_response_empty():
    resp = WeakTopicsResponse(
        user_id="00000000-0000-0000-0000-000000000001",
    )
    assert resp.total_weak_topics == 0
    assert resp.weak_topics == []


@pytest.mark.asyncio
async def test_get_weak_topics_returns_filtered():
    mock_session = AsyncMock()

    mock_mastery_1 = MagicMock()
    mock_mastery_1.topic = "Genetics"
    mock_mastery_1.unit = "Unit 4"
    mock_mastery_1.grade_level = 10
    mock_mastery_1.average_score = 35.0
    mock_mastery_1.attempt_count = 3
    mock_mastery_1.severity = "critical"
    mock_mastery_1.confidence = 1.0
    mock_mastery_1.last_assessed_at = None

    mock_mastery_2 = MagicMock()
    mock_mastery_2.topic = "Cell Biology"
    mock_mastery_2.unit = "Unit 3"
    mock_mastery_2.grade_level = 10
    mock_mastery_2.average_score = 55.0
    mock_mastery_2.attempt_count = 2
    mock_mastery_2.severity = "moderate"
    mock_mastery_2.confidence = 0.67
    mock_mastery_2.last_assessed_at = None

    mock_mastery_3 = MagicMock()
    mock_mastery_3.topic = "Ecology"
    mock_mastery_3.unit = "Unit 5"
    mock_mastery_3.grade_level = 10
    mock_mastery_3.average_score = 90.0
    mock_mastery_3.attempt_count = 4
    mock_mastery_3.severity = "good"
    mock_mastery_3.confidence = 1.0
    mock_mastery_3.last_assessed_at = None

    mock_mis_1 = MagicMock()
    mock_mis_1.topic = "Genetics"
    mock_mis_1.pattern_type = "wrong_answer"
    mock_mis_1.pattern_description = "Student answers 'dominant' instead of 'recessive'"
    mock_mis_1.frequency = 3

    mastery_result = MagicMock()
    mastery_result.scalars.return_value.all.return_value = [
        mock_mastery_1,
        mock_mastery_2,
        mock_mastery_3,
    ]

    mis_result = MagicMock()
    mis_result.scalars.return_value.all.return_value = [mock_mis_1]

    mock_session.execute = AsyncMock(side_effect=[mastery_result, mis_result])

    result = await get_weak_topics("test-user-id", mock_session)

    assert len(result) == 2
    assert result[0]["topic"] == "Genetics"
    assert result[0]["severity"] == "critical"
    assert result[0]["average_score"] == 35.0
    assert result[1]["topic"] == "Cell Biology"
    assert result[1]["severity"] == "moderate"

    assert len(result[0]["misconceptions"]) == 1
    assert result[0]["misconceptions"][0]["pattern_type"] == "wrong_answer"
    assert result[0]["misconceptions"][0]["frequency"] == 3


@pytest.mark.asyncio
async def test_get_weak_topics_empty():
    mock_session = AsyncMock()

    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(return_value=empty_result)

    result = await get_weak_topics("test-user-id", mock_session)
    assert result == []


@pytest.mark.asyncio
async def test_get_weak_topics_all_good():
    mock_session = AsyncMock()

    mock_mastery = MagicMock()
    mock_mastery.topic = "Ecology"
    mock_mastery.unit = "Unit 5"
    mock_mastery.grade_level = 10
    mock_mastery.average_score = 95.0
    mock_mastery.attempt_count = 5
    mock_mastery.severity = "good"
    mock_mastery.confidence = 1.0
    mock_mastery.last_assessed_at = None

    mastery_result = MagicMock()
    mastery_result.scalars.return_value.all.return_value = [mock_mastery]

    mis_result = MagicMock()
    mis_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mastery_result, mis_result])

    result = await get_weak_topics("test-user-id", mock_session)
    assert result == []


@pytest.mark.asyncio
async def test_record_mastery_history_creates_entry():
    mock_session = AsyncMock()

    mock_mastery = MagicMock()
    mock_mastery.topic = "Cell Biology"
    mock_mastery.unit = "Unit 3"
    mock_mastery.grade_level = 10
    mock_mastery.average_score = 65.0
    mock_mastery.attempt_count = 2
    mock_mastery.severity = "moderate"
    mock_mastery.confidence = 0.67
    mock_mastery.last_assessed_at = None

    mastery_result = MagicMock()
    mastery_result.scalar_one_or_none.return_value = mock_mastery
    mock_session.execute = AsyncMock(return_value=mastery_result)

    await record_mastery_history(
        user_id="test-user-id",
        topic="Cell Biology",
        unit="Unit 3",
        grade_level=10,
        session=mock_session,
        source="task_completion",
        source_id="test-task-id",
    )

    assert mock_session.add.called
    added = mock_session.add.call_args[0][0]
    assert added.topic == "Cell Biology"
    assert added.source == "task_completion"
    assert added.source_id == "test-task-id"
    assert added.average_score == 65.0


@pytest.mark.asyncio
async def test_record_mastery_history_no_mastery():
    mock_session = AsyncMock()

    mastery_result = MagicMock()
    mastery_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mastery_result)

    await record_mastery_history(
        user_id="test-user-id",
        topic="Unknown Topic",
        unit=None,
        grade_level=0,
        session=mock_session,
    )

    assert not mock_session.add.called
