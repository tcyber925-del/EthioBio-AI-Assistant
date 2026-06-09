"""Tests for the EvidenceGraphNode."""
from unittest.mock import AsyncMock, MagicMock

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
async def test_node_creates_session():
    """With a DB factory, node should create an EvidenceSession."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph  # inject mock

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
async def test_node_persists_records():
    """Each chunk should become an EvidenceRecord."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = []

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph

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
async def test_node_updates_evidence_ids():
    """Node should populate state.evidence_ids from selector output."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(id="e1", confidence=0.95), MagicMock(id="e2", confidence=0.85)
    ]

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph
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
async def test_node_sets_coverage_and_missing():
    """Node should populate coverage_score and missing_information."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(id="e1", content="Cell theory", source_type="curriculum", confidence=0.95),
    ]

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph
    node.selector = mock_selector

    state = AgentState(user_message="What is cell theory?", trace_id="trace-1")
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

    assert result.coverage_score >= 0.0
    assert isinstance(result.missing_information, list)
    assert isinstance(result.evidence_summary, str)


@pytest.mark.asyncio
async def test_node_without_source_results():
    """Node should handle empty retrieval_source_results gracefully."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {}

    result = await node(state)

    assert result is state
    mock_graph.create_session.assert_not_called()
