import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["message"] == "Test endpoint from Telegram"
        assert "timestamp" in body
