"""Tests for EventLogger schema validation and subscriber registry."""

from uuid import uuid4

import pytest

from src.core.memory.event_logger import (
    SCHEMA_REGISTRY,
    EventLogger,
    EventValidationError,
)


@pytest.fixture
def logger():
    return EventLogger()


def test_schema_registry_has_known_types():
    expected = {
        "session_started",
        "quiz_completed",
        "lesson_viewed",
        "recovery_task_done",
        "misconception_detected",
        "xp_awarded",
        "streak_updated",
        "achievement_unlocked",
    }
    assert set(SCHEMA_REGISTRY) == expected


def test_schema_registry_entries_have_required_keys():
    for event_type, schema in SCHEMA_REGISTRY.items():
        assert "required_fields" in schema, f"{event_type} missing required_fields"
        assert "optional_fields" in schema, f"{event_type} missing optional_fields"
        assert "metadata_schema" in schema, f"{event_type} missing metadata_schema"


def test_validate_passes_with_required_fields(logger):
    meta = {"score": 85, "total_questions": 10}
    # Should not raise
    logger._validate("quiz_completed", meta)


def test_validate_raises_on_missing_required(logger):
    with pytest.raises(EventValidationError, match="missing required field.*score"):
        logger._validate("quiz_completed", {"total_questions": 10})


def test_validate_raises_on_wrong_type(logger):
    with pytest.raises(EventValidationError, match="expected.*int.*got.*str"):
        logger._validate("quiz_completed", {"score": "eighty", "total_questions": 10})


def test_validate_accepts_float_for_int_field(logger):
    # score accepts (int, float)
    logger._validate("xp_awarded", {"amount": 50.5, "source": "quiz"})


def test_validate_unknown_type_does_not_raise(logger):
    logger._validate("unknown_event_type", {"anything": "goes"})


def test_subscribe_receives_events(logger):
    received = []

    def handler(event_type, user_id, metadata, event_id):
        received.append((event_type, user_id, metadata, event_id))

    logger.subscribe("quiz_completed", handler)
    assert len(logger._subscribers["quiz_completed"]) == 1


def test_subscribe_all_registers_for_all_types(logger):
    calls = []

    def handler(event_type, user_id, metadata, event_id):
        calls.append(event_type)

    logger.subscribe_all(handler)
    assert len(calls) == 0
    assert len(logger._subscribers) == len(SCHEMA_REGISTRY)


@pytest.mark.asyncio
async def test_notify_dispatches_to_subscribers(logger):
    received = []

    def handler(event_type, user_id, metadata, event_id):
        received.append((event_type, str(user_id), metadata, event_id))

    uid = uuid4()
    eid = uuid4()

    logger.subscribe("session_started", handler)
    await logger._notify("session_started", uid, {"mode": "tutor"}, eid)

    assert len(received) == 1
    assert received[0][0] == "session_started"
    assert received[0][1] == str(uid)


@pytest.mark.asyncio
async def test_notify_async_handler(logger):
    received = []

    async def handler(event_type, user_id, metadata, event_id):
        received.append(event_type)

    logger.subscribe("xp_awarded", handler)
    await logger._notify("xp_awarded", uuid4(), {"amount": 10, "source": "quiz"}, uuid4())

    assert received == ["xp_awarded"]


@pytest.mark.asyncio
async def test_subscriber_error_does_not_block(logger):
    """An error in one subscriber should not affect others."""

    def failing(event_type, user_id, metadata, event_id):
        raise RuntimeError("boom")

    ok_calls = []

    def ok(event_type, user_id, metadata, event_id):
        ok_calls.append(event_type)

    logger.subscribe("session_started", failing)
    logger.subscribe("session_started", ok)

    await logger._notify("session_started", uuid4(), {}, uuid4())

    assert ok_calls == ["session_started"]
