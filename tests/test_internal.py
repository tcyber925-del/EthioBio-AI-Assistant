from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_health_with_valid_key(client):
    with patch("src.config.settings.internal_api_key", "test-key-123"):
        response = await client.get(
            "/internal/health",
            headers={"X-API-Key": "test-key-123"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_internal_health_without_key(client):
    response = await client.get("/internal/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_internal_health_with_wrong_key(client):
    with patch("src.config.settings.internal_api_key", "test-key-123"):
        response = await client.get(
            "/internal/health",
            headers={"X-API-Key": "wrong-key"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_internal_health_with_unset_key(client):
    with patch("src.config.settings.internal_api_key", ""):
        response = await client.get(
            "/internal/health",
            headers={"X-API-Key": "test-key-123"},
        )
    assert response.status_code == 401
