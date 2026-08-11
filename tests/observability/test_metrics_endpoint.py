import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.observability.metrics import inc_counter


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test that /metrics endpoint returns Prometheus-formatted metrics."""
    # Trigger a metric so the registry has content
    inc_counter("test_counter")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        # Response should be Prometheus text format
        assert "# HELP" in response.text
        assert "test_counter" in response.text
        assert response.text.endswith("\n")


@pytest.mark.asyncio
async def test_metrics_endpoint_has_content():
    """Test that /metrics returns some metrics content."""
    # Trigger a metric so the registry has content
    inc_counter("test_counter_2")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        # Should have some content
        assert len(response.text) > 0
        assert "test_counter_2" in response.text
