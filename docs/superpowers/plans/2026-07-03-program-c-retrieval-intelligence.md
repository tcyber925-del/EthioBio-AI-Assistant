# Program C — Retrieval Intelligence Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 6-epic Retrieval Intelligence Platform (Gateway, Router, EvidencePackage, Citation, TrustRanking, PlannerIntegration) alongside the existing RAG pipeline.

**Architecture:** New `src/core/retrieval/` package per KASCS Services pattern. Thin facade over existing VectorStore + KnowledgeRegistry. Design doc at `docs/superpowers/specs/2026-07-03-program-c-retrieval-intelligence.md`.

**Tech Stack:** FastAPI, Pydantic v2, ChromaDB (existing VectorStore), asyncio, pytest.

**Key constraint — Strangler Fig:** No existing code modified except:
- `src/api/knowledge.py` — inline search → Gateway delegation (same response schema)
- `src/main.py` — register new router
All existing graph nodes, VectorStoreAdapter, and evidence modules stay untouched.

---

### Task 1: Retrieval Models (`src/core/retrieval/models.py`)

**Files:**
- Create: `src/core/retrieval/__init__.py`
- Create: `src/core/retrieval/models.py`
- Test: `tests/test_retrieval_platform.py` (new file, TestRetrievalModels class)

- [ ] **Step 1: Create package with models**

`src/core/retrieval/__init__.py`:
```python
from src.core.retrieval.models import (
    EvidencePackage,
    EvidenceSource,
    RetrievalResult,
    RoutingPlan,
    SourceCitation,
)

__all__ = [
    "EvidencePackage",
    "EvidenceSource",
    "RetrievalResult",
    "RoutingPlan",
    "SourceCitation",
]
```

`src/core/retrieval/models.py`:
```python
from __future__ import annotations

from pydantic import BaseModel


class TextMatch(BaseModel):
    text: str
    chunk_index: int
    score: float


class SourceCitation(BaseModel):
    ko_id: str
    title: str
    chunk_excerpt: str
    confidence_badge: str


class EvidenceSource(BaseModel):
    ko_id: str
    title: str
    content: str
    chunk_index: int
    confidence: float
    citation: SourceCitation


class EvidencePackage(BaseModel):
    query: str
    sources: list[EvidenceSource]
    total_results: int
    degraded: bool = False


class RetrievalResult(BaseModel):
    ko_id: str
    title: str
    content_type: str
    score: float
    matches: list[TextMatch]
    workspace_id: str | None = None
    enrichment: dict | None = None


class RoutingPlan(BaseModel):
    layers: list[str]
    primary_source: str
    strategy: str
```

- [ ] **Step 2: Write model tests**

Add to the end of `tests/test_knowledge_platform.py` or create `tests/test_retrieval_platform.py`:

```python
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
        r = RetrievalResult(
            ko_id="1", title="T", content_type="pdf", score=0.9, matches=[]
        )
        assert r.workspace_id is None
        assert r.enrichment is None

    def test_evidence_source_has_citation(self):
        c = SourceCitation(ko_id="1", title="T", chunk_excerpt="excerpt", confidence_badge="high")
        s = EvidenceSource(
            ko_id="1", title="T", content="content", chunk_index=0,
            confidence=0.95, citation=c,
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
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_retrieval_platform.py -v`
Expected: 5 passed

---

### Task 2: TrustRanker (C5)

**Files:**
- Create: `src/core/retrieval/ranking.py`
- Test: `tests/test_retrieval_platform.py` (TestTrustRanker class)

- [ ] **Step 1: Write TrustRanker tests**

```python
class TestTrustRanker:
    async def test_rerank_keeps_all_results(self):
        from src.core.retrieval.ranking import TrustRanker
        from src.core.retrieval.models import RetrievalResult, TextMatch

        ranker = TrustRanker()
        results = [
            RetrievalResult(ko_id="1", title="A", content_type="pdf", score=0.5, matches=[TextMatch(text="a", chunk_index=0, score=0.5)]),
            RetrievalResult(ko_id="2", title="B", content_type="txt", score=0.8, matches=[TextMatch(text="b", chunk_index=0, score=0.8)]),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        assert len(ranked) == 2

    async def test_rerank_sorts_by_score_descending(self):
        from src.core.retrieval.ranking import TrustRanker
        from src.core.retrieval.models import RetrievalResult, TextMatch

        ranker = TrustRanker()
        results = [
            RetrievalResult(ko_id="1", title="A", content_type="pdf", score=0.5, matches=[TextMatch(text="a", chunk_index=0, score=0.5)]),
            RetrievalResult(ko_id="2", title="B", content_type="txt", score=0.8, matches=[TextMatch(text="b", chunk_index=0, score=0.8)]),
            RetrievalResult(ko_id="3", title="C", content_type="pdf", score=0.6, matches=[TextMatch(text="c", chunk_index=0, score=0.6)]),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    async def test_rerank_boosts_enriched_results(self):
        from src.core.retrieval.ranking import TrustRanker
        from src.core.retrieval.models import RetrievalResult, TextMatch

        ranker = TrustRanker()
        results = [
            RetrievalResult(ko_id="1", title="A", content_type="pdf", score=0.7, matches=[TextMatch(text="a", chunk_index=0, score=0.7)]),
            RetrievalResult(ko_id="2", title="B", content_type="txt", score=0.7, matches=[TextMatch(text="b", chunk_index=0, score=0.7)], enrichment={"content_class": "lesson"}),
        ]
        ranked = ranker.rerank(results, workspace_id=None)
        assert ranked[0].ko_id == "2"
        assert ranked[0].score > 0.7

    async def test_rerank_boosts_workspace_match(self):
        from src.core.retrieval.ranking import TrustRanker
        from src.core.retrieval.models import RetrievalResult, TextMatch

        ranker = TrustRanker()
        ws = "ws-1"
        results = [
            RetrievalResult(ko_id="1", title="A", content_type="pdf", score=0.7, matches=[TextMatch(text="a", chunk_index=0, score=0.7)], workspace_id="ws-2"),
            RetrievalResult(ko_id="2", title="B", content_type="txt", score=0.7, matches=[TextMatch(text="b", chunk_index=0, score=0.7)], workspace_id=ws),
        ]
        ranked = ranker.rerank(results, workspace_id=ws)
        assert ranked[0].ko_id == "2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_retrieval_platform.py::TestTrustRanker -v`
Expected: 4 failed — `TrustRanker` not found

- [ ] **Step 3: Implement TrustRanker**

`src/core/retrieval/ranking.py`:
```python
from __future__ import annotations

import json

from src.core.retrieval.models import RetrievalResult

ENRICHMENT_BONUS = 0.05
WORKSPACE_MATCH_BONUS = 0.02
LESSON_REFERENCE_BONUS = 0.03


class TrustRanker:
    def rerank(
        self,
        results: list[RetrievalResult],
        workspace_id: str | None = None,
    ) -> list[RetrievalResult]:
        scored = [(self._score_with_boosts(r, workspace_id), r) for r in results]
        scored.sort(key=lambda x: -x[0])
        for s, r in scored:
            r.score = s
        return [r for _, r in scored]

    def _score_with_boosts(
        self, result: RetrievalResult, workspace_id: str | None
    ) -> float:
        score = result.score
        if result.enrichment:
            score += ENRICHMENT_BONUS
            content_class = result.enrichment.get("content_class")
            if content_class in ("lesson", "reference"):
                score += LESSON_REFERENCE_BONUS
        if workspace_id and result.workspace_id == workspace_id:
            score += WORKSPACE_MATCH_BONUS
        return score
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_retrieval_platform.py::TestTrustRanker -v`
Expected: 4 passed

---

### Task 3: RetrievalGateway (C1)

**Files:**
- Create: `src/core/retrieval/gateway.py`
- Test: `tests/test_retrieval_platform.py` (TestRetrievalGateway class)

- [ ] **Step 1: Write gateway tests**

```python
class TestRetrievalGateway:
    async def test_search_returns_results(self):
        from src.core.retrieval.gateway import RetrievalGateway
        from unittest.mock import AsyncMock, MagicMock

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query.return_value = {
            "documents": ["cell biology", "dna structure"],
            "metadatas": [
                {"knowledge_object_id": "ko-1", "chunk_index": 0},
                {"knowledge_object_id": "ko-1", "chunk_index": 1},
            ],
            "distances": [0.1, 0.2],
            "ids": ["ko-1:chunk:0", "ko-1:chunk:1"],
        }
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1", title="Cell Biology", content_type="pdf",
            workspace_id="ws-1", metadata={},
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
        from src.core.retrieval.gateway import RetrievalGateway
        from unittest.mock import AsyncMock, MagicMock

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query.return_value = {"documents": [], "metadatas": [], "distances": [], "ids": []}

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=AsyncMock(),
        )
        results = await gateway.search(q="nothing", workspace_id=None, limit=10)
        assert results == []

    async def test_search_filters_by_workspace(self):
        from src.core.retrieval.gateway import RetrievalGateway
        from unittest.mock import AsyncMock, MagicMock

        mock_embedder = AsyncMock()
        mock_embedder.embed_text.return_value = [0.1] * 384
        mock_vs = MagicMock()
        mock_vs.query.return_value = {
            "documents": ["cell biology"],
            "metadatas": [{"knowledge_object_id": "ko-1", "chunk_index": 0}],
            "distances": [0.1],
            "ids": ["ko-1:chunk:0"],
        }
        mock_registry = AsyncMock()
        mock_registry.get.return_value = MagicMock(
            id="ko-1", title="Cell Biology", content_type="pdf",
            workspace_id="ws-2", metadata={},
        )

        gateway = RetrievalGateway(
            embedder=mock_embedder,
            vector_store=mock_vs,
            registry=mock_registry,
        )
        results = await gateway.search(q="biology", workspace_id="ws-1", limit=10)
        assert len(results) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_retrieval_platform.py::TestRetrievalGateway -v`
Expected: 3 failed — `RetrievalGateway` not found

- [ ] **Step 3: Implement RetrievalGateway**

`src/core/retrieval/gateway.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.core.retrieval.models import RetrievalResult, TextMatch
from src.core.retrieval.ranking import TrustRanker

if TYPE_CHECKING:
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore
    from src.core.knowledge_registry.service import KnowledgeRegistry

logger = structlog.get_logger()


class RetrievalGateway:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        registry: KnowledgeRegistry,
        ranker: TrustRanker | None = None,
    ):
        self._embedder = embedder
        self._vector_store = vector_store
        self._registry = registry
        self._ranker = ranker or TrustRanker()

    async def search(
        self,
        q: str,
        workspace_id: str | None,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        query_embedding = await self._embedder.embed_text(q)
        raw = await self._vector_store.query(
            query_embedding,
            n_results=limit * 3,
        )
        if not raw["documents"]:
            return []

        seen: dict[str, dict] = {}
        for i in range(len(raw["documents"])):
            ko_id = raw["metadatas"][i].get("knowledge_object_id", "")
            score = 1.0 - raw["distances"][i]
            if ko_id not in seen:
                seen[ko_id] = {"score": score, "chunks": [], "ko_id": ko_id}
            else:
                seen[ko_id]["score"] = max(seen[ko_id]["score"], score)
            seen[ko_id]["chunks"].append(
                TextMatch(
                    text=raw["documents"][i],
                    chunk_index=raw["metadatas"][i].get("chunk_index", 0),
                    score=score,
                )
            )

        results: list[RetrievalResult] = []
        for entry in seen.values():
            ko = await self._registry.get(entry["ko_id"])
            if ko is None:
                continue
            if workspace_id and ko.workspace_id != workspace_id:
                continue
            enrichment_raw = ko.metadata.get("enrichment") if ko.metadata else None
            enrichment = None
            if enrichment_raw:
                import json
                try:
                    enrichment = json.loads(enrichment_raw)
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(
                RetrievalResult(
                    ko_id=entry["ko_id"],
                    title=ko.title,
                    content_type=ko.content_type,
                    score=entry["score"],
                    matches=entry["chunks"][:3],
                    workspace_id=ko.workspace_id,
                    enrichment=enrichment,
                )
            )

        results = self._ranker.rerank(results, workspace_id=workspace_id)
        return results[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_retrieval_platform.py::TestRetrievalGateway -v`
Expected: 3 passed

---

### Task 4: CitationFormatter (C4) + EvidencePackageBuilder (C3)

**Files:**
- Create: `src/core/retrieval/citation.py`
- Create: `src/core/retrieval/evidence_package.py`
- Test: `tests/test_retrieval_platform.py` (TestCitationFormatter, TestEvidencePackageBuilder)

- [ ] **Step 1: Write tests**

```python
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
        cit = SourceCitation(ko_id="1", title="Cell Biology", chunk_excerpt="Cells are...", confidence_badge="high")
        source = EvidenceSource(ko_id="1", title="Cell Biology", content="Cells are...", chunk_index=0, confidence=0.95, citation=cit)
        result = f.format_inline(source)
        assert "Cell Biology" in result
        assert "[high]" in result

    def test_format_footnote(self):
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.models import EvidenceSource, SourceCitation

        f = CitationFormatter()
        cit = SourceCitation(ko_id="1", title="Cell Biology", chunk_excerpt="Cells are...", confidence_badge="high")
        source = EvidenceSource(ko_id="1", title="Cell Biology", content="Cells are...", chunk_index=0, confidence=0.95, citation=cit)
        result = f.format_footnote(source, 1)
        assert "[1]" in result
        assert "Cell Biology" in result


class TestEvidencePackageBuilder:
    def test_build_from_results(self):
        from src.core.retrieval.evidence_package import EvidencePackageBuilder
        from src.core.retrieval.citation import CitationFormatter
        from src.core.retrieval.models import RetrievalResult, TextMatch

        builder = EvidencePackageBuilder(CitationFormatter())
        results = [
            RetrievalResult(
                ko_id="1", title="Cell Biology", content_type="pdf",
                score=0.95, matches=[TextMatch(text="Cells are the basic unit", chunk_index=0, score=0.95)],
            ),
        ]
        pkg = builder.build("what is a cell", results)
        assert pkg.query == "what is a cell"
        assert len(pkg.sources) == 1
        assert pkg.sources[0].title == "Cell Biology"
        assert pkg.sources[0].confidence == 0.95
        assert pkg.sources[0].citation.confidence_badge == "high"

    def test_build_empty_results(self):
        from src.core.retrieval.evidence_package import EvidencePackageBuilder
        from src.core.retrieval.citation import CitationFormatter

        builder = EvidencePackageBuilder(CitationFormatter())
        pkg = builder.build("nothing", [])
        assert pkg.total_results == 0
        assert pkg.sources == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_retrieval_platform.py::TestCitationFormatter tests/test_retrieval_platform.py::TestEvidencePackageBuilder -v`
Expected: 6 failed

- [ ] **Step 3: Implement CitationFormatter**

`src/core/retrieval/citation.py`:
```python
from __future__ import annotations

from src.core.retrieval.models import EvidenceSource, SourceCitation


class CitationFormatter:
    def format_badge(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "high"
        if confidence >= 0.7:
            return "medium"
        return "low"

    def format_inline(self, source: EvidenceSource) -> str:
        badge = source.citation.confidence_badge
        return f"{source.title} [{badge} confidence]"

    def format_footnote(self, source: EvidenceSource, index: int) -> str:
        badge = source.citation.confidence_badge
        return f"[{index}] {source.title} — \"{source.citation.chunk_excerpt}\" [{badge}]"

    def build_citation(
        self, ko_id: str, title: str, content: str, confidence: float
    ) -> SourceCitation:
        badge = self.format_badge(confidence)
        excerpt = content[:200]
        return SourceCitation(
            ko_id=ko_id,
            title=title,
            chunk_excerpt=excerpt,
            confidence_badge=badge,
        )
```

- [ ] **Step 4: Implement EvidencePackageBuilder**

`src/core/retrieval/evidence_package.py`:
```python
from __future__ import annotations

from src.core.retrieval.citation import CitationFormatter
from src.core.retrieval.models import EvidencePackage, EvidenceSource


class EvidencePackageBuilder:
    def __init__(self, formatter: CitationFormatter | None = None):
        self._formatter = formatter or CitationFormatter()

    def build(
        self,
        query: str,
        results: list,
        degraded: bool = False,
    ) -> EvidencePackage:
        sources: list[EvidenceSource] = []
        for r in results:
            chunk_text = r.matches[0].text if r.matches else ""
            citation = self._formatter.build_citation(
                ko_id=r.ko_id,
                title=r.title,
                content=chunk_text,
                confidence=r.score,
            )
            source = EvidenceSource(
                ko_id=r.ko_id,
                title=r.title,
                content=chunk_text,
                chunk_index=r.matches[0].chunk_index if r.matches else 0,
                confidence=r.score,
                citation=citation,
            )
            sources.append(source)

        return EvidencePackage(
            query=query,
            sources=sources,
            total_results=len(results),
            degraded=degraded,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_retrieval_platform.py::TestCitationFormatter tests/test_retrieval_platform.py::TestEvidencePackageBuilder -v`
Expected: 6 passed

---

### Task 5: API Router (`GET /api/v1/retrieval/search`) + Migrate Existing Search

**Files:**
- Create: `src/api/retrieval.py`
- Modify: `src/api/knowledge.py` (replace inline search with Gateway delegation)
- Test: `tests/test_retrieval_platform.py` (TestRetrievalAPI class)

- [ ] **Step 1: Write API integration tests**

```python
class TestRetrievalAPI:
    async def test_search_returns_evidence_package(self):
        from unittest.mock import AsyncMock, patch
        from src.api.retrieval import _get_gateway, _get_builder

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
        app = FastAPI()
        import src.api.retrieval as retrieval_module
        app.include_router(retrieval_module.router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/retrieval/search")
            assert resp.status_code == 422
```

- [ ] **Step 2: Implement retrieval router**

`src/api/retrieval.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.knowledge_registry.service import KnowledgeRegistry
from src.core.retrieval.evidence_package import EvidencePackageBuilder
from src.core.retrieval.gateway import RetrievalGateway
from src.core.retrieval.models import EvidencePackage

if TYPE_CHECKING:
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])

_registry: KnowledgeRegistry | None = None
_gateway: RetrievalGateway | None = None
_package_builder: EvidencePackageBuilder | None = None


def _get_registry() -> KnowledgeRegistry:
    global _registry
    if _registry is None:
        from src.database.session import async_session_factory
        _registry = KnowledgeRegistry(async_session_factory)
    return _registry


def _get_gateway() -> RetrievalGateway:
    global _gateway
    if _gateway is None:
        from src.config import settings
        from src.rag.embedder import Embedder
        from src.rag.vector_store import VectorStore

        _gateway = RetrievalGateway(
            embedder=Embedder(),
            vector_store=VectorStore(
                persist_directory=settings.vector_store_path,
                collection_name=settings.collection_name,
            ),
            registry=_get_registry(),
        )
    return _gateway


def _get_builder() -> EvidencePackageBuilder:
    global _package_builder
    if _package_builder is None:
        from src.core.retrieval.citation import CitationFormatter
        _package_builder = EvidencePackageBuilder(CitationFormatter())
    return _package_builder


@router.get("/search", response_model=EvidencePackage)
async def search(
    q: str = Query(..., min_length=1),
    workspace_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    results = await _get_gateway().search(q=q, workspace_id=workspace_id, limit=limit)
    pkg = _get_builder().build(query=q, results=results)
    return pkg
```

- [ ] **Step 3: Refactor existing `/knowledge/search` to delegate**

In `src/api/knowledge.py`, replace the inline search logic:

```python
@router.get("/search", response_model=list[SearchResult])
async def search_knowledge(
    q: str = Query(..., min_length=1),
    workspace_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    gateway = RetrievalGateway(
        embedder=Embedder(),
        vector_store=VectorStore(
            persist_directory=settings.vector_store_path,
            collection_name=settings.collection_name,
        ),
        registry=_get_registry(),
    )
    results = await gateway.search(q=q, workspace_id=workspace_id, limit=limit)
    return [
        SearchResult(
            ko_id=r.ko_id,
            title=r.title,
            content_type=r.content_type,
            score=r.score,
            matches=r.matches,
        )
        for r in results
    ]
```

Add imports at the top of `src/api/knowledge.py`:
```python
from src.core.retrieval.gateway import RetrievalGateway
```

Remove the old `_get_search_helpers()` function and the old inline search body (lines 99-156 replaced by above).

- [ ] **Step 4: Register router in main.py**

Add to `src/main.py`:
```python
from src.api.retrieval import router as retrieval_router
app.include_router(retrieval_router)
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_retrieval_platform.py tests/test_knowledge_platform.py -v`
Expected: all existing tests pass, new tests pass

---

### Task 6: KnowledgeRouter (C2) — Facade

**Files:**
- Create: `src/core/retrieval/router.py`
- Test: `tests/test_retrieval_platform.py` (TestKnowledgeRouter class)

- [ ] **Step 1: Write router tests**

```python
class TestKnowledgeRouter:
    async def test_route_with_workspace_returns_kml(self):
        from src.core.retrieval.router import KnowledgeRouter
        router = KnowledgeRouter()
        plan = await router.route(query="cell biology", workspace_id="ws-1", user_id=None)
        assert plan.primary_source == "kml"
        assert "workspace" in plan.layers

    async def test_route_without_workspace_returns_legacy(self):
        from src.core.retrieval.router import KnowledgeRouter
        router = KnowledgeRouter()
        plan = await router.route(query="cell biology", workspace_id=None, user_id=None)
        assert plan.primary_source == "legacy"
        assert "curriculum" in plan.layers
```

- [ ] **Step 2: Implement KnowledgeRouter**

`src/core/retrieval/router.py`:
```python
from __future__ import annotations

from src.core.retrieval.models import RoutingPlan


class KnowledgeRouter:
    async def route(
        self,
        query: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> RoutingPlan:
        if workspace_id:
            return RoutingPlan(
                layers=["workspace", "curriculum"],
                primary_source="kml",
                strategy="hybrid",
            )
        return RoutingPlan(
            layers=["curriculum"],
            primary_source="legacy",
            strategy="vector_only",
        )
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_retrieval_platform.py::TestKnowledgeRouter -v`
Expected: 2 passed

---

### Task 7: PlannerIntegrationService (C6)

**Files:**
- Create: `src/core/retrieval/planner_integration.py`
- Test: `tests/test_retrieval_platform.py` (TestPlannerIntegration class)

- [ ] **Step 1: Write planner integration tests**

```python
class TestPlannerIntegration:
    async def test_get_evidence_returns_package(self):
        from src.core.retrieval.planner_integration import PlannerIntegrationService
        from unittest.mock import AsyncMock, MagicMock

        mock_gateway = AsyncMock()
        mock_gateway.search.return_value = []
        mock_builder = MagicMock()
        mock_builder.build.return_value = MagicMock(query="test", sources=[], total_results=0)

        service = PlannerIntegrationService(gateway=mock_gateway, builder=mock_builder)
        pkg = await service.get_evidence(query="cell biology", workspace_id=None, limit=10)
        assert pkg is not None

    async def test_get_evidence_calls_search_with_correct_params(self):
        from src.core.retrieval.planner_integration import PlannerIntegrationService
        from unittest.mock import AsyncMock, MagicMock

        mock_gateway = AsyncMock()
        mock_gateway.search.return_value = []
        mock_builder = MagicMock()
        mock_builder.build.return_value = MagicMock(query="test", sources=[], total_results=0)

        service = PlannerIntegrationService(gateway=mock_gateway, builder=mock_builder)
        await service.get_evidence(query="cell biology", workspace_id="ws-1", user_id="user-1", limit=5)
        mock_gateway.search.assert_called_once_with(q="cell biology", workspace_id="ws-1", limit=5)
```

- [ ] **Step 2: Implement PlannerIntegrationService**

`src/core/retrieval/planner_integration.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.retrieval.evidence_package import EvidencePackageBuilder
    from src.core.retrieval.gateway import RetrievalGateway
    from src.core.retrieval.models import EvidencePackage


class PlannerIntegrationService:
    def __init__(
        self,
        gateway: RetrievalGateway,
        builder: EvidencePackageBuilder,
    ):
        self._gateway = gateway
        self._builder = builder

    async def get_evidence(
        self,
        query: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> EvidencePackage:
        results = await self._gateway.search(
            q=query,
            workspace_id=workspace_id,
            limit=limit,
        )
        return self._builder.build(query=query, results=results)
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_retrieval_platform.py::TestPlannerIntegration -v`
Expected: 2 passed

---

### Task 8: Update Package Exports + Full Test Run

- [ ] **Step 1: Update `src/core/retrieval/__init__.py`**

```python
from src.core.retrieval.citation import CitationFormatter
from src.core.retrieval.evidence_package import EvidencePackageBuilder
from src.core.retrieval.gateway import RetrievalGateway
from src.core.retrieval.models import (
    EvidencePackage,
    EvidenceSource,
    RetrievalResult,
    RoutingPlan,
    SourceCitation,
    TextMatch,
)
from src.core.retrieval.planner_integration import PlannerIntegrationService
from src.core.retrieval.ranking import TrustRanker
from src.core.retrieval.router import KnowledgeRouter

__all__ = [
    "RetrievalGateway",
    "KnowledgeRouter",
    "EvidencePackageBuilder",
    "CitationFormatter",
    "TrustRanker",
    "PlannerIntegrationService",
    "RetrievalResult",
    "EvidencePackage",
    "EvidenceSource",
    "SourceCitation",
    "RoutingPlan",
    "TextMatch",
]
```

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/test_retrieval_platform.py -v
```

Expected: all tests pass

```bash
python -m pytest tests/test_knowledge_platform.py -v
```

Expected: all 59 existing tests still pass

- [ ] **Step 3: Run ruff + mypy**

```bash
python -m ruff check src/core/retrieval/ src/api/retrieval.py
python -m mypy src/core/retrieval/ src/api/retrieval.py
```

Expected: clean

- [ ] **Step 4: Run full Platform test suite**

```bash
python -m pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"
```

Expected: no regressions
