"""Shared fixtures for end-to-end journey tests.

Journey tests mock external dependencies (DB, LLM, vector store)
and test the wiring between LangGraph pipeline nodes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_pipeline_components():
    """Returns mocked LangGraph pipeline nodes wired together."""
    with (
        patch("src.graph.nodes.planner.PlannerNode") as mock_planner,
        patch("src.graph.nodes.query_rewriter.QueryRewriterNode") as mock_rewriter,
        patch("src.graph.nodes.search_fanout.SearchFanoutNode") as mock_fanout,
        patch("src.graph.nodes.evidence_graph.EvidenceGraphNode") as mock_evidence,
        patch("src.graph.nodes.sufficient_context.SufficientContextNode") as mock_context,
        patch("src.graph.nodes.tutor.TutorNode") as mock_tutor,
        patch("src.graph.nodes.synthesis.SynthesisNode") as mock_synthesis,
    ):
        mock_planner.return_value.__call__ = AsyncMock()
        mock_rewriter.return_value.__call__ = AsyncMock()
        mock_fanout.return_value.__call__ = AsyncMock()
        mock_evidence.return_value.__call__ = AsyncMock()
        mock_context.return_value.__call__ = AsyncMock()
        mock_tutor.return_value.__call__ = AsyncMock()
        mock_synthesis.return_value.__call__ = AsyncMock()

        yield {
            "planner": mock_planner,
            "rewriter": mock_rewriter,
            "fanout": mock_fanout,
            "evidence": mock_evidence,
            "context": mock_context,
            "tutor": mock_tutor,
            "synthesis": mock_synthesis,
        }
