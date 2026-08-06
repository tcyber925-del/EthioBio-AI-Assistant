# OpenRouter Remote Reranker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **REVISION (2026-08-06):** OpenRouter dropped `nvidia/llama-nemotron-rerank-vl-1b-v2` from its rerank catalog (returns 404 "No endpoints found"). Switched provider to **Jina AI** `jina-reranker-v3` via `https://api.jina.ai/v1/rerank` — free tier (10M tokens per key, 100 RPM). Code: `src/core/retrieval/jina_reranker.py` (class `JinaReranker`), settings `jina_api_key` / `jina_reranker_base_url` / `jina_reranker_model`, gateway lazy-constructs when `enable_reranker` + `jina_api_key`. Response shape (`results[].index`/`relevance_score`) identical, so batching/fallback logic is unchanged.

**Goal:** Add cross-encoder reranking to the active retrieval path (`RetrievalGateway.search`) using Jina AI's hosted `/v1/rerank` with the free-tier `jina-reranker-v3`, with graceful fallback so retrieval never 500s when reranking fails. Flip `ENABLE_RERANKER=true` in prod.

**Architecture:** New `src/core/retrieval/jina_reranker.py` (httpx client, batched, raises `RerankerError` on failure). `RetrievalGateway` gets an optional `reranker` param; when `settings.enable_reranker` + `jina_api_key` are set, `search()` reranks raw chunk candidates before KO grouping and replaces chunk scores (clamped), falling back to vector scores on `RerankerError`.

**Tech Stack:** Python 3.12+, httpx (already dep), Jina base URL + key from settings, pytest-asyncio, ruff, mypy.

---

### Task 1: Settings + `.env.example`

**Files:**
- Modify: `src/config.py` (OpenRouter block, line ~26)
- Modify: `.env.example` (OpenRouter section)

- [ ] **Step 1: Add settings fields**

```python
    openrouter_reranker_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2"
    reranker_top_n: int = 30
    reranker_batch_size: int = 64
```

- [ ] **Step 2: `.env.example` documentation**

```
# Reranker (OpenRouter hosted; free model default)
OPENROUTER_RERANKER_MODEL=nvidia/llama-nemotron-rerank-vl-1b-v2
ENABLE_RERANKER=true
```

- [ ] **Step 3: Verify** — `python -c "from src.config import settings; print(settings.openrouter_reranker_model)"` prints the slug

- [ ] **Step 4: Commit**
```bash
git add src/config.py .env.example
git commit -m "feat(config): openrouter reranker settings (model, top_n, batch)"
```

---

## Task 2: Failing tests for `OpenRouterReranker`

**Files:**
- Create: `tests/test_openrouter_reranker.py`

- [ ] **Step 1: Write the tests**

```python
import pytest
from httpx import RequestError, Response

from src.core.retrieval.openrouter_reranker import (
    OpenRouterReranker,
    RerankerError,
)


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


def _json_response(payload):
    r = httpx.Response(200, json=payload)
    r._content = json.dumps(payload).encode()
    return r


# (tests below use the constructor param `_client` injected via monkeypatch on the module httpx.AsyncClient)


async def test_rerank_returns_scores_in_index_order(monkeypatch):
    def fake_client(*a, **k):
        return _FakeClient([
            ...  # single response {"results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.5}]}
        ])
    monkeypatch.setattr(httpx, "AsyncClient", fake_client)
    r = OpenRouterReranker()
    out = await r.rerank("query", ["doc_a", "doc_b"])
    assert out == pytest.approx([0.5, 0.9])


async def test_rerank_batches_documents(monkeypatch):
    # 130 docs with batch_size patched to 64 -> 3 requests (64/64/2)
    ...


async def test_rerank_raises_on_api_error(monkeypatch):
    # response 500 -> RerankerError
    with pytest.raises(RerankerError):
        await OpenRouterReranker().rerank("q", ["a"])


async def test_rerank_raises_on_timeout(monkeypatch):
    # fake client raises httpx.TimeoutException -> RerankerError


async def test_missing_index_fills_zero(monkeypatch):
    # results omit index 1 -> [0.9, 0.0]
```

- [ ] **Step 2: Run to verify failing** — `pytest tests/test_openrouter_reranker.py -v`
  Expected: IMPORT ERROR (module doesn't exist)

- [ ] **Step 3: Commit failing tests**
```bash
git add tests/test_openrouter_reranker.py
git commit -m "test(retrieval): failing tests for OpenRouter reranker"
```

---

## Task 3: Implement `OpenRouterReranker`

**Files:**
- Create: `src/core/retrieval/openrouter_reranker.py`

- [ ] **Step 1: Write the module**

```python
"""OpenRouter-hosted document reranker.

Calls POST {base}/rerank with {model, query, documents, top_n}. Free model
default: nvidia/llama-nemotron-rerank-vl-1b-v2. Failures raise RerankerError
(never crash retrieval — the gateway catches it and falls back).
"""
from __future__ import annotations

import structlog
import httpx
from src.config import settings

logger = structlog.get_logger(__name__)


class RerankerError(Exception):
    pass


class OpenRouterReranker:
    def __init__(self):
        self.model = settings.openrouter_reranker_model
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.batch_size = settings.reranker_batch_size

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        scores = [0.0] * len(documents)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for idx in range(0, len(documents), self.batch_size):
            batch = documents[idx : idx + self.batch_size]
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    resp = await client.post(
                        f"{self.base_url}/rerank",
                        headers=headers,
                        json={
                            "model": self.model,
                            "query": query,
                            "documents": batch,
                            "top_n": len(batch),
                        },
                    )
                if resp.status_code != 200:
                    raise RerankerError(f"openrouter rerank HTTP {resp.status_code}")
                results = resp.json().get("results", [])
                for item in results:
                    index = item.get("index")
                    if index is not None and idx + index < len(scores):
                        scores[idx + index] = float(item.get("relevance_score") or 0.0)
            except httpx.HTTPError as e:
                raise RerankerError(f"openrouter rerank request failed: {e}") from e
        return scores
```

- [ ] **Step 2: Run tests** — `pytest tests/test_openrouter_reranker.py -v` → all PASS

- [ ] **Step 3: Lint + typecheck** — `ruff check src/core/retrieval/openrouter_reranker.py && mypy src/core/retrieval/openrouter_reranker.py`

- [ ] **Step 4: Commit**
```bash
git add src/core/retrieval/openrouter_reranker.py
git commit -m "feat(retrieval): OpenRouter hosted reranker with error propagation"
```

---

## Task 4: Wire into `RetrievalGateway` + fallback

**Files:**
- Modify: `src/core/retrieval/gateway.py`
- Modify: `tests/test_retrieval_platform.py`

- [ ] **Step 1: Write failing/updated gateway tests**

In `tests/test_retrieval_platform.py`, add to `TestRetrievalGateway`:

```python
async def test_search_uses_reranker_when_enabled(self, monkeypatch):
    # enable_reranker + openrouter_api_key set; mocked _reranker
    ...

async def test_search_falls_back_when_reranker_raises(self, monkeypatch):
    # _reranker.rerank side_effect = RerankerError -> results returned with vector scores
    ...

async def test_search_no_reranker_when_disabled(self, monkeypatch):
    # settings.enable_reranker=False -> construct with default reranker=None
    ...
```

- [ ] **Step 2: Implement gateway changes**

```python
from src.core.retrieval.openrouter_reranker import OpenRouterReranker, RerankerError

class RetrievalGateway:
    def __init__(self, embedder, vector_store, registry, ranker=None, reranker=None):
        ...
        self._reranker = reranker
        if self._reranker is None and settings.enable_reranker and settings.openrouter_api_key:
            self._reranker = OpenRouterReranker()

    async def search(self, q, workspace_id, limit=10):
        query_embedding = await self._embedder.embed_text(q)
        raw = await self._vector_store.query(query_embedding, n_results=limit * 3)
        if not raw["documents"]:
            return []

        scores = None
        if self._reranker is not None:
            try:
                scores = await self._reranker.rerank(q, raw["documents"])
            except RerankerError:
                logger.warning("reranker_failed_falling_back", q=q[:50])
            except Exception:
                logger.warning("reranker_failed_falling_back", q=q[:50])

        seen = {}
        for i in range(len(raw["documents"])):
            ko_id = raw["metadatas"][i].get("knowledge_object_id", "")
            if scores is not None and i < len(scores):
                rs = scores[i]
                if rs > 0:
                    score = min(1.0, max(0.01, rs))
                else:
                    score = max(0.01, 1.0 - raw["distances"][i])
                    score = 0.4 * score  # de-prioritize zero-rerank chunks
            else:
                score = 1.0 - raw["distances"][i]
            ... (rest unchanged: grouping, TrustRanker, slicing)
```

(gateway currently imports `settings` inside `__init__` lazily to avoid test env issues — follow the same lazy pattern.)

- [ ] **Step 3: Run tests** — `pytest tests/test_retrieval_platform.py -v` → green; `pytest tests/ -k "not slow"` → all green

- [ ] **Step 4: Commit**
```bash
git add src/core/retrieval/gateway.py tests/test_retrieval_platform.py
git commit -m "feat(retrieval): wire OpenRouter reranker into gateway with fallback"
```

---

## Task 5: Enable in prod + docs

**Files:**
- Modify: `render.yaml` (line ~59)
- Modify: `.env.example`
- (Optional) `docs/runbook.md`

- [ ] **Step 1: `render.yaml`** — change `ENABLE_RERANKER=false` → `ENABLE_RERANKER=true`

- [ ] **Step 2: Commit**
```bash
git add render.yaml
git commit -m "chore(render): enable hosted reranker (free model) in prod"

# (then push -> CI -> GHCR build -> Render hook deploy)
```

- [ ] **Step 3: Verify prod**

```bash
curl https://ethiobio-api.onrender.com/health
curl "https://ethiobio-api.onrender.com/api/v1/knowledge/search?q=mitosis&workspace_id=a543a7e7-9385-473e-b840-20db474ce8df"
```
Then check Render logs after a search: expect `reranker_applied` / `reranker_failed_falling_back` line. Confirm no OOM (hosted model, no in-process weights).

- [ ] **Step 4: Full suite + CI**

```bash
pytest tests/ -v -k "not slow"
ruff check . && mypy src/
git push   # CI green
```

---

## Self-Review

**Spec coverage:**
- Settings → Task 1 ✓
- Reranker module + batching + error types → Task 3 ✓
- Gateway integration + fallback → Task 4 ✓
- `ENABLE_RERANKER=true` in prod → Task 5 ✓
- Free model default → `src/config.py` ✓
- Legacy `src/retrieval/reranker.py` untouched ✓

**Placeholders:** The `workspace_id` in Task 5 step 3 — verify actual value (handoff used `a543a7e7-9385-473e-b840-20db474ce8df`; fix typo if needed).

**Type consistency:** `rerank(query: str, documents: list[str]) -> list[float]` — length matches input; gateway indexes with `i < len(scores)`. `RerankerError` raised for HTTP errors and timeouts, caught by gateway. `scores is None` sentinel distinguishes "reranker disabled" from "didn't run".