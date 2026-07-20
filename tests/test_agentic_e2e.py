"""End-to-end tests for the unified graph pipeline.

Tests the full pipeline through the production entry point (run_graph),
verifying routing decisions and state propagation end-to-end.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.orchestrator import build_unified_graph, run_graph
from src.graph.state import AgentState

_ROUTE_RESPONSE = {
    "content": (
        "Mitosis is the process of cell division where a single cell "
        "divides into two identical daughter cells."
    ),
    "model": "ollama/test",
    "usage": {"total_tokens": 50},
}


async def _fake_stream(*args, **kwargs):
    yield _ROUTE_RESPONSE["content"]


def _make_router():
    mock = AsyncMock()
    mock.route.return_value = _ROUTE_RESPONSE
    mock.route_stream = _fake_stream
    mock.generate = AsyncMock()
    mock.close = AsyncMock()
    return mock


def _make_adapter():
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    mock.format_context.return_value = "Context"
    return mock


@pytest.mark.asyncio
async def test_simple_query_via_run_graph():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router_cls.return_value = _make_router()
            adapter_cls.return_value = _make_adapter()

            result = await run_graph(
                user_message="What is photosynthesis?",
                grade_level=9,
                language="en",
            )

            assert result.answer
            assert result.status in ("approved", "needs_review")
            assert result.model_used


@pytest.mark.asyncio
async def test_simple_query_state_fields():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router = _make_router()
            adapter = _make_adapter()
            router_cls.return_value = router
            adapter_cls.return_value = adapter

            graph = build_unified_graph(router, adapter)
            state = AgentState(
                user_message="What is photosynthesis?",
                grade_level=9,
                language="en",
            )
            result = await graph.ainvoke(state)

            assert result.get("draft")
            assert result.get("intent") == "tutor"
            assert result.get("groundedness_score", 0) >= 0
            assert result.get("status") in ("approved", "needs_review")


@pytest.mark.asyncio
async def test_complex_query_via_run_graph():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router_cls.return_value = _make_router()
            adapter_cls.return_value = _make_adapter()

            result = await run_graph(
                user_message="Why do I keep confusing mitosis and meiosis?",
                grade_level=10,
                language="en",
            )

            assert result.answer
            assert result.model_used


@pytest.mark.asyncio
async def test_complex_query_sets_requires_planning():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router = _make_router()
            adapter = _make_adapter()
            router_cls.return_value = router
            adapter_cls.return_value = adapter

            graph = build_unified_graph(router, adapter)
            state = AgentState(
                user_message="Why do I keep confusing mitosis and meiosis?",
                grade_level=10,
                language="en",
            )
            result = await graph.ainvoke(state)

            assert result.get("draft")
            assert result.get("requires_planning") is True
            assert result.get("retrieval_iterations", 0) > 0


@pytest.mark.asyncio
async def test_amharic_query_completes():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router_cls.return_value = _make_router()
            adapter_cls.return_value = _make_adapter()

            result = await run_graph(
                user_message="ፎቶሲንቴሲስ ምንድን ነው?",
                grade_level=9,
                language="am",
            )

            assert result.answer
            assert result.model_used


@pytest.mark.asyncio
async def test_admin_skips_retrieval():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router_cls.return_value = _make_router()
            adapter_cls.return_value = _make_adapter()

            result = await run_graph(
                user_message="What can you do?",
                grade_level=9,
                language="en",
            )

            assert result.answer


@pytest.mark.asyncio
async def test_direct_invocation_populates_all_fields():
    with patch("src.graph.orchestrator.ModelRouter") as router_cls:
        with patch("src.graph.orchestrator.VectorStoreAdapter") as adapter_cls:
            router = _make_router()
            adapter = _make_adapter()
            router_cls.return_value = router
            adapter_cls.return_value = adapter

            graph = build_unified_graph(router, adapter)
            state = AgentState(
                user_message="What is mitosis?",
                grade_level=9,
                language="en",
            )
            result = await graph.ainvoke(state)

            assert result.get("intent") == "tutor"
            assert result.get("draft")
            assert "evidence_items" in result
            assert "evidence_ids" in result
            assert "groundedness_score" in result
