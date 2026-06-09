# Iterative Retrieval Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for syntax tracking.

**Goal:** Add explicit iteration control to the Agentic RAG pipeline with a `RetrievalLoopController`, `FeedbackProcessor`, and telemetry, replacing inline hardcoded stopping criteria.

**Architecture:** Standalone `RetrievalLoopController` that `SufficientContextNode` delegates to for stop/continue decisions (3 criteria: max iterations, no progress, no new evidence). `FeedbackProcessor` converts gaps into targeted directives for `PlanExecutor` on re-entry. Graph topology unchanged.

**Tech Stack:** Python 3.12+, LangGraph, asyncio

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `src/core/loops/__init__.py` | Package init, re-export public API |
| Create | `src/core/loops/controller.py` | `LoopDecision` + `RetrievalLoopController` |
| Create | `src/core/loops/feedback_processor.py` | `FeedbackProcessor` |
| Create | `src/core/loops/telemetry.py` | `record_loop_decision()` |
| Create | `tests/test_retrieval_loop.py` | Tests for all 3 components |
| Modify | `src/graph/state.py` | Add `max_iterations`, `coverage_history`, `termination_reason`, `retrieval_feedback` |
| Modify | `src/graph/nodes/sufficient_context.py` | Delegate to controller + feedback + telemetry, fix routing |
| Modify | `src/graph/nodes/plan_executor.py` | Use feedback directives on re-entry |
| Modify | `tests/test_agentic_nodes.py` | Fix `route_after_sufficiency` tests |

---

### Task 1: Add AgentState fields

**Files:**
- Modify: `src/graph/state.py:97-114`
- Test: covered by `tests/test_retrieval_loop.py` (Task 2+)

- [ ] **Step 1: Add 4 fields to AgentState**

Add after `requires_iteration` (line 114):

```python
    # Iterative Retrieval Loop
    max_iterations: int = 3
    coverage_history: list[float] = field(default_factory=list)
    termination_reason: str = ""
    retrieval_feedback: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Verify AgentState instantiation works**

Run: `.venv/bin/python -c "from src.graph.state import AgentState; s = AgentState(); assert s.max_iterations == 3; assert s.coverage_history == []; assert s.termination_reason == ''; assert s.retrieval_feedback == []; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/graph/state.py
git commit -m "feat(state): add iteration loop fields to AgentState"
```

---

### Task 2: Create `src/core/loops/` package

**Files:**
- Create: `src/core/loops/__init__.py`

- [ ] **Step 1: Create `src/core/loops/__init__.py`**

```python
from src.core.loops.controller import LoopDecision, RetrievalLoopController
from src.core.loops.feedback_processor import FeedbackProcessor
from src.core.loops.telemetry import record_loop_decision

__all__ = [
    "LoopDecision",
    "RetrievalLoopController",
    "FeedbackProcessor",
    "record_loop_decision",
]
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from src.core.loops import LoopDecision, RetrievalLoopController, FeedbackProcessor, record_loop_decision; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/core/loops/__init__.py
git commit -m "feat(loops): create iterated retrieval loops package"
```

---

### Task 3: Implement `RetrievalLoopController`

**Files:**
- Create: `src/core/loops/controller.py`
- Test: `tests/test_retrieval_loop.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the RetrievalLoopController."""
from dataclasses import dataclass, field
from src.core.loops.controller import LoopDecision, RetrievalLoopController


@dataclass
class FakeState:
    retrieval_iterations: int = 0
    max_iterations: int = 3
    coverage_score: float = 0.0
    coverage_history: list[float] = field(default_factory=list)
    previous_evidence_count: int = 0
    evidence_ids: list[str] = field(default_factory=list)


def test_controller_continue_when_below_all_thresholds():
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=3,
        coverage_score=0.5,
        coverage_history=[0.3],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True
    assert decision.reason == "CONTINUE"


def test_controller_stops_at_max_iterations():
    state = FakeState(
        retrieval_iterations=3,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_exceeds_max_iterations():
    state = FakeState(
        retrieval_iterations=4,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_stops_on_no_progress():
    """2 consecutive low gains → stop.
    Gains here: 0.31-0.5=-0.19, 0.32-0.31=0.01 → both < 0.02."""
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.32,
        coverage_history=[0.5, 0.31],  # gains: 0.31-0.5=-0.19, 0.32-0.31=0.01
        previous_evidence_count=3,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "NO_PROGRESS"


def test_controller_continues_after_single_low_gain():
    """Only stop after 2 consecutive low-gain iterations.
    Gains here: 0.05-0.5=-0.45 (low), 0.50-0.05=0.45 (high) → only 1 low → continue."""
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.50,
        coverage_history=[0.5, 0.05],  # first gain low, second gain high
        previous_evidence_count=3,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True


def test_controller_stops_on_no_new_evidence():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.5,
        coverage_history=[0.3, 0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2"],  # same count as previous_evidence_count
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "NO_NEW_EVIDENCE"


def test_controller_respects_state_max_iterations():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=2,  # custom low cap
        coverage_score=0.5,
        coverage_history=[0.3],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_no_history_is_continue():
    """First iteration with empty history should not trigger no-progress."""
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=5,
        coverage_score=0.5,
        coverage_history=[],  # first run, no prior
        previous_evidence_count=0,
        evidence_ids=["e1"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True


def test_controller_no_new_evidence_first_iteration():
    """First iteration with 0 evidence should not trigger no-new-evidence
    (previous_evidence_count starts at 0, so 0 == 0 means no change)."""
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=5,
        coverage_score=0.0,
        coverage_history=[0.0],
        previous_evidence_count=0,
        evidence_ids=[],  # no evidence, but also no change from previous
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True
```

- [ ] **Step 2: Run to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py -v`
Expected: `FAILED` — import errors for `LoopDecision`, `RetrievalLoopController`

- [ ] **Step 3: Write minimal implementation**

`src/core/loops/controller.py`:

```python
"""Iterative retrieval loop controller.

Evaluates 3 stopping criteria and returns a LoopDecision."""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NO_PROGRESS_THRESHOLD = 0.02
NO_PROGRESS_CONSECUTIVE = 2


@dataclass
class LoopDecision:
    should_continue: bool
    reason: str  # CONTINUE | MAX_ITERATIONS | NO_PROGRESS | NO_NEW_EVIDENCE


class RetrievalLoopController:
    """Decides whether the retrieval loop should continue or stop.

    Stateless — all state comes from the AgentState (or duck-typed equivalent).
    Order of checks:
    1. Max iterations — hard cap
    2. No progress — coverage gain < threshold for N consecutive iterations
    3. No new evidence — evidence count unchanged from previous pass
    """

    def decide(self, state) -> LoopDecision:
        iterations = state.retrieval_iterations
        max_iter = state.max_iterations

        # 1. Max iterations
        if iterations >= max_iter:
            logger.info("loop_stop: max_iterations", current=iterations, max=max_iter)
            return LoopDecision(should_continue=False, reason="MAX_ITERATIONS")

        # 2. No progress (requires at least NO_PROGRESS_CONSECUTIVE history entries)
        if len(state.coverage_history) >= NO_PROGRESS_CONSECUTIVE:
            all_values: list[float] = list(state.coverage_history) + [state.coverage_score]
            all_gains = [all_values[i + 1] - all_values[i] for i in range(len(all_values) - 1)]
            recent_gains = all_gains[-NO_PROGRESS_CONSECUTIVE:]
            if all(g < NO_PROGRESS_THRESHOLD for g in recent_gains):
                logger.info(
                    "loop_stop: no_progress",
                    gains=[round(g, 4) for g in gains],
                )
                return LoopDecision(should_continue=False, reason="NO_PROGRESS")

        # 3. No new evidence (only after first iteration)
        if iterations > 0 and len(state.evidence_ids) <= state.previous_evidence_count:
            logger.info(
                "loop_stop: no_new_evidence",
                previous=state.previous_evidence_count,
                current=len(state.evidence_ids),
            )
            return LoopDecision(should_continue=False, reason="NO_NEW_EVIDENCE")

        return LoopDecision(should_continue=True, reason="CONTINUE")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/loops/controller.py tests/test_retrieval_loop.py
git commit -m "feat(loops): add RetrievalLoopController with 3-stop criteria"
```

---

### Task 4: Implement `FeedbackProcessor`

**Files:**
- Create: `src/core/loops/feedback_processor.py`
- Test: `tests/test_retrieval_loop.py` (append to existing)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_retrieval_loop.py`:

```python
# ─── FeedbackProcessor Tests ──────────────────────────────────────────


from src.core.loops.feedback_processor import FeedbackProcessor


def test_feedback_empty_gaps():
    processor = FeedbackProcessor()
    result = processor.process(missing_information=[], coverage_score=0.95)
    assert result == []


def test_feedback_single_gap():
    processor = FeedbackProcessor()
    result = processor.process(
        missing_information=["Explain DNA replication steps"],
        coverage_score=0.6,
    )
    assert len(result) == 1
    assert "DNA replication" in result[0]


def test_feedback_multiple_gaps():
    processor = FeedbackProcessor()
    result = processor.process(
        missing_information=[
            "Describe mitosis phases",
            "Define cell wall function",
            "List organelles",
        ],
        coverage_score=0.3,
    )
    assert len(result) == 3


def test_feedback_empty_gaps_low_coverage():
    processor = FeedbackProcessor()
    result = processor.process(missing_information=[], coverage_score=0.2)
    assert len(result) == 1
    assert "Broader" in result[0] or "broaden" in result[0].lower()
```

- [ ] **Step 2: Run to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py::test_feedback_empty_gaps -v`
Expected: FAILED — import error

- [ ] **Step 3: Write minimal implementation**

`src/core/loops/feedback_processor.py`:

```python
"""Feedback processor for the iterative retrieval loop.

Converts missing_information and coverage analysis into targeted
retrieval directives for the next iteration."""
import logging

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """Generates retrieval feedback from sufficiency gaps.

    Each gap in missing_information becomes a targeted directive.
    When missing_information is empty but coverage is low,
    generates a broader search directive.
    """

    def process(
        self,
        missing_information: list[str],
        coverage_score: float,
    ) -> list[str]:
        directives: list[str] = []

        for gap in missing_information:
            directive = f"Find information about: {gap}"
            directives.append(directive)

        if not missing_information and coverage_score < 0.5:
            directives.append(
                "Broaden search scope — coverage is low but no specific gaps identified"
            )

        if directives:
            logger.info(
                "feedback_generated",
                count=len(directives),
                from_gaps=len(missing_information),
            )

        return directives
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py::test_feedback_empty_gaps tests/test_retrieval_loop.py::test_feedback_single_gap tests/test_retrieval_loop.py::test_feedback_multiple_gaps tests/test_retrieval_loop.py::test_feedback_empty_gaps_low_coverage -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/loops/feedback_processor.py
git commit -m "feat(loops): add FeedbackProcessor for gap-to-directive conversion"
```

---

### Task 5: Implement telemetry

**Files:**
- Create: `src/core/loops/telemetry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieval_loop.py`:

```python
# ─── Telemetry Tests ──────────────────────────────────────────────────


from src.core.loops.telemetry import record_loop_decision


def test_record_loop_decision_returns_metrics():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.3, 0.7],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    # Add fields that telemetry reads
    state.sufficiency_score = 0.8
    state.termination_reason = "MAX_ITERATIONS"

    metrics = record_loop_decision(state)
    assert metrics["iteration"] == 2
    assert metrics["coverage"] == 0.7
    assert metrics["sufficiency"] == 0.8
    assert metrics["termination"] == "MAX_ITERATIONS"
    assert metrics["evidence_count"] == 2
    assert metrics["coverage_history"] == [0.3, 0.7]
```

- [ ] **Step 2: Run to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py::test_record_loop_decision_returns_metrics -v`
Expected: FAILED — import error

- [ ] **Step 3: Write minimal implementation**

`src/core/loops/telemetry.py`:

```python
"""Telemetry for the iterative retrieval loop."""


def record_loop_decision(state) -> dict:
    """Return loop metrics dict for PipelineMonitor."""
    return {
        "iteration": state.retrieval_iterations,
        "coverage": state.coverage_score,
        "sufficiency": getattr(state, "sufficiency_score", 0.0),
        "termination": state.termination_reason,
        "evidence_count": len(state.evidence_ids),
        "coverage_history": list(state.coverage_history),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py::test_record_loop_decision_returns_metrics -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/loops/telemetry.py
git commit -m "feat(loops): add loop telemetry metrics"
```

---

### Task 6: Run all loop tests before refactoring node

- [ ] **Step 1: Run all retrieval loop tests**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py -v`
Expected: 11 tests pass

- [ ] **Step 2: Commit**

```bash
git add tests/test_retrieval_loop.py
git commit -m "test(loops): complete test suite for loop components"
```

---

### Task 7: Refactor SufficientContextNode

**Files:**
- Modify: `src/graph/nodes/sufficient_context.py` (full file, 202 lines)

This is the main integration task. Changes:
1. Remove `MAX_ITERATIONS` and `DIMINISHING_RETURNS_THRESHOLD` constants
2. `evaluate_sufficiency()` no longer checks hard cap or diminishing returns — always does score computation
3. `SufficientContextNode.__call__()` delegates to `FeedbackProcessor`, `RetrievalLoopController`, and `record_loop_decision()`
4. `route_after_sufficiency` returns `"synthesis"` instead of `"tutor"`

- [ ] **Step 1: Remove hard cap from evaluate_sufficiency**

Simplify `evaluate_sufficiency()` — remove the early return blocks (Layer 1 and Layer 2). Now it always does the Layer 3 computation:

Replace the function (lines 43-126):

```python
def evaluate_sufficiency(state: AgentState) -> SufficiencyResult:
    """Evaluate whether evidence is sufficient to answer the question.

    Computes a combined score from evidence count and coverage,
    then classifies as sufficient, minor_gap, or major_gap.

    Termination decisions (max iterations, no progress, no new evidence)
    are handled by RetrievalLoopController, not here.
    """
    evidence_count = len(state.evidence_ids)
    coverage_score = state.coverage_score

    evidence_score = min(1.0, evidence_count / MIN_EVIDENCE_COUNT)
    base_score = (evidence_score + coverage_score) / 2

    missing = state.missing_information
    missing_penalty = len(missing) * 0.15
    final_score = max(0.0, base_score - missing_penalty)

    if final_score >= SUFFICIENCY_THRESHOLD and not missing:
        action = "sufficient"
        reason = f"Sufficient evidence: {evidence_count} records, coverage={coverage_score:.2f}"
    elif final_score >= REPLAN_EVIDENCE_THRESHOLD and len(missing) < REPLAN_MISSING_THRESHOLD:
        action = "minor_gap"
        reason = f"Minor gap: missing {', '.join(missing[:2])}"
    else:
        action = "major_gap"
        reason = f"Major gap: {len(missing)} missing areas, score={final_score:.2f}"

    return SufficiencyResult(
        is_sufficient=action == "sufficient",
        score=final_score,
        missing_information=missing,
        reason=reason,
        action=action,
    )
```

- [ ] **Step 2: Update SufficientContextNode.__call__ to delegate to components**

Update the `__call__` method (lines 141-181):

```python
from src.core.loops import FeedbackProcessor, RetrievalLoopController, record_loop_decision

class SufficientContextNode:
    """Evaluates context sufficiency in the Agentic RAG pipeline.

    Delegates termination logic to RetrievalLoopController and
    gap-to-directive conversion to FeedbackProcessor.
    """

    def __init__(self) -> None:
        self.controller = RetrievalLoopController()
        self.feedback_processor = FeedbackProcessor()

    async def __call__(self, state: AgentState) -> AgentState:
        state.previous_evidence_count = len(state.evidence_ids)

        result = evaluate_sufficiency(state)

        state.sufficiency_score = result.score
        state.sufficiency_reason = result.reason
        state.missing_information = result.missing_information

        # Append coverage to history before controller runs
        state.coverage_history.append(state.coverage_score)

        # Generate retrieval feedback for next iteration
        state.retrieval_feedback = self.feedback_processor.process(
            missing_information=state.missing_information,
            coverage_score=state.coverage_score,
        )

        # Let controller decide: should we continue?
        decision = self.controller.decide(state)
        state.requires_iteration = decision.should_continue
        state.termination_reason = decision.reason

        state.retrieval_iterations += 1

        # Emit telemetry
        record_loop_decision(state)

        logger.info(
            "sufficiency_evaluated",
            score=result.score,
            action=result.action,
            iterations=state.retrieval_iterations,
            termination=state.termination_reason,
            evidence_count=len(state.evidence_ids),
        )

        return state
```

- [ ] **Step 3: Fix route_after_sufficiency return value**

Replace the function (lines 184-202):

```python
def route_after_sufficiency(state: AgentState) -> str:
    """Route after sufficiency evaluation.

    When controller says STOP (any termination reason), route to synthesis.
    Otherwise route based on gap severity:
    - Minor gap -> rewrite (back to plan_executor)
    - Major gap -> replan (back to planner)

    Returns:
        "synthesis" if stopped or sufficient,
        "rewrite" for minor gaps,
        "replan" for major gaps.
    """
    # Controller says stop — always route to synthesis
    if not state.requires_iteration:
        return "synthesis"

    if len(state.missing_information) < REPLAN_MISSING_THRESHOLD:
        return "rewrite"

    return "replan"
```

- [ ] **Step 4: Remove unused constants**

Remove `MAX_ITERATIONS = 2` and `DIMINISHING_RETURNS_THRESHOLD = 0` from the top of the file (lines 28-29).

- [ ] **Step 5: Run existing sufficient_context tests**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSufficientContextNode -v`
Expected: Some tests may fail — `evaluate_sufficiency` no longer has early returns, so hard cap tests need updating. That's next.

- [ ] **Step 6: Run ruff on modified file**

Run: `.venv/bin/ruff check src/graph/nodes/sufficient_context.py`
Expected: All checks passed

- [ ] **Step 7: Commit**

```bash
git add src/graph/nodes/sufficient_context.py
git commit -m "feat(loops): refactor SufficientContextNode to delegate to RetrievalLoopController + FeedbackProcessor"
```

---

### Task 8: Add node-level integration tests

- [ ] **Step 1: Write integration test for SufficientContextNode delegation**

Append to `tests/test_retrieval_loop.py`:

```python
# ─── SufficientContextNode Integration Tests ──────────────────────────

from src.graph.nodes.sufficient_context import (
    SufficientContextNode,
    route_after_sufficiency,
    evaluate_sufficiency,
)
from src.graph.state import AgentState


@pytest.mark.asyncio
async def test_sufficient_context_node_delegates_to_controller():
    """Verify the node sets termination_reason and requires_iteration."""
    node = SufficientContextNode()
    state = AgentState(user_message="test")
    state.evidence_ids = ["e1"]
    state.coverage_score = 0.5
    state.missing_information = ["gap about dna"]

    result = await node(state)

    assert result.termination_reason in ("CONTINUE", "MAX_ITERATIONS", "NO_PROGRESS", "NO_NEW_EVIDENCE")
    assert result.retrieval_iterations == 1
    assert result.retrieval_feedback is not None


def test_route_after_sufficiency_returns_synthesis_when_stopped():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.8
    state.coverage_score = 0.8
    state.requires_iteration = False  # controller says stop

    route = route_after_sufficiency(state)

    assert route == "synthesis"


def test_route_after_sufficiency_returns_rewrite_for_minor_gap():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.3
    state.coverage_score = 0.3
    state.requires_iteration = True
    state.missing_information = ["Explain mitosis"]

    route = route_after_sufficiency(state)

    assert route == "rewrite"


def test_route_after_sufficiency_returns_replan_for_major_gap():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.1
    state.coverage_score = 0.1
    state.requires_iteration = True
    state.missing_information = ["gap 1", "gap 2", "gap 3"]

    route = route_after_sufficiency(state)

    assert route == "replan"
```

- [ ] **Step 2: Run all tests**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py tests/test_agentic_nodes.py::TestSufficientContextNode -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_retrieval_loop.py
git commit -m "test(loops): add SufficientContextNode integration tests for loop delegation"
```

---

### Task 9: PlanExecutor — use feedback on re-entry

**Files:**
- Modify: `src/graph/nodes/plan_executor.py`

- [ ] **Step 1: Update `_execute_subtask` to append feedback on re-entry**

Modify `_execute_subtask` (lines 85-106):

```python
    async def _execute_subtask(
        self,
        state: AgentState,
        subtask: dict,
        index: int,
    ) -> None:
        objective = subtask.get("objective", state.user_message)
        query = objective if objective else state.user_message

        # On re-entry, append retrieval feedback to make search more targeted
        if state.retrieval_iterations > 0 and state.retrieval_feedback:
            feedback_prefix = "; ".join(state.retrieval_feedback[:2])
            query = f"{query} — {feedback_prefix}"

        state.retrieval_queries = [query]
        state.retrieval_indices = ["curriculum"]

        try:
            await self.search_fanout(state)
        except Exception as e:
            logger.warning("subtask_retrieval_failed: %s", str(e))
```

- [ ] **Step 2: Run ruff**

Run: `.venv/bin/ruff check src/graph/nodes/plan_executor.py`
Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add src/graph/nodes/plan_executor.py
git commit -m "feat(loops): PlanExecutor appends retrieval feedback on re-entry"
```

---

### Task 10: Fix existing SufficientContextNode tests

**Files:**
- Modify: `tests/test_agentic_nodes.py`

The old `evaluate_sufficiency` tests for hard cap and diminishing returns need updating since those checks moved to the controller.

- [ ] **Step 1: Update the hard cap test**

Replace `test_evaluate_sufficiency_hard_cap` (lines 256-265):

```python
    def test_evaluate_sufficiency_no_longer_checks_hard_cap(self):
        """evaluate_sufficiency no longer stops at max iterations —
        that's the controller's job."""
        state = AgentState(user_message="test")
        state.retrieval_iterations = 2
        state.evidence_ids = ["e1"]
        state.coverage_score = 0.5

        result = evaluate_sufficiency(state)

        # Should compute score instead of early-returning
        assert result.score > 0  # score computed normally
        assert result.action in ("sufficient", "minor_gap")
```

- [ ] **Step 2: Update the diminishing returns test**

Replace `test_evaluate_sufficiency_diminishing_returns` (lines 277-287):

```python
    def test_evaluate_sufficiency_no_longer_checks_diminishing_returns(self):
        """evaluate_sufficiency no longer stops on diminishing returns —
        that's the controller's job."""
        state = AgentState(user_message="test")
        state.retrieval_iterations = 1
        state.evidence_ids = ["e1"]
        state.previous_evidence_count = 1
        state.coverage_score = 0.5

        result = evaluate_sufficiency(state)

        # Should compute score instead of early-returning
        assert result.score > 0
```

- [ ] **Step 3: Fix routing tests**

Replace `test_route_after_sufficiency_sufficient` (lines 238-245):

```python
    def test_route_after_sufficiency_sufficient(self):
        state = AgentState(user_message="test")
        state.sufficiency_score = 0.8
        state.coverage_score = 0.8
        state.requires_iteration = False

        route = route_after_sufficiency(state)

        assert route == "synthesis"
```

Replace `test_route_after_sufficiency_gap` (lines 247-254):

```python
    def test_route_after_sufficiency_gap(self):
        state = AgentState(user_message="test")
        state.sufficiency_score = 0.3
        state.coverage_score = 0.3
        state.requires_iteration = True
        state.missing_information = ["Explain mitosis"]

        route = route_after_sufficiency(state)

        assert route == "rewrite"
```

- [ ] **Step 4: Run all SufficientContextNode tests**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSufficientContextNode -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_agentic_nodes.py
git commit -m "test(loops): update SufficientContextNode tests for controller delegation"
```

---

### Task 11: Final verification

- [ ] **Step 1: Run all loop + agentic node tests**

Run: `.venv/bin/python -m pytest tests/test_retrieval_loop.py tests/test_agentic_nodes.py -v 2>&1`
Expected: All pass

- [ ] **Step 2: Run ruff on all changed files**

Run: `.venv/bin/ruff check src/core/loops/ src/graph/nodes/sufficient_context.py src/graph/nodes/plan_executor.py src/graph/state.py tests/`
Expected: All checks passed

- [ ] **Step 3: Run mypy**

Run: `.venv/bin/mypy src/core/loops/ src/graph/nodes/sufficient_context.py src/graph/nodes/plan_executor.py --ignore-missing-imports`
Expected: Success — no new errors

- [ ] **Step 4: Commit last adjustments**

```bash
git add -A && git commit -m "chore: final polish for iterative retrieval loop"
```
