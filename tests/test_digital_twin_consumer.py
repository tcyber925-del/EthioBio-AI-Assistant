from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.digital_twin.consumer import DigitalTwinEventConsumer
from src.core.event_infrastructure.models import PipelineEvent


@pytest.mark.asyncio
async def test_digital_twin_consumer_process():
    # Setup
    consumer = DigitalTwinEventConsumer(redis_url="redis://localhost")
    user_id = str(uuid4())
    event = PipelineEvent(
        event_type="assessment_completed",
        ko_id="ko_123",
        workspace_id="ws_123",
        payload={"user_id": user_id, "score": 85},
        occurred_at=datetime.now(timezone.utc),
        correlation_id="corr_123",
    )

    # Mock TwinBuilder to check if it's called
    with patch("src.core.digital_twin.consumer.TwinBuilder") as MockBuilder:
        with patch("src.core.digital_twin.consumer.async_session_factory") as MockFactory:
            mock_session = AsyncMock()

            # We mock the return of async_session_factory
            # Since it returns a factory function, we need a nested mock
            # factory = async_session_factory()
            # async with factory() as session:
            mock_factory_func = MagicMock()
            MockFactory.return_value = mock_factory_func

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_factory_func.return_value = mock_context

            mock_builder_instance = MockBuilder.return_value
            mock_builder_instance.rebuild = AsyncMock()

            # Execute
            await consumer.process(event)

            # Assert
            MockBuilder.assert_called_once_with(mock_session)
            mock_builder_instance.rebuild.assert_called_once()

            # Extract the user_id arg it was called with
            called_user_id = mock_builder_instance.rebuild.call_args[0][0]
            assert str(called_user_id) == user_id

            # Assert commit was called
            mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_digital_twin_consumer_fallback_koid():
    # Setup
    consumer = DigitalTwinEventConsumer(redis_url="redis://localhost")
    user_id = str(uuid4())
    event = PipelineEvent(
        event_type="lesson_completed",
        ko_id=user_id,
        workspace_id="ws_123",
        payload={"progress": 100},
        occurred_at=datetime.now(timezone.utc),
        correlation_id="corr_123",
    )

    with patch("src.core.digital_twin.consumer.TwinBuilder") as MockBuilder:
        with patch("src.core.digital_twin.consumer.async_session_factory") as MockFactory:
            mock_session = AsyncMock()
            mock_factory_func = MagicMock()
            MockFactory.return_value = mock_factory_func

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_factory_func.return_value = mock_context

            mock_builder_instance = MockBuilder.return_value
            mock_builder_instance.rebuild = AsyncMock()

            # Execute
            await consumer.process(event)

            # Assert
            mock_builder_instance.rebuild.assert_called_once()
            called_user_id = mock_builder_instance.rebuild.call_args[0][0]
            assert str(called_user_id) == user_id


@pytest.mark.asyncio
async def test_digital_twin_consumer_invalid_user_id():
    # Setup
    consumer = DigitalTwinEventConsumer(redis_url="redis://localhost")
    event = PipelineEvent(
        event_type="assessment_completed",
        ko_id="not-a-uuid",
        workspace_id="ws_123",
        payload={"score": 85},
        occurred_at=datetime.now(timezone.utc),
        correlation_id="corr_123",
    )

    with patch("src.core.digital_twin.consumer.TwinBuilder") as MockBuilder:
        with patch("src.core.digital_twin.consumer.async_session_factory") as MockFactory:
            # Execute
            await consumer.process(event)

            # Assert
            MockBuilder.assert_not_called()
            MockFactory.assert_not_called()
