import pytest

from src.core.memory.event_logger import (
    SCHEMA_REGISTRY,
    EventSchema,
    EventValidationError,
)


class TestEventSchema:
    def test_validates_required_fields(self):
        schema = EventSchema(
            event_type="test_event",
            required_fields=["score", "user_id"],
        )
        result = schema.validate({"score": 85, "user_id": "abc"})
        assert result["score"] == 85

    def test_raises_on_missing_required_field(self):
        schema = EventSchema(
            event_type="test_event",
            required_fields=["score", "user_id"],
        )
        with pytest.raises(EventValidationError, match="missing required field.*score"):
            schema.validate({"user_id": "abc"})

    def test_validates_typed_metadata(self):
        schema = EventSchema(
            event_type="scored_event",
            metadata_schema={"score": int, "name": str},
        )
        result = schema.validate({"score": 90, "name": "test", "extra": "ignored"})
        assert result["score"] == 90

    def test_raises_on_type_mismatch(self):
        schema = EventSchema(
            event_type="scored_event",
            metadata_schema={"score": int},
        )
        with pytest.raises(EventValidationError, match="expected int, got str"):
            schema.validate({"score": "ninety"})

    def test_accepts_empty_metadata(self):
        schema = EventSchema(event_type="empty_event")
        result = schema.validate(None)
        assert result == {}

    def test_accepts_union_types(self):
        schema = EventSchema(
            event_type="flexible",
            metadata_schema={"score": (int, float)},
        )
        assert schema.validate({"score": 85})["score"] == 85
        assert schema.validate({"score": 85.5})["score"] == 85.5


class TestSchemaRegistry:
    def test_quiz_completed_requires_score_and_total(self):
        schema = SCHEMA_REGISTRY["quiz_completed"]
        with pytest.raises(EventValidationError, match="missing required field.*score"):
            schema.validate({"total": 10})
        result = schema.validate({"score": 8, "total": 10})
        assert result["score"] == 8

    def test_session_started_requires_tutoring_mode(self):
        schema = SCHEMA_REGISTRY["session_started"]
        with pytest.raises(EventValidationError):
            schema.validate({})
        result = schema.validate({"tutoring_mode": "socratic"})
        assert result["tutoring_mode"] == "socratic"

    def test_achievement_unlocked_requires_ids(self):
        schema = SCHEMA_REGISTRY["achievement_unlocked"]
        with pytest.raises(EventValidationError):
            schema.validate({})
        result = schema.validate({"achievement_id": "ach_1", "title": "First Quiz"})
        assert result["title"] == "First Quiz"

    def test_xp_awarded_rejects_string_amount(self):
        schema = SCHEMA_REGISTRY["xp_awarded"]
        with pytest.raises(EventValidationError, match="expected int"):
            schema.validate({"amount": "100", "source": "quiz"})

    def test_all_registered_types_have_descriptions(self):
        for event_type, schema in SCHEMA_REGISTRY.items():
            assert schema.description, f"{event_type} missing description"
            assert schema.event_type == event_type
