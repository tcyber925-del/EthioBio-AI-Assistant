# Evidence Graph Node — Design Spec

**Date:** 2026-06-09
**Status:** Draft
**PRD:** PRD-005 — Evidence Graph LangGraph Node

## Architecture

```
planner → plan_executor → evidence_graph → sufficient_context → synthesis → ...
```

The `EvidenceGraphNode` normalizes raw retrieval output into persisted, selected, and scored evidence records before SufficientContextNode evaluates sufficiency.

## Component: `EvidenceGraphNode` (`src/graph/nodes/evidence_graph.py`)

A LangGraph node that wires existing Evidence Graph infrastructure into the pipeline.

### Step-by-step flow

1. **Get or create EvidenceSession** — keyed by `state.trace_id` (with `state.session_id` as fallback). Calls `EvidenceGraph.create_session()` if no existing session found.

2. **Persist evidence records** — iterates `state.retrieval_source_results` and persists each chunk as an `EvidenceRecord` via `EvidenceGraph.add()`. Skips chunks already persisted (dedup by content hash or chunk_id).

3. **Select best evidence** — calls `EvidenceSelector.select_for_generation()` with the session's evidence IDs. Sets `state.evidence_ids` to the selected subset (replacing the heuristic extraction in `SearchFanoutNode`).

4. **Analyze coverage** — calls `scoring.analyze_coverage()` to compute `state.coverage_score` and `state.missing_information` (replacing the simple average in `SearchFanoutNode`).

5. **Summarize** — calls `summarizer.summarize_evidence()` to set `state.evidence_summary` (replacing the template string in `PlanExecutor`).

### State changes

| Field | How it's set | Before (current heuristic) | After (new) |
|-------|-------------|-------------------|-------------|
| `evidence_ids` | `selector.select_for_generation()` | From chunk metadata in SearchFanoutNode | Selected from persisted records via weighted scoring |
| `coverage_score` | `scoring.analyze_coverage()` | Average of chunk scores in SearchFanoutNode | Word-split coverage analysis |
| `missing_information` | `scoring.detect_missing_information()` | Set by SufficientContextNode from heuristic | Structured gap detection from coverage |
| `evidence_summary` | `summarizer.summarize_evidence()` | Template string in PlanExecutor | Structured summary with source distribution |

### Constructor

```python
class EvidenceGraphNode:
    def __init__(
        self,
        db_session_factory=None,
        router: Optional[ModelRouter] = None,
    ):
        self.db_session_factory = db_session_factory
        self.selector = EvidenceSelector(router=router)
        self.graph = EvidenceGraph(db_session_factory) if db_session_factory else None
```

`db_session_factory` is a callable that returns an async SQLAlchemy session, or `None` for fallback mode. When `None`, the node skips persistence and falls back to heuristic evidence selection (same behavior as before). The `router` is optional — `EvidenceSelector` falls back to heuristic ranking without it.

## Graph wiring

### `build_agentic_graph()` (lines 55-107)

Add after `plan_executor` edge (line 88):
```python
workflow.add_node("evidence_graph", EvidenceGraphNode(db_session, router))
workflow.add_edge("plan_executor", "evidence_graph")
workflow.add_edge("evidence_graph", "sufficient_context")
```

Change line 88 from:
```python
workflow.add_edge("plan_executor", "sufficient_context")
```
to:
```python
workflow.add_edge("plan_executor", "evidence_graph")
```

### `build_unified_graph()` (lines 227-294)

Same change — add node, wire after `plan_executor`, update the `plan_executor` edge to point to `evidence_graph` instead of `sufficient_context`.

## Fallback behavior

The node MUST never crash the pipeline. Three fallback levels:

1. **DB available (ideal):** Session created, records persisted, selector runs, coverage analyzed, summary generated
2. **DB unavailable:** `EvidenceGraph` constructor receives `None` or raises on `create_session` — node catches the exception, logs a warning, and falls back to the existing heuristic logic (same as current `SearchFanoutNode` behavior)
3. **Selector unavailable (no router):** `EvidenceSelector` falls back to greedy selection without LLM tie-breaking

The fallback is a constructor-time decision: `EvidenceGraphNode(db_session_factory=None)` means "heuristic mode" with no persistence.

## What gets replaced (heuristic code)

| Location | Lines | Code | Replaced by |
|----------|-------|------|------------|
| `search_fanout.py:156-162` | 7 | Heuristic `evidence_ids` from chunk metadata | `selector.select_for_generation()` |
| `search_fanout.py:149-154` | 6 | Average coverage score | `scoring.analyze_coverage()` |
| `plan_executor.py:73-75` | 3 | Template `evidence_summary` | `summarizer.summarize_evidence()` |

The heuristic code stays in place but is only reached when `EvidenceGraphNode` is in fallback mode.

## Files

| Action | Path |
|--------|------|
| Create | `src/graph/nodes/evidence_graph.py` |
| Modify | `src/graph/orchestrator.py` — add node + edges in both graph builders |
| Modify | `src/graph/nodes/search_fanout.py` — remove heuristic `evidence_ids`/`coverage_score` (optional cleanup) |
| Modify | `src/graph/nodes/plan_executor.py` — remove template `evidence_summary` (optional cleanup) |
| Create | `tests/test_evidence_graph_node.py` |

## Test Plan

- `test_node_creates_session`: Verify session is created from `trace_id`
- `test_node_persists_records`: Verify chunks become EvidenceRecords
- `test_node_selects_evidence`: Verify `state.evidence_ids` populated from selector
- `test_node_analyzes_coverage`: Verify `state.coverage_score` set from coverage analysis
- `test_node_summarizes`: Verify `state.evidence_summary` populated
- `test_node_fallback_no_db`: Verify falls back to heuristic when DB unavailable
- `test_node_skip_duplicates`: Verify duplicate chunks not re-persisted
- `test_graph_wiring`: Verify edge exists in compiled graph
