# Program C — Retrieval Intelligence Platform

**Date:** 2026-07-03
**Status:** Draft
**Depends on:** Programs A (Foundation) + B (Processing) + E (Enrichment)

## Architecture

New `src/core/retrieval/` package per KASCS Services pattern (CONTEXT.md §66-67).
API router at `src/api/retrieval.py`.

```
src/core/retrieval/
├── __init__.py           # exports RetrievalGateway, KnowledgeRouter, CitationFormatter, etc.
├── models.py             # RetrievalResult, EvidencePackage, Citation, RoutingPlan
├── gateway.py            # C1 — RetrievalGateway
├── router.py             # C2 — KnowledgeRouter (facade)
├── evidence_package.py   # C3 — EvidencePackageBuilder
├── citation.py           # C4 — CitationFormatter
├── ranking.py            # C5 — TrustRanker
└── planner_integration.py  # C6 — PlannerIntegrationService
```

## C1 — RetrievalGateway

Encapsulates the current inline search logic (`src/api/knowledge.py:search_knowledge`) into a reusable service. Replaces the inline search with a `RetrievalGateway.search()` call.

```
Gateway
  ├── embed query (via Embedder)
  ├── query vector store (via VectorStore, with workspace filter in metadata)
  ├── enrich results with KO metadata (via KnowledgeRegistry.get)
  ├── deduplicate by KO ID
  ├── pass through TrustRanker for re-ranking
  └── return list[RetrievalResult]
```

RetrievalResult model:
```python
class RetrievalResult(BaseModel):
    ko_id: str
    title: str
    content_type: str
    score: float
    matches: list[TextMatch]  # existing
    workspace_id: str | None
    enrichment: dict | None   # from KO metadata.enrichment
```

## C2 — KnowledgeRouter (facade)

Thin routing facade (CONTEXT.md §12-13) that wraps existing agentic pipeline + new KML gateway.

- `route(query, workspace_id, user_id)` → `RoutingPlan(layers, sources, strategy)`
- For new KML consumers (Program D/E/F): routes through RetrievalGateway with workspace context
- For legacy consumers: delegates to existing `_route_after_orchestrator` unchanged
- Layer detection: if `workspace_id` is present → KML path, else → legacy path

RoutingPlan model:
```python
class RoutingPlan(BaseModel):
    layers: list[str]         # ["workspace", "curriculum", ...]
    primary_source: str       # "kml" or "legacy"
    strategy: str             # "vector_only" | "hybrid"
```

## C3 — EvidencePackage Engine

New Pydantic model for KML path only (CONTEXT.md §48-49). The existing `EvidenceGraph` (`src/core/evidence/`) persists evidence for the Agentic RAG pipeline — EvidencePackage is a *response format*, not a storage model.

Pipeline: `RetrievalResult[] → EvidencePackageBuilder → EvidencePackage`

EvidencePackage model:
```python
class EvidenceSource(BaseModel):
    ko_id: str
    title: str
    content: str              # chunk text
    chunk_index: int
    confidence: float
    citation: SourceCitation  # from CitationFormatter

class EvidencePackage(BaseModel):
    query: str
    sources: list[EvidenceSource]
    total_results: int
    degraded: bool            # True if any source lookup failed
```

## C4 — CitationFormatter

Additive service (CONTEXT.md §84-85). Transforms EvidenceSource records into structured citations.

```python
class SourceCitation(BaseModel):
    ko_id: str
    title: str
    chunk_excerpt: str        # first 200 chars of content
    confidence_badge: str     # "high" / "medium" / "low"

class CitationFormatter:
    def format_inline(source: EvidenceSource) -> str
    def format_footnote(source: EvidenceSource, index: int) -> str
    def format_badge(confidence: float) -> str
```

Confidence mapping: `≥0.9 → "high"`, `≥0.7 → "medium"`, else `"low"`.

## C5 — TrustRanker

Re-ranks RetrievalResult[] before returning. Builds on existing `evidence/scoring.py` weights.

```python
class TrustRanker:
    def rerank(results: list[RetrievalResult], workspace_id: str | None) -> list[RetrievalResult]
```

Factors:
- Base score from vector distance (inherited)
- Source quality boost: KOs with enrichment metadata get +0.05
- Workspace match bonus: if KO workspace matches query workspace, +0.02
- Enrichment bonus: KOs with content_class "lesson" or "reference" get +0.03
- Recency: KOs created within last 7 days get +0.01 (requires KO.created_at)

## C6 — PlannerIntegrationService

Bridge to `AgentOrchestrator` (src/core/agent_orchestrator/). Converts EvidencePackage → format the orchestrator consumes.
Also exposes a convenience method that the LangGraph nodes (SearchFanoutNode, RetrievalNode) can call without knowing KML internals.

```python
class PlannerIntegrationService:
    async def get_evidence(
        query: str,
        workspace_id: str | None,
        user_id: str | None,
        limit: int = 10,
    ) -> EvidencePackage
```

The orchestrator calls `get_evidence()` instead of calling `VectorStoreAdapter.search()` directly when the request has workspace context. Existing graph nodes unchanged — this is opt-in by the caller.

## API Changes

1. **New: `GET /api/v1/retrieval/search`** — wraps RetrievalGateway + EvidencePackageBuilder
   - Query params: `q`, `workspace_id`, `limit`, `format` (raw | evidence | citation)
   - `format=raw` → list[RetrievalResult] (backward compat with existing `/search`)
   - `format=evidence` → EvidencePackage
   - `format=citation` → EvidencePackage with formatted citations in each source

2. **Migrate:** `GET /api/v1/knowledge/search` → delegates to `GET /api/v1/retrieval/search?format=raw`
   - Keep `GET /api/v1/knowledge/search` working, rewire internals to Gateway

3. **Backward compat:** `GET /api/v1/knowledge/search` keeps its exact `list[SearchResult]` response schema. Only its internal implementation changes from inline code → Gateway delegation. All existing query params (`q`, `workspace_id`, `limit`) preserved. Clients see zero behavior change.

## Integration with Existing Systems

| Component | Interaction |
|-----------|-------------|
| `KnowledgeRegistry` | Gateway calls `registry.get()` for KO metadata enrichment |
| `VectorStore` | Gateway calls `vector_store.query()` for initial retrieval |
| `Embedder` | Gateway calls `embedder.embed_text()` for query encoding |
| `EvidenceGraph` (src/core/evidence/) | Unchanged — EvidencePackage is response format, not storage |
| `AgentOrchestrator` | PlannerIntegrationService provides evidence packages |
| `SearchFanoutNode` / `RetrievalNode` | Unchanged — they continue using `VectorStoreAdapter.search()` directly |

## Strangler Fig Rules

- `VectorStoreAdapter.search()` is NOT modified
- `SearchFanoutNode`, `RetrievalNode`, `TutorNode` are NOT modified
- New `/retrieval/search` endpoint does NOT modify existing `/knowledge/search`
- Existing `/knowledge/search` becomes a thin delegation to Gateway (no behavior change)
- `KnowledgeRouter` only activates for new KML consumers — legacy path unchanged

## Testing

- **Unit tests** for each component: Gateway, Router, EvidencePackageBuilder, CitationFormatter, TrustRanker
- **Integration test** for new `GET /api/v1/retrieval/search` endpoint
- **Sniff test:** existing `/knowledge/search` still works (delegation)
- 59 existing tests continue passing

## Implementation Order

1. Models (`models.py`) — RetrievalResult, EvidencePackage, SourceCitation, RoutingPlan
2. C1 Gateway + C5 TrustRanker (core retrieval with re-ranking)
3. C3 EvidencePackageBuilder + C4 CitationFormatter (response formatting)
4. API endpoint + migration of existing `/knowledge/search`
5. C2 KnowledgeRouter (delegation facade)
6. C6 PlannerIntegrationService (orchestrator bridge)
