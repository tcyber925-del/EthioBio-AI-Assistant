"""Tests for the EvidenceGraphNode."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.nodes.evidence_graph import EvidenceGraphNode
from src.graph.state import AgentState


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
