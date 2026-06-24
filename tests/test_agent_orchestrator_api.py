"""Tests for the agent orchestrator API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_list_agents_endpoint(client):
    async with client as ac:
        resp = await ac.get("/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_list_reflections_empty(client):
    async with client as ac:
        resp = await ac.get("/agents/reflections?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_list_capabilities(client):
    async with client as ac:
        resp = await ac.get("/agents/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_execute_endpoint_missing_agent(client):
    async with client as ac:
        resp = await ac.post("/agents/execute", json={
            "task": "test task",
            "preferred_agent": "nonexistent_agent",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
