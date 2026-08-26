# Search Fanout Agent — Design Spec

## Project
EthioSci AI Assistant — Multi-Agent Agentic RAG Platform

## PRD
PRD-004 — Search Fanout Agent

## Status
Approved

---

## 1. Architecture

The Search Fanout Agent sits between QueryRewriter and the retrieval execution layer:

```
QueryRewriter → SearchFanoutAgent → asyncio.gather() → retrieved_chunks
```

It is a **rule-based router**, not an LLM-powered agent. No LLM calls. The routing is a dict lookup on `query.source_type`.

## 2. Component Tree

```
src/agents/search_fanout/
├── __init__.py          # exports
├── models.py            # RetrievalTask, RetrievalStrategy, RetrievalStrategyName
├── routing.py           # route_queries(), derive_strategy()
└── search_fanout.py     # SearchFanoutAgent
```

## 3. Models

### RetrievalTask
| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique task ID |
| `query` | str | The query string to execute |
| `target_source` | str | Curriculum/Memory/Learner/Recommendation |
| `priority` | int | 1-10 |
| `estimated_cost` | float | Reserved for future budgeting |
| `reasoning` | str | Why this query routes here |

### RetrievalStrategyName (enum)
SIMPLE, COMPARISON, PERSONALIZED, REMEDIATION, MULTI_HOP

### RetrievalStrategy
| Field | Type | Description |
|-------|------|-------------|
| `strategy_name` | str | From RetrievalStrategyName |
| `retrieval_mode` | str | "single" or "multi" |
| `parallel_execution` | bool | True unless single-source |
| `expected_sources` | list[str] | Sources this strategy targets |

## 4. Routing Logic

### route_queries(query_groups: dict[str, list[str]]) -> list[RetrievalTask]

Pure dict lookup. Each `query.source_type` maps to a retriever:

| source_type | target_source |
|-------------|---------------|
| curriculum | curriculum |
| memory | memory |
| misconception | memory |
| learner_profile | learner |
| recommendation | recommendation |
| comparison | curriculum |
| definition | curriculum |

Each query becomes a `RetrievalTask` with its priority copied from the `RewrittenQuery.priority`.

### derive_strategy(query_groups: dict[str, list[str]]) -> RetrievalStrategy

Inspects present source types:

| Sources Present | Strategy |
|----------------|----------|
| Only curriculum | SIMPLE |
| curriculum + comparison | COMPARISON |
| Includes memory | PERSONALIZED |
| Includes recommendation | REMEDIATION |
| 3+ sources | MULTI_HOP |

## 5. Retriever Implementation

| Retriever | Status | Implementation |
|-----------|--------|----------------|
| Curriculum | Live | VectorStoreAdapter (existing Chroma) |
| Memory | Stub | `async def _memory_search(): return []` |
| Learner | Stub | `async def _learner_search(): return {}` |
| Recommendation | Stub | `async def _recommendation_search(): return []` |

Stubs are clearly marked with `TODO: Implement real retriever`. Their empty results will trigger the sufficiency iteration loop naturally.

## 6. Node Integration

`SearchFanoutNode.__call__()` (refactored):
1. Instantiate `SearchFanoutAgent` if not already
2. Call `agent.plan(query_groups)` → `(tasks, strategy)`
3. Map tasks to retriever callables
4. Execute via `asyncio.gather()`
5. Merge results into `state.retrieved_chunks`
6. Set `state.retrieval_tasks`, `state.retrieval_strategy`

Wired into `query_rewriter → search_fanout` inside `plan_executor`'s per-subtask loop.

## 7. State Changes

Add to `AgentState`:
- `retrieval_strategy: dict` — serialized RetrievalStrategy
- `retrieval_source_results: dict[str, list[dict]]` — per-source raw results

## 8. Budget Limits

| Parameter | Default |
|-----------|---------|
| `MAX_QUERIES` | 20 (hard cap) |
| `MAX_SOURCES` | 4 |
| `MAX_PARALLEL` | 4 (no semaphore needed for asyncio.gather) |

## 9. Error Handling

- Per-source failures caught individually — other sources continue
- `_safe_search()` wrapper logs warning, returns `[]` for failed source
- No retry at this layer (iteration loop handles gaps)

## 10. Testing

- `tests/agents/test_search_fanout.py` — models, routing, derive_strategy, agent
- Existing `SearchFanoutNode` tests updated in `tests/test_agentic_nodes.py`
- Target: >90% coverage on routing + derive_strategy

## 11. Dependencies

- PRD-003 (Query Rewriter) — consumed
- VectorStoreAdapter — existing dependency for curriculum
