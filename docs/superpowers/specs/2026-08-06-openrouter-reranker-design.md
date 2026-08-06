# OpenRouter Remote Reranker (Free Model, Prod-Safe)

> **REVISION (2026-08-06):** OpenRouter removed `nvidia/llama-nemotron-rerank-vl-1b-v2` from its rerank catalog (404 "No endpoints found"; catalog lists zero rerank models). Provider switched to **Jina AI** `jina-reranker-v3` (`https://api.jina.ai/v1/rerank`, free tier: 10M tokens per key, 100 RPM, multilingual 100+ langs). Class renamed `JinaReranker` in `src/core/retrieval/jina_reranker.py`; settings `jina_api_key`, `jina_reranker_base_url`, `jina_reranker_model`; identical request/response shape so batching + gateway fallback design below is unchanged.

Date: 2026-08-06
Status: Approved

## Problem

The active retrieval path (`RetrievalGateway.search` in
`src/core/retrieval/gateway.py`) runs vector-only search → KO grouping →
heuristic `TrustRanker` re-ranking. No cross-encoder reranking happens in prod.
The existing local reranker (`src/retrieval/reranker.py`, sentence-transformers
`cross-encoder/ms-marco-MiniLM-L-6-v2`) OOMs the 512Mi Render instance and is
only wired into the legacy ChromaDB/BM25 adapter (`src/retrieval/adapter.py`) —
not the active gateway. `ENABLE_RERANKER=false` is pinned in `render.yaml:59`.

## Goals

- Cross-encoder reranking for the active path using a **hosted** model
  (OpenRouter `/api/v1/rerank`) — zero in-process model, no OOM on 512Mi.
- Model: `nvidia/llama-nemotron-rerank-vl-1b-v2` (free per OpenRouter collection,
  1.7B, strong text relevance) — env-configurable.
- Graceful degradation: if the rerank API fails (no key, 4xx/5xx, timeout,
  network), retrieval falls back to current vector+TrustRanker scoring.
  **Retrieval must never 500 because reranking failed.**
- Reuse the existing `enable_reranker` setting; flip to `true` in prod env.

## Non-Goals

- No changes to the legacy ChromaDB/BM25 adapter or `src/retrieval/reranker.py`
  (local cross-encoder is left as-is for offline/local Chroma use).
- No hybrid BM25 fusion — rerank applies to the raw vector candidates.
- No attempt to rerank per-KO grouped results — we rerank raw chunks while they
  still carry their scores, then group.

## Design

### 1. Settings (`src/config.py`, OpenRouter block ~line 26)

| Field | Default | Notes |
|-------|---------|-------|
| `reranker_model` | `nvidia/llama-nemotron-rerank-vl-1b-v2` | OpenRouter slug |
| `reranker_top_n` | `30` | documents per API call (== `limit * 3`) |
| `reranker_batch_size` | `64` | documents per request (free model limits ~32K tokens/pair; chunk texts are ~1.5KB so 64 is safe) |

`enable_reranker` (already exists, default `True`) stays the master switch.

### 2. New `OpenRouterReranker` (`src/core/retrieval/openrouter_reranker.py`)

- Method `async rerank(query: str, documents: list[str]) -> list[float]` returning
  one relevance score per input document (order preserved by `index` from API).
- Uses `httpx.AsyncClient` (already a dependency), base URL + API key from
  `settings.openrouter_base_url` / `settings.openrouter_api_key`.
- POST `{base}/rerank` with JSON:
  `{"model": settings.reranker_model, "query": query, "documents": batch, "top_n": len(batch)}`.
- Response: `{"results": [{"index": i, "relevance_score": s, ...}]}` — map index →
  score into a full-length list (missing indices → 0.0).
- Batches documents by `reranker_batch_size`, aggregates scores.
- Raises `RerankError` (internal exception) on any non-200 / timeout / parse
  failure — the gateway catches it and falls back.

### 3. Gateway integration (`src/core/retrieval/gateway.py`)

- `RetrievalGateway.__init__` gains optional `reranker` param (default
  `None` → lazily construct `OpenRouterReranker()` when `settings.enable_reranker`
  and `settings.openrouter_api_key` are both set; else `None`).
- In `search()`: after `raw = await self._vector_store.query(...)` and before
  KO grouping, if `self._reranker` is active:
  1. Filter out empty/blank documents.
  2. `scores = await self._reranker.rerank(q, documents)`.
  3. Replace chunk scores: `score = rerank_score` (normalized by max score when
     rerank scores aren't already 0..1 — clamp to [0.01, 1.0] with a floor so
     zero-scored chunks rank last but still appear).
  4. Group by KO and average/max as today (`TrustRanker` still runs afterwards).
- Wrap the rerank call in `try/except RerankerError` → log warning
  (`reranker_failed_falling_back`) and continue with vector scores.
- Keep `TextMatch` metadata (chunk_index, page_number) intact — only scores change.

### 4. Config/docs

- `.env.example`: document `RERANKER_MODEL`, `RERANKER_TOP_N` (optional).
- `render.yaml:59`: set `ENABLE_RERANKER=true` (remote reranker, no OOM).
- AGENTS.md: no changes needed (no gotcha conflicts).

### 5. Tests

- New `tests/test_openrouter_reranker.py`:
  - Success: mock httpx client returns `{"results": [{"index": 1, "relevance": 0.9}, {"index": 0, "relevance": 0.5}]}` → `[0.5, 0.9]`.
  - Batching: 130 docs → 3 requests (64/64/2), scores merged in order.
  - Failure: 500 / timeout → raises `RerankerError`.
  - Missing index → 0.0 in output list.
- Update `tests/test_retrieval_platform.py` gateway tests:
  - `enable_reranker=True` + mocked `reranker` → `search()` calls rerank and uses
    its scores (assert score ordering).
  - `reranker.rerank` raises `RerankerError` → search still returns results with
    vector scores (no 500).
  - `enable_reranker=False` or no API key → reranker not constructed, scores
    unchanged (existing tests cover default).

## Error Handling

| Case | Behavior |
|------|----------|
| API 401/402/429/5xx | `RerankerError`, gateway falls back to vector scores |
| Timeout | `httpx.TimeoutException` → `RerankerError` |
| Malformed JSON | `RerankerError` |
| Empty documents | reranker skipped (no API call) |
| `rerank_score` outside [0,1] | clamp to [0.01, 1.0] |

## Testing

```bash
pytest tests/ -v -k "not slow"   # unit tests
ruff check . && mypy src/        # lint + typecheck
```

## References

- OpenRouter rerank API: `POST https://openrouter.ai/api/v1/rerank` (doc
  `docs/api/api-reference/rerank/create-rerank`) — request `{"model","query","documents","top_n"}`
- Collection `https://openrouter.ai/collections/rerank-models` — free
  `nvidia/llama-nemotron-rerank-vl-1b-v2`, rerank-2.5-lite, rerank-2.5, cohere v3.5
- `src/retrieval/reranker.py` — old local cross-encoder (kept)
- `render.yaml:59` — prod `ENABLE_RERANKER=false` flips to `true` with this feature