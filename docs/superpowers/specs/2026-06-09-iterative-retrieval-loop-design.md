# Iterative Retrieval Loop — Design Spec

**Date:** 2026-06-09
**Status:** Draft
**PRD:** PRD-007 — Iterative Retrieval Loop

## Architecture

```
sufficient_context → RetrievalLoopController.decide()
    ├── CONTINUE           → plan_executor (or planner for major gaps — normal routing)
    ├── MAX_ITERATIONS     → synthesis                   (override, always stop)
    ├── NO_PROGRESS        → synthesis                   (override, always stop)
    └── NO_NEW_EVIDENCE    → synthesis                   (override, always stop)
```

The existing graph topology (edges `synthesis` / `rewrite` / `replan` from `sufficient_context`) remains unchanged. Only the **termination decision logic** inside `SufficientContextNode` changes — it delegates to `RetrievalLoopController` instead of inline hardcoded constants.

On re-entry, `PlanExecutor` reads `retrieval_feedback` to refine subtask objectives for more targeted retrieval.

## Components

### 1. `RetrievalLoopController` (`src/core/loops/controller.py`)

Stateless. Single method:

```python
@dataclass
class LoopDecision:
    should_continue: bool
    reason: str  # CONTINUE | MAX_ITERATIONS | NO_PROGRESS | NO_NEW_EVIDENCE

class RetrievalLoopController:
    def decide(self, state: AgentState) -> LoopDecision:
```

Decision order (first match wins):

1. **Max iterations:** `state.retrieval_iterations >= state.max_iterations` (default 3) → stop with `MAX_ITERATIONS`
2. **No progress:** `coverage_gain < 0.02` for 2 consecutive iterations → stop with `NO_PROGRESS`
   - Coverage gain = `state.coverage_score - state.coverage_history[-1]` (if history non-empty)
3. **No new evidence:** total evidence count unchanged from previous iteration → stop with `NO_NEW_EVIDENCE`
   - Uses `state.previous_evidence_count` comparison
4. **Default:** continue with `CONTINUE`

Note: sufficiency is NOT checked here — `evaluate_sufficiency` already routes to `"synthesis"` (ending the loop) when coverage is sufficient. The controller only adds the 3 hard-stop criteria that override normal routing.

`coverage_gain` uses the last value in `state.coverage_history`, which is appended BEFORE the controller runs each iteration.

### 2. `FeedbackProcessor` (`src/core/loops/feedback_processor.py`)

```python
class FeedbackProcessor:
    def process(self, state: AgentState) -> list[str]:
        """
        Converts missing_information + coverage_analysis into
        targeted retrieval directives for the next iteration.
        Each gap generates one directive string.
        """
```

Rules:
- Each item in `state.missing_information` becomes `"Find information about: {gap}"`
- If `state.missing_information` is empty but coverage is low, generates `"Broaden search for {topic}"`
- Directives are stored in `state.retrieval_feedback`
- Called by `SufficientContextNode` after evaluating sufficiency (before setting `requires_iteration`)

### 3. Telemetry (`src/core/loops/telemetry.py`)

```python
def record_loop_decision(state: AgentState) -> dict:
    """Return loop metrics dict for PipelineMonitor."""
    return {
        "iteration": state.retrieval_iterations,
        "coverage": state.coverage_score,
        "sufficiency": state.sufficiency_score,
        "termination": state.termination_reason,
        "evidence_count": len(state.evidence_ids),
        "coverage_history": state.coverage_history,
    }
```

Called by `SufficientContextNode` after controller decision. Metrics are emitted via `PipelineMonitor.log_metric()`.

## AgentState Changes

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `max_iterations` | `int` | `3` | Configurable per-request cap |
| `coverage_history` | `list[float]` | `[]` | Per-iteration coverage scores |
| `termination_reason` | `str` | `""` | Why the loop stopped |
| `retrieval_feedback` | `list[str]` | `[]` | Gap-targeted directives for PlanExecutor |

## Integration Points

### `SufficientContextNode`

Current flow:
```
evaluate_sufficiency() → set requires_iteration
```

New flow:
```
evaluate_sufficiency() → feedback_processor.process() → controller.decide() → set fields
```

The node:
1. Evaluates sufficiency as before
2. Calls `FeedbackProcessor.process(state)` → `state.retrieval_feedback`
3. Prepends `state.coverage_score` to `state.coverage_history`
4. Calls `RetrievalLoopController.decide(state)` → sets `state.requires_iteration` and `state.termination_reason`
5. Calls `telemetry.record_loop_decision(state)` for metrics

### `PlanExecutor`

On re-entry (`state.retrieval_iterations > 0`):
1. Reads `state.retrieval_feedback`
2. For each subtask, appends relevant feedback directives to `subtask["objective"]`
3. Calls `SearchFanoutNode` as before

### `route_after_sufficiency`

- Same routing logic: minor gaps → `"rewrite"`, major gaps → `"replan"`, sufficient → `"synthesis"`
- When controller says STOP (any termination reason), always routes to `"synthesis"` even if gaps exist
- **Bug fix:** return `"synthesis"` instead of `"tutor"` to match graph edge keys

## Bug Fixes (Bundled)

1. `route_after_sufficiency` returns `"synthesis"` (not `"tutor"`) to match `build_unified_graph` edge keys
2. Tests updated: `test_route_after_sufficiency_sufficient` expects `"synthesis"`, `test_route_after_sufficiency_gap` expects `"rewrite"`

## Files

| Action | Path |
|--------|------|
| Create | `src/core/loops/__init__.py` |
| Create | `src/core/loops/controller.py` |
| Create | `src/core/loops/feedback_processor.py` |
| Create | `src/core/loops/telemetry.py` |
| Modify | `src/graph/state.py` — add 4 fields |
| Modify | `src/graph/nodes/sufficient_context.py` — delegate to controller + feedback |
| Modify | `src/graph/nodes/plan_executor.py` — use feedback on re-entry |
| Fix | `src/graph/nodes/sufficient_context.py` — `route_after_sufficiency` return value |
| Create | `tests/test_retrieval_loop.py` |
| Fix | `tests/test_agentic_nodes.py` — SufficientContextNode routing tests |

## Test Plan

- `test_controller_decide_max_iterations`: count ≥ `state.max_iterations` → `MAX_ITERATIONS`
- `test_controller_decide_no_progress`: gain < 0.02 for 2 consecutive → `NO_PROGRESS`
- `test_controller_decide_no_new_evidence`: evidence count unchanged → `NO_NEW_EVIDENCE`
- `test_controller_decide_continue`: below all 3 thresholds → `CONTINUE`
- `test_controller_respects_state_max_iterations`: uses `state.max_iterations` not hardcoded
- `test_feedback_processor_empty_gaps`: no missing_info → empty list
- `test_feedback_processor_generates_directives`: 2 gaps → 2 directives
- `test_sufficient_context_delegates_to_controller`: mock controller, verify call
- `test_plan_executor_uses_feedback_on_reentry`: re-entry refines objectives
