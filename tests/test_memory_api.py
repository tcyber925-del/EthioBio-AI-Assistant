from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.session import get_session
from src.main import app


@pytest.fixture(autouse=True)
def override_db():
    async def mock_get_session():
        mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock.execute.return_value = mock_result
        yield mock

    app.dependency_overrides[get_session] = mock_get_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_log_event_invalid_payload_returns_422():
    """Schema-invalid memory events are client errors, not server errors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/memory/events",
            json={
                "user_id": str(uuid4()),
                "event_type": "quiz_completed",
                "topic": "photosynthesis",
                "event_metadata": {},
            },
        )
    assert response.status_code == 422
    assert "score" in response.json()["detail"]
