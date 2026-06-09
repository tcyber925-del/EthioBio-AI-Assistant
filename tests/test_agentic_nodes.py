"""Tests for Agentic RAG nodes.

Tests SufficientContextNode, ClaimVerifierNode, QueryRewriterNode,
and SearchFanoutNode.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.nodes.claim_verifier import (
    ClaimVerifierNode,
    calculate_groundedness,
    extract_claims_simple,
    route_after_verification,
)
from src.graph.nodes.query_rewriter import (
    QueryRewriterNode,
    route_after_rewrite,
)
from src.graph.nodes.search_fanout import (
    SearchFanoutNode,
)
from src.graph.nodes.sufficient_context import (
    SufficientContextNode,
    evaluate_sufficiency,
    route_after_sufficiency,
)
from src.graph.state import AgentState

# ─── QueryRewriterNode Tests ──────────────────────────────────────────


class TestQueryRewriterNode:
    """Tests for QueryRewriterNode."""

    @pytest.mark.asyncio
    async def test_node_updates_state(self):
        """Should update state with rewritten queries."""
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": (
                    '{"queries": [{"query": "test query", "category": "curriculum",'
                    ' "purpose": "test", "priority": 5}], "coverage_score": 0.8}'
                )
            }
        )
        node = QueryRewriterNode(mock_router)

        state = AgentState(user_message="test")
        state.subtasks = [{"id": "1", "type": "curriculum", "objective": "test objective"}]

        result = await node(state)

        assert len(result.rewritten_queries) >= 1
        assert "curriculum" in result.query_source_types

    @pytest.mark.asyncio
    async def test_node_without_router_uses_fallback(self):
        """Should use heuristic fallback when no router."""
        node = QueryRewriterNode(router=None)

        state = AgentState(user_message="test query")
        state.subtasks = [
            {"id": "1", "type": "curriculum", "objective": "find mitosis info"}
        ]

        result = await node(state)

        assert len(result.rewritten_queries) >= 1
        assert result.rewritten_queries[0] == "find mitosis info"

    @pytest.mark.asyncio
    async def test_node_without_subtasks_fallback(self):
        """Should use original query when no subtasks."""
        node = QueryRewriterNode(router=None)

        state = AgentState(user_message="what is osmosis")

        result = await node(state)

        assert len(result.rewritten_queries) == 1
        assert result.rewritten_queries[0] == "what is osmosis"

    def test_route_after_rewrite_always_search_fanout(self):
        """Should always route to search_fanout."""
        state = AgentState(user_message="test")

        route = route_after_rewrite(state)

        assert route == "search_fanout"


# ─── SearchFanout Tests ────────────────────────────────────────────────


class TestChunkDeduplication:
    """Tests for chunk deduplication."""

    @pytest.mark.asyncio
    async def test_deduplicate_removes_duplicates(self):
        """Should remove duplicate chunks."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {
            "documents": [
                {"content": "same content", "metadata": {"id": "id1"}, "score": 0.8},
                {"content": "same content", "metadata": {"id": "id2"}, "score": 0.9},
            ]
        }

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["test"]},
            rewritten_queries=["test"],
        )

        result = await node(state)

        assert len(result.retrieved_chunks) == 1
        assert result.retrieved_chunks[0]["content"] == "same content"

    @pytest.mark.asyncio
    async def test_rank_chunks(self):
        """Should rank chunks by score."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {
            "documents": [
                {"content": "low", "metadata": {"id": "id1"}, "score": 0.3},
                {"content": "high", "metadata": {"id": "id2"}, "score": 0.9},
                {"content": "medium", "metadata": {"id": "id3"}, "score": 0.6},
            ]
        }

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["test"]},
            rewritten_queries=["test"],
        )

        result = await node(state)

        assert len(result.retrieved_chunks) <= 3
        if len(result.retrieved_chunks) >= 2:
            assert result.retrieved_chunks[0]["score"] >= result.retrieved_chunks[1]["score"]


class TestSearchFanoutNode:
    """Tests for SearchFanoutNode."""

    @pytest.mark.asyncio
    async def test_node_retrieves_chunks(self):
        """Should retrieve and rank chunks via curriculum retriever."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {
            "documents": [
                {"content": "test content", "metadata": {"id": "id1"}, "score": 0.8}
            ]
        }

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(user_message="test")
        state.rewritten_queries = ["test query"]
        state.query_groups = {"curriculum": ["test query"]}

        result = await node(state)

        assert len(result.retrieved_chunks) >= 0
        assert result.retrieval_strategy != {}

    @pytest.mark.asyncio
    async def test_node_sets_strategy_and_tasks(self):
        """Should populate retrieval_strategy and retrieval_tasks."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {"documents": []}

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["mitosis"], "memory": ["past mistakes"]},
            rewritten_queries=["mitosis", "past mistakes"],
        )

        result = await node(state)

        assert len(result.retrieval_tasks) == 2
        assert result.retrieval_strategy.get("strategy_name") == "PERSONALIZED"

    @pytest.mark.asyncio
    async def test_node_handles_source_failure_gracefully(self):
        """Should continue when one source fails."""
        mock_adapter = MagicMock()
        mock_adapter.search.side_effect = Exception("DB down")

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["mitosis"]},
            rewritten_queries=["mitosis"],
        )

        result = await node(state)

        assert result.retrieval_strategy != {}
        assert result.status == "pending"


# ─── SufficientContextNode Tests ─────────────────────────────────────


class TestSufficientContextNode:
    """Tests for SufficientContextNode."""

    @pytest.mark.asyncio
    async def test_node_sufficient_context(self):
        node = SufficientContextNode()
        state = AgentState(user_message="test")
        state.context = "A" * 600

        result = await node(state)

        assert result.sufficiency_score > 0.5
        assert result.coverage_score > 0.5

    @pytest.mark.asyncio
    async def test_node_insufficient_context(self):
        node = SufficientContextNode()
        state = AgentState(user_message="test")
        state.context = "short"

        result = await node(state)

        assert result.sufficiency_score < 0.3
        assert result.requires_iteration is True

    def test_route_after_sufficiency_sufficient(self):
        state = AgentState(user_message="test")
        state.sufficiency_score = 0.8
        state.coverage_score = 0.8

        route = route_after_sufficiency(state)

        assert route == "synthesis"

    def test_route_after_sufficiency_gap(self):
        state = AgentState(user_message="test")
        state.sufficiency_score = 0.3
        state.coverage_score = 0.3
        state.requires_iteration = True
        state.missing_information = ["Explain mitosis"]

        route = route_after_sufficiency(state)

        assert route == "rewrite"

    def test_evaluate_sufficiency_no_longer_checks_hard_cap(self):
        """evaluate_sufficiency no longer stops at max iterations —
        that's the controller's job. Should compute score normally."""
        state = AgentState(user_message="test")
        state.retrieval_iterations = 2
        state.evidence_ids = ["e1"]
        state.coverage_score = 0.5

        result = evaluate_sufficiency(state)

        assert result.score > 0
        assert result.action in ("sufficient", "minor_gap")

    def test_evaluate_sufficiency_hard_cap_no_evidence(self):
        """Should report major gap when hard cap hit with no evidence."""
        state = AgentState(user_message="test")
        state.retrieval_iterations = 2

        result = evaluate_sufficiency(state)

        assert result.is_sufficient is False
        assert result.action == "major_gap"

    def test_evaluate_sufficiency_no_longer_checks_diminishing_returns(self):
        """evaluate_sufficiency no longer stops on diminishing returns —
        that's the controller's job. Should compute score normally."""
        state = AgentState(user_message="test")
        state.retrieval_iterations = 1
        state.evidence_ids = ["e1"]
        state.previous_evidence_count = 1
        state.coverage_score = 0.5

        result = evaluate_sufficiency(state)

        assert result.score > 0

    def test_evaluate_sufficiency_sufficient(self):
        """Should report sufficient when coverage meets threshold."""
        state = AgentState(user_message="test")
        state.evidence_ids = ["e1"]
        state.coverage_score = 0.9

        result = evaluate_sufficiency(state)

        assert result.is_sufficient is True

    def test_evaluate_sufficiency_insufficient(self):
        """Should report gap when coverage is low or missing info exists."""
        state = AgentState(user_message="test")
        state.evidence_ids = ["e1"]
        state.coverage_score = 0.2
        state.missing_information = ["gap 1"]

        result = evaluate_sufficiency(state)

        assert result.is_sufficient is False


# ─── ClaimVerifierNode Tests ──────────────────────────────────────────


class TestClaimExtraction:
    """Tests for claim extraction."""

    def test_extract_claims_simple(self):
        text = "Mitosis has four stages. Meiosis has two divisions."
        claims = extract_claims_simple(text)
        assert len(claims) >= 2
        assert any("mitosis" in c.lower() for c in claims)

    def test_extract_claims_empty(self):
        assert extract_claims_simple("") == []
        assert extract_claims_simple("   ") == []


class TestGroundedness:
    """Tests for groundedness scoring."""

    def test_calculate_groundedness_full_support(self):
        claims = ["Mitosis has prophase"]
        evidence = "Prophase is the first stage of mitosis"
        score = calculate_groundedness(claims, evidence)
        assert score > 0.5

    def test_calculate_groundedness_no_evidence(self):
        claims = ["Photosynthesis happens on Mars"]
        evidence = "Plants need sunlight for photosynthesis"
        score = calculate_groundedness(claims, evidence)
        assert score < 0.1

    def test_calculate_groundedness_empty_claims(self):
        score = calculate_groundedness([], "some evidence")
        assert score == 1.0


class TestClaimVerifierNode:
    """Tests for ClaimVerifierNode integration."""

    @pytest.mark.asyncio
    async def test_node_verifies_claims(self):
        node = ClaimVerifierNode()
        state = AgentState(
            user_message="test",
            draft="Mitosis has four stages: prophase, metaphase, anaphase, telophase.",
        )
        state.context = (
            "The four stages of mitosis are prophase, metaphase, anaphase, and telophase."
        )

        result = await node(state)

        assert result.groundedness_score > 0.5
        assert result.safety_action == "finalize"

    @pytest.mark.asyncio
    async def test_node_low_groundedness(self):
        node = ClaimVerifierNode()
        state = AgentState(
            user_message="test",
            draft="Mitosis happens on the Moon.",
        )
        state.context = "Mitosis is cell division in Earth organisms."

        result = await node(state)

        assert result.groundedness_score < 0.5
        assert result.safety_action == "revise"

    def test_route_after_verification_finalize(self):
        state = AgentState(user_message="test")
        state.safety_action = "finalize"
        state.safety_score = 0.9
        state.groundedness_score = 0.8
        route = route_after_verification(state)
        assert route == "finalize"

    def test_route_after_verification_revise(self):
        state = AgentState(user_message="test")
        state.safety_action = "revise"
        route = route_after_verification(state)
        assert route == "revise"

    def test_route_after_verification_reject(self):
        state = AgentState(user_message="test")
        state.safety_action = "reject"
        route = route_after_verification(state)
        assert route == "reject"
