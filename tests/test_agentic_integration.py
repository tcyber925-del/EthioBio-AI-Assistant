"""Integration tests for Agentic RAG pipeline.

These tests require a running Ollama instance with models available.
Skip with: pytest -m "not integration"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.orchestrator import run_graph


@pytest.mark.integration
class TestAgenticRAGIntegration:
    """Integration tests for the Agentic RAG pipeline."""

    @pytest.mark.asyncio
    async def test_simple_query_routes_to_legacy(self):
        """Simple queries should route to legacy pipeline."""
        with patch("src.graph.orchestrator.ModelRouter") as mock_router_cls:
            with patch("src.graph.orchestrator.VectorStoreAdapter") as mock_adapter_cls:
                mock_router = AsyncMock()
                mock_router_cls.return_value = mock_router
                mock_router.close = AsyncMock()

                mock_adapter = MagicMock()
                mock_adapter_cls.return_value = mock_adapter

                result = await run_graph(
                    user_message="What is photosynthesis?",
                    grade_level=9,
                    topic="Biology",
                    language="en",
                )

                assert result.answer is not None
                assert result.model_used is not None

    @pytest.mark.asyncio
    async def test_complex_query_routes_to_agentic(self):
        """Complex queries should route to agentic pipeline."""
        with patch("src.graph.orchestrator.ModelRouter") as mock_router_cls:
            with patch("src.graph.orchestrator.VectorStoreAdapter") as mock_adapter_cls:
                mock_router = AsyncMock()
                mock_router_cls.return_value = mock_router
                mock_router.close = AsyncMock()

                mock_adapter = MagicMock()
                mock_adapter_cls.return_value = mock_adapter

                result = await run_graph(
                    user_message=(
                        "Compare and contrast cellular respiration and photosynthesis, "
                        "explain how they are connected, and discuss the role of mitochondria "
                        "and chloroplasts in these processes."
                    ),
                    grade_level=11,
                    topic="Biology",
                    language="en",
                )

                assert result.answer is not None
                assert result.model_used is not None

    @pytest.mark.asyncio
    async def test_amharic_query(self):
        """Amharic queries should work with the pipeline."""
        with patch("src.graph.orchestrator.ModelRouter") as mock_router_cls:
            with patch("src.graph.orchestrator.VectorStoreAdapter") as mock_adapter_cls:
                mock_router = AsyncMock()
                mock_router_cls.return_value = mock_router
                mock_router.close = AsyncMock()

                mock_adapter = MagicMock()
                mock_adapter_cls.return_value = mock_adapter

                result = await run_graph(
                    user_message="ፎቶሲንቴ시스 ምንድን ነው?",
                    grade_level=9,
                    topic="Biology",
                    language="am",
                )

                assert result.answer is not None
                assert result.model_used is not None


@pytest.mark.integration
class TestPipelineMonitoring:
    """Integration tests for pipeline monitoring."""

    def test_trace_creation(self):
        """Should create trace with unique ID."""
        from src.core.monitoring import pipeline_monitor

        trace = pipeline_monitor.start_trace(metadata={"test": True})

        assert trace.trace_id.startswith("trace_")
        assert trace.status == "running"

    def test_trace_node_timing(self):
        """Should track node timing."""
        from src.core.monitoring import pipeline_monitor

        trace = pipeline_monitor.start_trace()

        trace.start_node("orchestrator")
        import time
        time.sleep(0.01)
        duration = trace.end_node("orchestrator")

        assert duration > 0
        assert "orchestrator" in trace.nodes_visited

    def test_trace_completion(self):
        """Should mark trace as completed."""
        from src.core.monitoring import pipeline_monitor

        trace = pipeline_monitor.start_trace()
        trace.finish(status="completed")

        assert trace.status == "completed"
        assert trace.end_time is not None
        assert trace.duration_ms > 0


@pytest.mark.integration
class TestEvidenceGraphIntegration:
    """Integration tests for Evidence Graph storage."""

    @pytest.mark.asyncio
    async def test_add_evidence(self):
        """Should add evidence to graph."""
        from src.core.evidence.graph import Evidence, EvidenceGraph

        mock_session = AsyncMock()
        graph = EvidenceGraph(mock_session)

        evidence = Evidence(
            id="",
            source_type="curriculum",
            source_name="Grade 9 Biology",
            chunk_id="chunk_123",
            content="Photosynthesis is the process...",
            original_query="What is photosynthesis?",
            retrieval_query="photosynthesis definition",
            retrieval_score=0.85,
            rerank_score=0.9,
            confidence=0.85,
            retrieved_by="search_fanout",
        )

        evidence_id = await graph.add(evidence)

        assert evidence_id is not None
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


@pytest.mark.integration
class TestQueryRewriterIntegration:
    """Integration tests for Query Rewriter."""

    def test_fallback_query_expansion(self):
        """Should expand query via fallback."""
        from unittest.mock import MagicMock

        from src.agents.query_rewriter.query_rewriter import QueryRewriterAgent

        agent = QueryRewriterAgent(MagicMock())
        bundle = agent._build_fallback("What is DNA?")

        assert len(bundle.rewritten_queries) >= 1
        assert bundle.rewritten_queries[0].query == "What is DNA?"

    def test_fallback_decomposition(self):
        """Should decompose via fallback with subtasks."""
        from unittest.mock import MagicMock

        from src.agents.query_rewriter.query_rewriter import QueryRewriterAgent

        agent = QueryRewriterAgent(MagicMock())
        subtasks = [
            {"id": "1", "objective": "Define DNA", "type": "curriculum"},
            {"id": "2", "objective": "Explain DNA structure", "type": "curriculum"},
        ]

        bundle = agent._build_fallback("Explain DNA", subtasks)

        assert len(bundle.rewritten_queries) >= 2


@pytest.mark.integration
class TestClaimVerifierIntegration:
    """Integration tests for Claim Verifier."""

    def test_claim_extraction(self):
        """Should extract claims from response."""
        from src.graph.nodes.claim_verifier import extract_claims_simple

        response = (
            "DNA is a double helix structure. "
            "It contains four nucleotide bases: A, T, G, C."
        )

        claims = extract_claims_simple(response)

        assert len(claims) >= 2
        assert any(c.claim_type == "definition" for c in claims)

    def test_groundedness_calculation(self):
        """Should calculate groundedness score."""
        from src.graph.nodes.claim_verifier import Claim, calculate_groundedness

        claims = [
            Claim(text="claim1", claim_type="fact", is_grounded=True),
            Claim(text="claim2", claim_type="fact", is_grounded=False),
            Claim(text="claim3", claim_type="fact", is_grounded=True),
        ]

        score = calculate_groundedness(claims)

        assert score == pytest.approx(2 / 3, rel=0.01)
