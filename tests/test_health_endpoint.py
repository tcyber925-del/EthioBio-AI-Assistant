from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.auth import get_current_user
from src.database.models import User, UserRole
from src.database.session import get_session
from src.main import app
from src.redis_client import get_redis


@pytest.fixture(autouse=True)
def override_db():
    async def mock_get_session():
        mock = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock.execute.return_value = mock_result

        def mock_add(instance):
            try:
                instance.id = uuid4()
            except Exception:
                pass

        mock.add.side_effect = mock_add

        async def mock_refresh(instance):
            try:
                instance.id = uuid4()
            except Exception:
                pass

        mock.refresh.side_effect = mock_refresh
        yield mock

    async def mock_get_redis():
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        yield mock_redis

    app.dependency_overrides[get_redis] = mock_get_redis

    async def mock_get_current_user():
        return User(
            id=uuid4(),
            email="test@example.com",
            role=UserRole.teacher,
            is_active=True,
        )

    app.dependency_overrides[get_session] = mock_get_session
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok_and_version():
    """Test that /health endpoint returns status ok and correct version"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.1.0"
        assert "ollama" in data
        assert "database" in data


@pytest.mark.asyncio
async def test_health_endpoint_with_ollama_check():
    """Test that /health endpoint calls ollama health check"""
    with patch("src.llm.router.ModelRouter.check_health", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["ollama"] is True


@pytest.mark.asyncio
async def test_health_endpoint_when_ollama_down():
    """Test that /health endpoint returns ollama=false when ollama is down"""
    with patch("src.llm.router.ModelRouter.check_health", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["ollama"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])