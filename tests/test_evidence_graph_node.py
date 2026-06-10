"""Tests for the EvidenceGraphNode."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.graph import StateGraph

from src.graph.nodes.evidence_graph import EvidenceGraphNode
from src.graph.orchestrator import build_agentic_graph, build_unified_graph
from src.graph.state import AgentState
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter


@pytest.mark.asyncio
async def test_node_passthrough_when_no_db():
    """Without db_session_factory, node should pass state through unchanged."""
    node = EvidenceGraphNode(db_session_factory=None)
    state = AgentState(user_message="test")
    result = await node(state)
    assert result is state
    assert result.user_message == "test"


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_creates_session(mock_evidence_graph_cls):
    """With a DB factory, node should create an EvidenceSession."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_evidence_graph_cls.return_value = mock_graph

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1", "topic": "Cell Biology"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    mock_graph.create_session.assert_called_once()
    assert result.retrieval_iterations == 0


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_persists_records(mock_evidence_graph_cls):
    """Each chunk should become an EvidenceRecord."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = []
    mock_evidence_graph_cls.return_value = mock_graph

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1", "topic": "Cell Biology"},
                "score": 0.95,
                "source": "curriculum",
            },
            {
                "content": "Mitosis is the process of cell division.",
                "metadata": {"id": "chunk-2", "topic": "Cell Division"},
                "score": 0.85,
                "source": "curriculum",
            },
        ]
    }

    await node(state)

    assert mock_graph.add.call_count == 2
    first_call_args = mock_graph.add.call_args_list[0][0]
    assert first_call_args[0].source_type == "curriculum"
    assert first_call_args[0].content == state.retrieval_source_results["curriculum"][0]["content"]


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_updates_evidence_ids(mock_evidence_graph_cls):
    """Node should populate state.evidence_ids from selector output."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(
            id="e1",
            content="Cell theory states all living things are made of cells.",
            source_type="curriculum",
            confidence=0.95,
        ),
        MagicMock(
            id="e2",
            content="Mitosis is the process of cell division.",
            source_type="curriculum",
            confidence=0.85,
        ),
    ]
    mock_evidence_graph_cls.return_value = mock_graph

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    node = EvidenceGraphNode(db_session_factory=MagicMock(return_value=mock_session))
    node.selector = mock_selector

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    assert result.evidence_ids == ["e1"]
    mock_selector.select_for_generation.assert_called_once()


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_sets_coverage_and_missing(mock_evidence_graph_cls):
    """Node should populate coverage_score and missing_information."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(id="e1", content="Cell theory", source_type="curriculum", confidence=0.95),
    ]
    mock_evidence_graph_cls.return_value = mock_graph

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    node = EvidenceGraphNode(db_session_factory=MagicMock(return_value=mock_session))
    node.selector = mock_selector

    state = AgentState(user_message="Cell theory", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    assert result.coverage_score == 1.0
    assert result.missing_information == []
    assert "evidence items" in result.evidence_summary


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_without_source_results(mock_evidence_graph_cls):
    """Node should handle empty retrieval_source_results gracefully."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_evidence_graph_cls.return_value = mock_graph

    node = EvidenceGraphNode(db_session_factory=MagicMock(return_value=mock_session))

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {}

    result = await node(state)

    assert result is state
    mock_graph.create_session.assert_not_called()


# ─── Graph Wiring Tests ───────────────────────────────────────────────


def _make_patched_graph(builder, router, adapter):
    """Build a graph with PlanExecutor mocked for LangGraph compatibility.

    Returns a namespace with .nodes dict so tests can verify node
    registration irrespective of pre-existing compilation issues.
    """
    patches = [
        patch("src.graph.orchestrator.PlanExecutor"),
        patch.object(
            StateGraph,
            "compile",
            lambda self: SimpleNamespace(nodes=self.nodes),
        ),
    ]
    for p in patches:
        p.start()
    try:
        result = builder(router, adapter)
        return result
    finally:
        for p in patches:
            p.stop()


def test_agentic_graph_has_evidence_graph_node():
    """Agentic graph should include evidence_graph node."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = _make_patched_graph(build_agentic_graph, router, adapter)

    nodes = list(graph.nodes.keys())
    assert "evidence_graph" in nodes, f"evidence_graph not in nodes: {nodes}"


def test_agentic_graph_node_ordering():
    """evidence_graph should be between plan_executor and sufficient_context."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = _make_patched_graph(build_agentic_graph, router, adapter)

    node_list = list(graph.nodes.keys())
    plan_idx = node_list.index("plan_executor")
    evidence_idx = node_list.index("evidence_graph")
    sufficient_idx = node_list.index("sufficient_context")

    assert plan_idx < evidence_idx < sufficient_idx, (
        f"Expected plan_executor < evidence_graph < sufficient_context, "
        f"got {node_list}"
    )


def test_unified_graph_has_evidence_graph_node():
    """Unified graph should include evidence_graph node."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = _make_patched_graph(build_unified_graph, router, adapter)

    nodes = list(graph.nodes.keys())
    assert "evidence_graph" in nodes, f"evidence_graph not in nodes: {nodes}"


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_sets_evidence_items(mock_evidence_graph_cls):
    """Evidence graph node should populate evidence_items with full dicts."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"

    mock_record = MagicMock()
    mock_record.id = "e1"
    mock_record.content = "Meiosis creates diversity"
    mock_record.source_name = "curriculum"
    mock_record.confidence = 0.9
    mock_record.archived = False

    mock_graph.get_evidence_for_session.return_value = [mock_record]
    mock_evidence_graph_cls.return_value = mock_graph

    node = EvidenceGraphNode(db_session_factory=MagicMock(return_value=mock_session))
    node.selector = AsyncMock()
    node.selector.select_for_generation.return_value = ["e1"]

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {"content": "test", "metadata": {}, "score": 0.9, "source": "curriculum"},
        ]
    }

    result = await node(state)

    assert len(result.evidence_items) >= 1
    assert result.evidence_items[0]["id"] == "e1"
    assert "content" in result.evidence_items[0]
    assert "source_name" in result.evidence_items[0]
    assert "confidence" in result.evidence_items[0]


def test_unified_graph_node_ordering():
    """evidence_graph should be between plan_executor and sufficient_context."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = _make_patched_graph(build_unified_graph, router, adapter)

    node_list = list(graph.nodes.keys())
    plan_idx = node_list.index("plan_executor")
    evidence_idx = node_list.index("evidence_graph")
    sufficient_idx = node_list.index("sufficient_context")

    assert plan_idx < evidence_idx < sufficient_idx, (
        f"Expected plan_executor < evidence_graph < sufficient_context, "
        f"got {node_list}"
    )


@pytest.mark.asyncio
@patch("src.graph.nodes.evidence_graph.EvidenceGraph")
async def test_node_skips_duplicates(mock_evidence_graph_cls):
    """Duplicate chunks should be deduplicated before persisting."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_evidence_graph_cls.return_value = mock_graph

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {"content": "Cell theory states all living things are made of cells.",
             "metadata": {"id": "chunk-1"}, "score": 0.95, "source": "curriculum"},
            # Exact duplicate
            {"content": "Cell theory states all living things are made of cells.",
             "metadata": {"id": "chunk-2"}, "score": 0.90, "source": "curriculum"},
            # Semantic duplicate
            {"content": "Cell theory: all living things are made of cells",
             "metadata": {"id": "chunk-3"}, "score": 0.85, "source": "curriculum"},
            # Unique
            {"content": "Mitosis is the process of cell division.",
             "metadata": {"id": "chunk-4"}, "score": 0.80, "source": "curriculum"},
        ]
    }

    await node(state)

    # Should only persist 2 out of 4 chunks (1 unique, 2 duplicates skipped)
    assert mock_graph.add.call_count == 2, (
        f"Expected 2 persists, got {mock_graph.add.call_count}"
    )
    persisted_contents = [
        call[0][0].content for call in mock_graph.add.call_args_list
    ]
    assert "Cell theory states all living things are made of cells." in persisted_contents
    assert "Mitosis is the process of cell division." in persisted_contents
