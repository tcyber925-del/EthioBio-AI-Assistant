from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.agents.spaced_repetition import (
    calculate_next_interval,
    generate_schedule,
    get_all_schedules,
    get_due_reviews,
    update_review,
)
from src.database.models import SpacedRepetitionSchedule, StudentMastery
from src.schemas.recovery import (
    DueReviewsResponse,
    SpacedRepetitionGenerateResponse,
    SpacedRepetitionItem,
    SpacedRepetitionReviewRequest,
    SpacedRepetitionReviewResponse,
    SpacedRepetitionScheduleResponse,
)


def test_calculate_next_interval_first_review():
    days, ef = calculate_next_interval(30.0, 0, 2.5, 0)
    assert days == 1
    assert ef == 2.5

    days, ef = calculate_next_interval(50.0, 0, 2.5, 0)
    assert days == 2

    days, ef = calculate_next_interval(70.0, 0, 2.5, 0)
    assert days == 3

    days, ef = calculate_next_interval(90.0, 0, 2.5, 0)
    assert days == 7


def test_calculate_next_interval_good_retention():
    days, ef = calculate_next_interval(85.0, 3, 2.5, 2)
    assert days >= 3
    assert ef == 2.6


def test_calculate_next_interval_acceptable_retention():
    days, ef = calculate_next_interval(70.0, 5, 2.5, 3)
    assert days == 5
    assert ef == 2.5


def test_calculate_next_interval_poor_retention():
    days, ef = calculate_next_interval(45.0, 7, 2.5, 4)
    assert days == 1
    assert ef == 2.3


def test_calculate_next_interval_ease_factor_floor():
    days, ef = calculate_next_interval(30.0, 10, 1.3, 5)
    assert ef >= 1.3
    assert days == 1


def test_calculate_next_interval_ease_factor_ceiling():
    days, ef = calculate_next_interval(95.0, 30, 3.0, 10)
    assert ef <= 3.0
    assert days >= 30


def _make_result(all_return=None, scalar_one_or_none_return=None):
    """Create a mock result object for async SQLAlchemy execute()."""
    mock = MagicMock()
    if all_return is not None:
        mock.scalars.return_value.all.return_value = all_return
    mock.scalar_one_or_none.return_value = scalar_one_or_none_return
    return mock


@pytest.mark.asyncio
async def test_generate_schedule_creates_new():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    mastery1 = MagicMock(spec=StudentMastery)
    mastery1.topic = "Cell Biology"
    mastery1.average_score = 45.0
    mastery1.grade_level = 10
    mastery1.unit = "Unit 2"
    mastery1.severity = "moderate"
    mastery1.confidence = 0.67
    mastery1.last_assessed_at = datetime.now(timezone.utc)

    session.execute = AsyncMock()
    session.execute.side_effect = [
        _make_result(all_return=[mastery1]),
        _make_result(scalar_one_or_none_return=None),
    ]

    result = await generate_schedule("test-user", session)
    assert len(result) == 1
    assert result[0]["topic"] == "Cell Biology"
    assert result[0]["interval_days"] == 2
    assert session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_generate_schedule_updates_existing():
    session = AsyncMock()

    mastery1 = MagicMock(spec=StudentMastery)
    mastery1.topic = "Cell Biology"
    mastery1.average_score = 65.0
    mastery1.grade_level = 10
    mastery1.unit = "Unit 2"
    mastery1.severity = "moderate"
    mastery1.confidence = 0.67
    mastery1.last_assessed_at = datetime.now(timezone.utc)

    existing = MagicMock(spec=SpacedRepetitionSchedule)
    existing.topic = "Cell Biology"
    existing.mastery_score = 45.0
    existing.interval_days = 2
    existing.ease_factor = 2.5
    existing.next_review_at = datetime.now(timezone.utc)
    existing.grade_level = 10
    existing.unit = "Unit 2"

    session.execute = AsyncMock()
    session.execute.side_effect = [
        _make_result(all_return=[mastery1]),
        _make_result(scalar_one_or_none_return=existing),
    ]

    result = await generate_schedule("test-user", session)
    assert len(result) == 1
    assert result[0]["topic"] == "Cell Biology"
    assert existing.mastery_score == 65.0
    assert session.commit.called


@pytest.mark.asyncio
async def test_generate_schedule_no_masteries():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result(all_return=[]))

    result = await generate_schedule("test-user", session)
    assert result == []


@pytest.mark.asyncio
async def test_get_due_reviews():
    session = AsyncMock()
    now = datetime.now(timezone.utc)

    due = MagicMock(spec=SpacedRepetitionSchedule)
    due.id = "id-1"
    due.topic = "Cell Biology"
    due.unit = "Unit 2"
    due.grade_level = 10
    due.mastery_score = 45.0
    due.interval_days = 2
    due.ease_factor = 2.5
    due.next_review_at = now - timedelta(days=1)
    due.last_reviewed_at = now - timedelta(days=3)
    due.review_count = 1

    session.execute = AsyncMock(return_value=_make_result(all_return=[due]))

    result = await get_due_reviews("test-user", session)
    assert len(result) == 1
    assert result[0]["topic"] == "Cell Biology"
    assert result[0]["days_overdue"] >= 1


@pytest.mark.asyncio
async def test_get_due_reviews_empty():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result(all_return=[]))

    result = await get_due_reviews("test-user", session)
    assert result == []


@pytest.mark.asyncio
async def test_get_all_schedules():
    session = AsyncMock()
    now = datetime.now(timezone.utc)

    item = MagicMock(spec=SpacedRepetitionSchedule)
    item.id = "id-1"
    item.topic = "Genetics"
    item.unit = "Unit 3"
    item.grade_level = 10
    item.mastery_score = 50.0
    item.interval_days = 2
    item.ease_factor = 2.5
    item.next_review_at = now + timedelta(days=1)
    item.last_reviewed_at = None
    item.review_count = 0

    session.execute = AsyncMock(return_value=_make_result(all_return=[item]))

    result = await get_all_schedules("test-user", session)
    assert len(result) == 1
    assert result[0]["topic"] == "Genetics"
    assert result[0]["is_due"] is False
    assert result[0]["days_overdue"] == 0


@pytest.mark.asyncio
async def test_update_review_good_score():
    session = AsyncMock()

    schedule = MagicMock(spec=SpacedRepetitionSchedule)
    schedule.review_count = 0
    schedule.interval_days = 2
    schedule.ease_factor = 2.5
    schedule.topic = "Cell Biology"

    session.execute = AsyncMock(return_value=_make_result(scalar_one_or_none_return=schedule))

    result = await update_review("test-user", "Cell Biology", 85.0, session)
    assert result is not None
    assert result["topic"] == "Cell Biology"
    assert result["review_count"] == 1
    assert result["ease_factor"] == 2.6
    assert schedule.last_reviewed_at is not None
    assert schedule.mastery_score == 85.0
    assert session.commit.called


@pytest.mark.asyncio
async def test_update_review_not_found():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result(scalar_one_or_none_return=None))

    result = await update_review("test-user", "Nonexistent", 85.0, session)
    assert result is None


def test_spaced_repetition_item_schema():
    now = datetime.now()
    item = SpacedRepetitionItem(
        id="00000000-0000-0000-0000-000000000001",
        topic="Cell Biology",
        mastery_score=45.0,
        interval_days=2,
        ease_factor=2.5,
        next_review_at=now,
        is_due=True,
        days_overdue=1,
    )
    assert item.topic == "Cell Biology"
    assert item.mastery_score == 45.0
    assert item.interval_days == 2
    assert item.is_due is True
    assert item.days_overdue == 1


def test_spaced_repetition_schedule_response_schema():
    now = datetime.now()
    item = SpacedRepetitionItem(
        id="00000000-0000-0000-0000-000000000001",
        topic="Genetics",
        mastery_score=50.0,
        interval_days=3,
        ease_factor=2.5,
        next_review_at=now,
    )
    resp = SpacedRepetitionScheduleResponse(
        user_id="00000000-0000-0000-0000-000000000002",
        total_items=1,
        items=[item],
    )
    assert resp.total_items == 1
    assert len(resp.items) == 1
    assert resp.items[0].topic == "Genetics"


def test_due_reviews_response_schema():
    now = datetime.now()
    item = SpacedRepetitionItem(
        id="00000000-0000-0000-0000-000000000001",
        topic="Cell Biology",
        mastery_score=45.0,
        interval_days=2,
        ease_factor=2.5,
        next_review_at=now,
        days_overdue=2,
    )
    resp = DueReviewsResponse(
        user_id="00000000-0000-0000-0000-000000000002",
        total_due=1,
        items=[item],
    )
    assert resp.total_due == 1
    assert resp.items[0].days_overdue == 2


def test_spaced_repetition_generate_response_schema():
    resp = SpacedRepetitionGenerateResponse(
        user_id="00000000-0000-0000-0000-000000000001",
        total_generated=2,
        items=[{"topic": "Cell Biology", "interval_days": 2}],
    )
    assert resp.total_generated == 2
    assert len(resp.items) == 1
    assert resp.items[0]["topic"] == "Cell Biology"


def test_spaced_repetition_review_request_schema():
    uid = UUID("00000000-0000-0000-0000-000000000001")
    req = SpacedRepetitionReviewRequest(
        user_id=uid,
        topic="Cell Biology",
        new_score=85.0,
    )
    assert req.user_id == uid
    assert req.topic == "Cell Biology"
    assert req.new_score == 85.0


def test_spaced_repetition_review_response_schema():
    now = datetime.now()
    resp = SpacedRepetitionReviewResponse(
        topic="Cell Biology",
        interval_days=7,
        ease_factor=2.6,
        next_review_at=now,
        review_count=2,
    )
    assert resp.topic == "Cell Biology"
    assert resp.interval_days == 7
    assert resp.ease_factor == 2.6
    assert resp.review_count == 2


def test_spaced_repetition_item_defaults():
    now = datetime.now()
    item = SpacedRepetitionItem(
        id="00000000-0000-0000-0000-000000000001",
        topic="Cell Biology",
        mastery_score=45.0,
        interval_days=2,
        ease_factor=2.5,
        next_review_at=now,
    )
    assert item.is_due is False
    assert item.days_overdue == 0
    assert item.review_count == 0
    assert item.last_reviewed_at is None


def test_spaced_repetition_schedule_no_items():
    resp = SpacedRepetitionScheduleResponse(
        user_id="00000000-0000-0000-0000-000000000001",
        total_items=0,
    )
    assert resp.items == []
