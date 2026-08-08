import pytest
from httpx import ASGITransport, AsyncClient, Response

from src.main import app
from src.observability import metrics as metrics_module


async def _get_metrics() -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/metrics")


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text():
    """Test that /metrics returns 200 with text/plain Prometheus format."""
    resp = await _get_metrics()
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.text.endswith("\n")


@pytest.mark.asyncio
async def test_metrics_endpoint_reflects_registered_metrics():
    """Test that registered metrics appear in the /metrics payload."""
    registry = metrics_module.registry
    if registry is None:
        pytest.skip("metrics registry disabled")
    name = "ethiobio_test_metric_total"
    registry.gauge(name).set(7)
    try:
        resp = await _get_metrics()
        assert resp.status_code == 200
        assert f"# HELP {name}" in resp.text
        assert f"# TYPE {name} gauge" in resp.text
        assert f"{name} 7" in resp.text
    finally:
        registry._gauges.pop(name, None)


@pytest.mark.asyncio
async def test_metrics_endpoint_when_registry_disabled(monkeypatch):
    """Test that /metrics returns a graceful message when metrics are disabled."""
    monkeypatch.setattr(metrics_module, "registry", None)
    resp = await _get_metrics()
    assert resp.status_code == 200
    assert resp.text.strip() == "# No metrics registry (disabled)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
