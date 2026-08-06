import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_config_validate_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/config/validate")
        assert response.status_code == 200
        assert response.json() == {"status": "valid", "service": "ethiobio"}
