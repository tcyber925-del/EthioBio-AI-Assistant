import pytest

from src.core.retrieval.models import (
    EvidencePackage,
    EvidenceSource,
    RetrievalResult,
    RoutingPlan,
    SourceCitation,
    TextMatch,
)


class TestRetrievalModels:
    def test_retrieval_result_defaults(self):
        r = RetrievalResult(ko_id="1", title="T", content_type="pdf", score=0.9, matches=[])
        assert r.workspace_id is None
        assert r.enrichment is None

    def test_evidence_source_has_citation(self):
        c = SourceCitation(ko_id="1", title="T", chunk_excerpt="excerpt", confidence_badge="high")
        s = EvidenceSource(
            ko_id="1",
            title="T",
            content="content",
            chunk_index=0,
            confidence=0.95,
            citation=c,
        )
        assert s.citation.confidence_badge == "high"

    def test_evidence_package_defaults(self):
        p = EvidencePackage(query="q", sources=[], total_results=0)
        assert p.degraded is False

    def test_routing_plan(self):
        p = RoutingPlan(layers=["workspace"], primary_source="kml", strategy="hybrid")
        assert p.primary_source == "kml"

    def test_text_match(self):
        m = TextMatch(text="cell biology", chunk_index=0, score=0.95)
        assert m.text == "cell biology"


class TestTrustRanker:
    def test_rerank_keeps_all_results(self):
        from src.core.retrieval.ranking import TrustRanker

        ranker = TrustRanker()
        results = [
            RetrievalResult(
                ko_id="1",
                title="A",
                content_type="pdf",
                score=0.5,
                matches=[TextMatch(text="a", chunk_index=0, score=0.5)],
            ),
            RetrievalResult(
                ko_id="2",
                title="B",
                content_type="txt",
                score=0.8,
                matches=[TextMatch(text="b", chunk_index=0, score=0.8)],
            ),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        assert len(ranked) == 2

    def test_rerank_sorts_by_score_descending(self):
        from src.core.retrieval.ranking import TrustRanker

        ranker = TrustRanker()
        results = [
            RetrievalResult(
                ko_id="1",
                title="A",
                content_type="pdf",
                score=0.5,
                matches=[TextMatch(text="a", chunk_index=0, score=0.5)],
            ),
            RetrievalResult(
                ko_id="2",
                title="B",
                content_type="txt",
                score=0.8,
                matches=[TextMatch(text="b", chunk_index=0, score=0.8)],
            ),
            RetrievalResult(
                ko_id="3",
                title="C",
                content_type="pdf",
                score=0.6,
                matches=[TextMatch(text="c", chunk_index=0, score=0.6)],
            ),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_boosts_enriched_results(self):
        from src.core.retrieval.ranking import TrustRanker

        ranker = TrustRanker()
        results = [
            RetrievalResult(
                ko_id="1",
                title="A",
                content_type="pdf",
                score=0.7,
                matches=[TextMatch(text="a", chunk_index=0, score=0.7)],
            ),
            RetrievalResult(
                ko_id="2",
                title="B",
                content_type="txt",
                score=0.7,
                matches=[TextMatch(text="b", chunk_index=0, score=0.7)],
                enrichment={"content_class": "lesson"},
            ),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        assert ranked[0].ko_id == "2"
        expected = 0.7 + 0.05 + 0.03
        assert ranked[0].score == expected

    def test_rerank_boosts_workspace_match(self):
        from src.core.retrieval.ranking import TrustRanker

        ranker = TrustRanker()
        ws = "ws-1"
        results = [
            RetrievalResult(
                ko_id="1",
                title="A",
                content_type="pdf",
                score=0.7,
                matches=[TextMatch(text="a", chunk_index=0, score=0.7)],
                workspace_id="ws-2",
            ),
            RetrievalResult(
                ko_id="2",
                title="B",
                content_type="txt",
                score=0.7,
                matches=[TextMatch(text="b", chunk_index=0, score=0.7)],
                workspace_id=ws,
            ),
        ]
        ranked = ranker.rerank(results, workspace_id=ws)
        assert ranked[0].ko_id == "2"


class TestRetrievalGateway:
    async def test_search_returns_results(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology", "dna structure"],
                "metadatas": [
                    {"knowledge_object_id": "ko-1", "chunk_index": 0},
                    {"knowledge_object_id": "ko-1", "chunk_index": 1},
                ],
                "distances": [0.1, 0.2],
                "ids": ["ko-1:chunk:0", "ko-1:chunk:1"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={},
        )

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].ko_id == "ko-1"
        assert results[0].title == "Cell Biology"

    async def test_search_returns_empty_for_no_matches(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={"documents": [], "metadatas": [], "distances": [], "ids": []}
        )

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=AsyncMock(),
        )
        results = await gateway.search(q="nothing", workspace_id=None, limit=10)
        assert results == []

    async def test_search_filters_by_workspace(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology"],
                "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
                "distances": [0.1],
                "ids": ["ko-1:chunk:0"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-2",
            metadata={},
        )

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id="ws-1", limit=10)
        assert len(results) == 0

    async def test_search_returns_enrichment_in_result(self):
        import json
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology"],
                "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
                "distances": [0.1],
                "ids": ["ko-1:chunk:0"],
            }
        )
        enrichment_data = {"content_class": "lesson", "key_terms": ["biology"]}
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={"enrichment": json.dumps(enrichment_data)},
        )

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].enrichment == enrichment_data

    async def test_search_handles_malformed_enrichment_json(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology"],
                "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
                "distances": [0.1],
                "ids": ["ko-1:chunk:0"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={"enrichment": "not valid json"},
        )
        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].enrichment is None

    async def test_search_handles_none_metadata(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology"],
                "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
                "distances": [0.1],
                "ids": ["ko-1:chunk:0"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata=None,
        )
        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].enrichment is None

    async def test_search_dedup_by_knowledge_object_id(self):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology intro", "cell biology advanced"],
                "metadatas": [
                    {"knowledge_object_id": "ko-1", "chunk_index": 0},
                    {"knowledge_object_id": "ko-1", "chunk_index": 1},
                ],
                "distances": [0.1, 0.3],
                "ids": ["ko-1:chunk:0", "ko-1:chunk:1"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={},
        )
        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert len(results[0].matches) == 2

    async def test_search_uses_reranker_when_enabled(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway
        from src.core.retrieval.openrouter_reranker import OpenRouterReranker

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology", "dna structure"],
                "metadatas": [
                    {"knowledge_object_id": "ko-1", "chunk_index": 0},
                    {"knowledge_object_id": "ko-1", "chunk_index": 1},
                ],
                "distances": [0.1, 0.9],
                "ids": ["ko-1:chunk:0", "ko-1:chunk:1"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={},
        )
        mock_reranker = AsyncMock(spec=OpenRouterReranker)
        mock_reranker.rerank.return_value = [0.9, 0.1]

        monkeypatch.setattr("src.config.settings.enable_reranker", True)
        monkeypatch.setattr("src.config.settings.openrouter_api_key", "sk-test")

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
            reranker=mock_reranker,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        mock_reranker.rerank.assert_awaited_once()
        reranked_score = results[0].matches[0].score
        assert reranked_score == pytest.approx(0.9)

    async def test_search_falls_back_when_reranker_raises(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway
        from src.core.retrieval.openrouter_reranker import OpenRouterReranker, RerankerError

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology", "dna structure"],
                "metadatas": [
                    {"knowledge_object_id": "ko-1", "chunk_index": 0},
                    {"knowledge_object_id": "ko-1", "chunk_index": 1},
                ],
                "distances": [0.1, 0.9],
                "ids": ["ko-1:chunk:0", "ko-1:chunk:1"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={},
        )
        mock_reranker = AsyncMock(spec=OpenRouterReranker)
        mock_reranker.rerank.side_effect = RerankerError("boom")

        monkeypatch.setattr("src.config.settings.enable_reranker", True)
        monkeypatch.setattr("src.config.settings.openrouter_api_key", "sk-test")

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
            reranker=mock_reranker,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].matches[0].score == pytest.approx(1.0 - 0.1)

    async def test_search_no_reranker_when_disabled(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        from src.core.retrieval.gateway import RetrievalGateway

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query = AsyncMock(
            return_value={
                "documents": ["cell biology"],
                "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
                "distances": [0.1],
                "ids": ["ko-1:chunk:0"],
            }
        )
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1",
            title="Cell Biology",
            content_type="pdf",
            workspace_id="ws-1",
            metadata={},
        )

        monkeypatch.setattr("src.config.settings.enable_reranker", False)
        monkeypatch.setattr("src.config.settings.openrouter_api_key", "sk-test")

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id=None, limit=10)
        assert len(results) == 1
        assert results[0].matches[0].score == pytest.approx(1.0 - 0.1)


class TestCitationFormatter:
    def test_format_badge_high(self):
        from src.core.retrieval.citation import CitationFormatter

        f = CitationFormatter()
        assert f.format_badge(0.95) == "high"
        assert f.format_badge(0.90) == "high"

    def test_format_badge_medium(self):
        from src.core.retrieval.citation import CitationFormatter

        f = CitationFormatter()
        assert f.format_badge(0.8) == "medium"
        assert f.format_badge(0.7) == "medium"

    def test_format_badge_low(self):
        from src.core.retrieval.citation import CitationFormatter

        f = CitationFormatter()
        assert f.format_badge(0.6) == "low"
        assert f.format_badge(0.0) == "low"

    def test_format_inline(self):
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.models import EvidenceSource, SourceCitation

        f = CitationFormatter()
        cit = SourceCitation(
            ko_id="1",
            title="Cell Biology",
            chunk_excerpt="Cells are...",
            confidence_badge="high",
        )
        source = EvidenceSource(
            ko_id="1",
            title="Cell Biology",
            content="Cells are...",
            chunk_index=0,
            confidence=0.95,
            citation=cit,
        )
        result = f.format_inline(source)
        assert "Cell Biology" in result
        assert "[high confidence]" in result

    def test_format_footnote(self):
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.models import EvidenceSource, SourceCitation

        f = CitationFormatter()
        cit = SourceCitation(
            ko_id="1",
            title="Cell Biology",
            chunk_excerpt="Cells are...",
            confidence_badge="high",
        )
        source = EvidenceSource(
            ko_id="1",
            title="Cell Biology",
            content="Cells are...",
            chunk_index=0,
            confidence=0.95,
            citation=cit,
        )
        result = f.format_footnote(source, 1)
        assert "[1]" in result
        assert "Cell Biology" in result

    def test_build_citation(self):
        from src.core.retrieval.citation import CitationFormatter

        f = CitationFormatter()
        cit = f.build_citation(
            ko_id="1",
            title="Cell Biology",
            content="Cells are the basic unit of life.",
            confidence=0.95,
        )
        assert cit.ko_id == "1"
        assert cit.confidence_badge == "high"
        assert "Cells are" in cit.chunk_excerpt


class TestEvidencePackageBuilder:
    def test_build_from_results(self):
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.evidence_package import EvidencePackageBuilder
        from src.core.retrieval.models import RetrievalResult, TextMatch

        builder = EvidencePackageBuilder(CitationFormatter())
        results = [
            RetrievalResult(
                ko_id="1",
                title="Cell Biology",
                content_type="pdf",
                score=0.95,
                matches=[TextMatch(text="Cells are the basic unit", chunk_index=0, score=0.95)],
            ),
        ]
        pkg = builder.build("what is a cell", results)
        assert pkg.query == "what is a cell"
        assert len(pkg.sources) == 1
        assert pkg.sources[0].title == "Cell Biology"
        assert pkg.sources[0].confidence == 0.95
        assert pkg.sources[0].citation.confidence_badge == "high"

    def test_build_empty_results(self):
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.evidence_package import EvidencePackageBuilder

        builder = EvidencePackageBuilder(CitationFormatter())
        pkg = builder.build("nothing", [])
        assert pkg.total_results == 0
        assert pkg.sources == []


class TestRetrievalAPI:
    async def test_search_returns_evidence_package(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        mock_gateway = AsyncMock()
        mock_gateway.search.return_value = []
        mock_builder = MagicMock()
        mock_builder.build.return_value = {
            "query": "biology",
            "sources": [],
            "total_results": 0,
            "degraded": False,
        }

        app = FastAPI()
        import src.api.retrieval as retrieval_module

        app.include_router(retrieval_module.router)

        with (
            patch.object(retrieval_module, "_get_gateway", return_value=mock_gateway),
            patch.object(retrieval_module, "_get_builder", return_value=mock_builder),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/retrieval/search", params={"q": "biology"})
                assert resp.status_code == 200
                data = resp.json()
                assert data["query"] == "biology"

    async def test_search_requires_query(self):
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()
        import src.api.retrieval as retrieval_module

        app.include_router(retrieval_module.router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/retrieval/search")
            assert resp.status_code == 422


class TestKnowledgeRouter:
    def test_route_with_workspace(self):
        from src.core.retrieval.router import KnowledgeRouter

        router = KnowledgeRouter()
        plan = router.route(query="biology", workspace_id="ws-1")
        assert plan.primary_source == "kml"
        assert "workspace" in plan.layers
        assert plan.strategy == "vector_only"

    def test_route_without_workspace(self):
        from src.core.retrieval.router import KnowledgeRouter

        router = KnowledgeRouter()
        plan = router.route(query="biology")
        assert plan.primary_source == "legacy"
        assert "curriculum" in plan.layers
        assert plan.strategy == "vector_only"

    async def test_route_and_search_kml(self):
        from unittest.mock import AsyncMock

        from src.core.retrieval.models import RetrievalResult, TextMatch
        from src.core.retrieval.router import KnowledgeRouter

        mock_gateway = AsyncMock()
        mock_gateway.search.return_value = [
            RetrievalResult(
                ko_id="1",
                title="Cell Biology",
                content_type="pdf",
                score=0.95,
                matches=[TextMatch(text="cells", chunk_index=0, score=0.95)],
            ),
        ]
        router = KnowledgeRouter(gateway=mock_gateway)
        results = await router.route_and_search(query="biology", workspace_id="ws-1")
        assert len(results) == 1
        assert results[0].title == "Cell Biology"

    async def test_route_and_search_legacy(self):
        from src.core.retrieval.router import KnowledgeRouter

        router = KnowledgeRouter()
        results = await router.route_and_search(query="biology")
        assert results == []


class TestPlannerIntegration:
    async def test_get_evidence_returns_package(self):
        from unittest.mock import AsyncMock

        from src.core.retrieval.gateway import RetrievalGateway
        from src.core.retrieval.models import EvidencePackage, RetrievalResult, TextMatch
        from src.core.retrieval.planner_integration import PlannerIntegrationService

        mock_gateway = AsyncMock(spec=RetrievalGateway)
        mock_gateway.search.return_value = [
            RetrievalResult(
                ko_id="1",
                title="Cell Biology",
                content_type="pdf",
                score=0.95,
                matches=[TextMatch(text="cells", chunk_index=0, score=0.95)],
            ),
        ]
        service = PlannerIntegrationService(gateway=mock_gateway)
        pkg = await service.get_evidence(query="biology")
        assert isinstance(pkg, EvidencePackage)
        assert pkg.query == "biology"
        assert len(pkg.sources) == 1
        assert pkg.sources[0].title == "Cell Biology"

    async def test_get_evidence_no_gateway(self):
        from src.core.retrieval.planner_integration import PlannerIntegrationService

        service = PlannerIntegrationService(gateway=None)
        pkg = await service.get_evidence(query="biology")
        assert pkg.total_results == 0
        assert pkg.degraded is True

    async def test_get_evidence_empty_results(self):
        from unittest.mock import AsyncMock

        from src.core.retrieval.gateway import RetrievalGateway
        from src.core.retrieval.planner_integration import PlannerIntegrationService

        mock_gateway = AsyncMock(spec=RetrievalGateway)
        mock_gateway.search.return_value = []
        service = PlannerIntegrationService(gateway=mock_gateway)
        pkg = await service.get_evidence(query="biology")
        assert pkg.total_results == 0
        assert len(pkg.sources) == 0
