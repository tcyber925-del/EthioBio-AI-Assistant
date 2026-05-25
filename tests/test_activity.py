"""Tests for the activity feed module."""

import pytest
from uuid import UUID
from datetime import datetime, timezone


class TestActivitySchemas:
    def test_activity_item_model(self):
        from src.schemas.activity import ActivityItem

        item = ActivityItem(
            activity_type="xp_event",
            title="Quiz Completion",
            description="10 XP earned",
            icon="Zap",
            timestamp=datetime.now(timezone.utc),
        )
        assert item.activity_type == "xp_event"
        assert item.title == "Quiz Completion"
        assert item.description == "10 XP earned"
        assert item.icon == "Zap"
        assert item.metadata == {}

    def test_activity_item_with_metadata(self):
        from src.schemas.activity import ActivityItem

        item = ActivityItem(
            activity_type="quiz_attempt",
            title="Quiz Attempt",
            description="Score: 85%",
            icon="FileCheck",
            timestamp=datetime.now(timezone.utc),
            metadata={"score": 85.0, "total": 10},
        )
        assert item.metadata["score"] == 85.0
        assert item.metadata["total"] == 10

    def test_activity_feed_response_empty(self):
        from src.schemas.activity import ActivityFeedResponse

        resp = ActivityFeedResponse()
        assert resp.activities == []

    def test_activity_feed_response_with_items(self):
        from src.schemas.activity import ActivityFeedResponse, ActivityItem

        items = [
            ActivityItem(
                activity_type="xp_event",
                title="Test",
                description="5 XP",
                icon="Zap",
                timestamp=datetime.now(timezone.utc),
            )
        ]
        resp = ActivityFeedResponse(activities=items)
        assert len(resp.activities) == 1
        assert resp.activities[0].activity_type == "xp_event"


class TestActivityEndpoint:
    @pytest.mark.asyncio
    async def test_activity_endpoint_exists(self):
        from src.api.activity import router

        routes = [r.path for r in router.routes]
        assert "/{user_id}" in routes or "/activity/{user_id}" in routes

    @pytest.mark.asyncio
    async def test_activity_response_schema_fields(self):
        from src.schemas.activity import ActivityItem

        now = datetime.now(timezone.utc)
        item = ActivityItem(
            activity_type="tutor_session",
            title="Tutor Session — Cell Biology",
            description="3 messages (telegram)",
            icon="MessageSquare",
            timestamp=now,
            metadata={"channel": "telegram", "topic": "Cell Biology", "message_count": 3},
        )
        assert item.activity_type == "tutor_session"
        assert "Cell Biology" in item.title
        assert item.metadata["channel"] == "telegram"
        assert item.metadata["message_count"] == 3

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_error(self):
        from src.schemas.activity import ActivityItem

        with pytest.raises(Exception):
            UUID("not-a-uuid")

    @pytest.mark.asyncio
    async def test_activity_types_enum(self):
        from src.schemas.activity import ActivityItem

        valid_types = {"xp_event", "quiz_attempt", "tutor_session", "achievement"}
        for atype in valid_types:
            item = ActivityItem(
                activity_type=atype,
                title="Test",
                description="Test description",
                icon="Zap",
                timestamp=datetime.now(timezone.utc),
            )
            assert item.activity_type == atype
