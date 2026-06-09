# Evidence Graph Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing Evidence Graph infrastructure into the Agentic RAG pipeline via a new LangGraph node.

**Architecture:** `EvidenceGraphNode` sits between `plan_executor` and `sufficient_context`. It creates an EvidenceSession, persists all retrieved chunks as EvidenceRecords, selects the best evidence subset, analyzes coverage, and summarizes. Falls back to passthrough (no-op) when DB is unavailable.

**Tech Stack:** Python 3.12+, LangGraph, SQLAlchemy async, asyncio

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `src/graph/nodes/evidence_graph.py` | EvidenceGraphNode LangGraph node |
| Modify | `src/graph/orchestrator.py` | Add node + edges in both graph builders |
| Create | `tests/test_evidence_graph_node.py` | Unit + integration tests |
| Modify | `src/graph/nodes/search_fanout.py` | Optional: remove heuristic evidence_ids (kept as fallback) |
| Modify | `src/graph/nodes/plan_executor.py` | Optional: remove template evidence_summary (kept as fallback) |

---

### Task 1: Create `EvidenceGraphNode`

**Files:**
- Create: `src/graph/nodes/evidence_graph.py`
- Test: `tests/test_evidence_graph_node.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the EvidenceGraphNode."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.graph.nodes.evidence_graph import EvidenceGraphNode
from src.graph.state import AgentState


@pytest.mark.asyncio
async def test_node_passthrough_when_no_db():
    """Without db_session_factory, node should pass state through unchanged."""
    node = EvidenceGraphNode(db_session_factory=None)
    state = AgentState(user_message="test")
    result = await node(state)
    assert result is state
    assert result.user_message == "test"


@pytest.mark.asyncio
async def test_node_creates_session():
    """With a DB factory, node should create an EvidenceSession."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph  # inject mock

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1", "topic": "Cell Biology"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    mock_graph.create_session.assert_called_once()
    assert result.retrieval_iterations == 0


@pytest.mark.asyncio
async def test_node_persists_records():
    """Each chunk should become an EvidenceRecord."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = []

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1", "topic": "Cell Biology"},
                "score": 0.95,
                "source": "curriculum",
            },
            {
                "content": "Mitosis is the process of cell division.",
                "metadata": {"id": "chunk-2", "topic": "Cell Division"},
                "score": 0.85,
                "source": "curriculum",
            },
        ]
    }

    result = await node(state)

    assert mock_graph.add.call_count == 2
    first_call_args = mock_graph.add.call_args_list[0][0]
    assert first_call_args[0].source_type == "curriculum"
    assert first_call_args[0].content == state.retrieval_source_results["curriculum"][0]["content"]


@pytest.mark.asyncio
async def test_node_updates_evidence_ids():
    """Node should populate state.evidence_ids from selector output."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(id="e1"), MagicMock(id="e2")
    ]

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph
    node.selector = mock_selector

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    assert result.evidence_ids == ["e1"]
    mock_selector.select_for_generation.assert_called_once()


@pytest.mark.asyncio
async def test_node_sets_coverage_and_missing():
    """Node should populate coverage_score and missing_information."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"
    mock_graph.add.return_value = "evidence-uuid"
    mock_graph.get_evidence_for_session.return_value = [
        MagicMock(id="e1", content="Cell theory", source_type="curriculum"),
    ]

    mock_selector = AsyncMock()
    mock_selector.select_for_generation.return_value = ["e1"]

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph
    node.selector = mock_selector

    state = AgentState(user_message="What is cell theory?", trace_id="trace-1")
    state.retrieval_source_results = {
        "curriculum": [
            {
                "content": "Cell theory states all living things are made of cells.",
                "metadata": {"id": "chunk-1"},
                "score": 0.95,
                "source": "curriculum",
            }
        ]
    }

    result = await node(state)

    assert result.coverage_score >= 0.0
    assert isinstance(result.missing_information, list)
    assert isinstance(result.evidence_summary, str)


@pytest.mark.asyncio
async def test_node_without_source_results():
    """Node should handle empty retrieval_source_results gracefully."""
    mock_session = AsyncMock()
    mock_graph = AsyncMock()
    mock_graph.create_session.return_value = "internal-session-uuid"

    mock_factory = MagicMock(return_value=mock_session)

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    node.graph = mock_graph

    state = AgentState(user_message="test", trace_id="trace-1")
    state.retrieval_source_results = {}

    result = await node(state)

    assert result is state
    mock_graph.create_session.assert_not_called()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v`
Expected: FAILED — `ModuleNotFoundError` for `src.graph.nodes.evidence_graph`

- [ ] **Step 3: Write minimal implementation**

`src/graph/nodes/evidence_graph.py`:

```python
"""Evidence Graph Node for Agentic RAG.

Normalizes raw retrieval output into persisted, selected, and scored
evidence records. Sits between PlanExecutor and SufficientContextNode.
"""
import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.evidence.graph import Evidence, EvidenceGraph
from src.core.evidence.scoring import (
    CoverageAnalysisResult,
    CoverageComponent,
    analyze_coverage,
    detect_missing_information,
)
from src.core.evidence.selector import EvidenceSelector
from src.core.evidence.summarizer import summarize_evidence
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


class EvidenceGraphNode:
    """Wires Evidence Graph into the LangGraph pipeline.

    Creates an EvidenceSession, persists chunks as EvidenceRecords,
    selects the best evidence, analyzes coverage, and generates a summary.
    Falls back to passthrough when db_session_factory is None.
    """

    def __init__(
        self,
        db_session_factory: Optional[callable] = None,
        router=None,
    ):
        self.db_session_factory = db_session_factory
        self.graph: Optional[EvidenceGraph] = None
        self.selector = EvidenceSelector(graph=None, router=router)

    async def __call__(self, state: AgentState) -> AgentState:
        if not self.db_session_factory or not state.retrieval_source_results:
            logger.info("evidence_graph: passthrough (no db or no results)")
            return state

        session: AsyncSession = self.db_session_factory()
        self.graph = EvidenceGraph(session)

        trace_id = state.trace_id or ""
        session_key = state.session_id or trace_id or "default"
        user_id_str = str(state.user_id) if state.user_id else None

        # 1. Create session
        internal_session_id = await self.graph.create_session(
            session_id=session_key,
            trace_id=trace_id,
            user_id=user_id_str,
        )
        logger.info("evidence_graph: session_created", session_id=internal_session_id)

        # 2. Persist all chunks as evidence records
        evidence_count = 0
        for source_type, chunks in state.retrieval_source_results.items():
            for chunk in chunks:
                evidence = Evidence(
                    id="",
                    source_type=source_type,
                    source_name=chunk.get("source", source_type),
                    chunk_id=chunk.get("metadata", {}).get("id"),
                    content=chunk.get("content", ""),
                    original_query=state.user_message,
                    retrieval_query=state.user_message,
                    retrieval_score=chunk.get("score", 0.0),
                    rerank_score=chunk.get("score", 0.0),
                    confidence=chunk.get("score", 0.0),
                    retrieved_by="search_fanout",
                    trace_id=trace_id,
                    user_id=user_id_str,
                )
                await self.graph.add(evidence, internal_session_id)
                evidence_count += 1

        logger.info("evidence_graph: records_persisted", count=evidence_count)

        # 3. Get evidence for selection
        evidence_list = await self.graph.get_evidence_for_session(session_key)
        evidence_ids = [e.id for e in evidence_list]

        # 4. Select best evidence
        selected_ids = await self.selector.select_for_generation(
            evidence_ids=evidence_ids,
            question=state.user_message,
        )
        state.evidence_ids = selected_ids

        # 5. Analyze coverage
        evidence_dicts: list[dict[str, Any]] = [
            {
                "id": e.id,
                "content": e.content,
                "score": e.confidence,
                "source": e.source_type,
            }
            for e in evidence_list
        ]
        coverage = analyze_coverage(
            question=state.user_message,
            evidence_list=evidence_dicts,
        )
        state.coverage_score = coverage.coverage_score
        state.missing_information = detect_missing_information(coverage)

        # 6. Generate summary
        summary = summarize_evidence(
            evidence_list=evidence_dicts,
            question=state.user_message,
        )
        state.evidence_summary = summary.summary_text

        return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v`
Expected: 6 passed

- [ ] **Step 5: Ruff check**

Run: `.venv/bin/ruff check src/graph/nodes/evidence_graph.py tests/test_evidence_graph_node.py`
Expected: All checks passed

- [ ] **Step 6: Commit**

```bash
git add src/graph/nodes/evidence_graph.py tests/test_evidence_graph_node.py
git commit -m "feat(evidence): add EvidenceGraphNode for persisting, selecting, and scoring evidence"
```

---

### Task 2: Wire node into graph

**Files:**
- Modify: `src/graph/orchestrator.py`

- [ ] **Step 1: Read the current orchestrator.py**

Run: `cat src/graph/orchestrator.py`
Note the current structure at line 14 (imports) and lines 72-73, 87-88, 246-248, 269-271.

- [ ] **Step 2: Add import**

Add after line 18:
```python
from src.graph.nodes.evidence_graph import EvidenceGraphNode
```

- [ ] **Step 3: Add node to `build_agentic_graph`**

Add after line 72:
```python
    workflow.add_node("evidence_graph", EvidenceGraphNode(db_session_factory=None))
```

Change line 88 from:
```python
    workflow.add_edge("plan_executor", "sufficient_context")
```
to:
```python
    workflow.add_edge("plan_executor", "evidence_graph")
    workflow.add_edge("evidence_graph", "sufficient_context")
```

- [ ] **Step 4: Add node to `build_unified_graph`**

Add after line 248:
```python
    workflow.add_node("evidence_graph", EvidenceGraphNode(db_session_factory=None))
```

Change line 271 from:
```python
    workflow.add_edge("plan_executor", "sufficient_context")
```
to:
```python
    workflow.add_edge("plan_executor", "evidence_graph")
    workflow.add_edge("evidence_graph", "sufficient_context")
```

- [ ] **Step 5: Verify graph compiles**

Run: `.venv/bin/python -c "from src.graph.orchestrator import build_agentic_graph, build_unified_graph; from src.llm.router import ModelRouter; from src.retrieval.adapter import VectorStoreAdapter; r=ModelRouter(); a=VectorStoreAdapter(); g1=build_agentic_graph(r,a); g2=build_unified_graph(r,a); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Ruff check**

Run: `.venv/bin/ruff check src/graph/orchestrator.py`
Expected: All checks passed

- [ ] **Step 7: Commit**

```bash
git add src/graph/orchestrator.py
git commit -m "feat(evidence): wire EvidenceGraphNode into agentic and unified graphs"
```

---

### Task 3: Graph wiring tests

**Files:**
- Modify: `tests/test_evidence_graph_node.py`

- [ ] **Step 1: Add graph wiring tests**

Append to `tests/test_evidence_graph_node.py`:

```python
# ─── Graph Wiring Tests ───────────────────────────────────────────────


from src.graph.orchestrator import build_agentic_graph, build_unified_graph
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter


def test_agentic_graph_has_evidence_graph_node():
    """Agentic graph should include evidence_graph node."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = build_agentic_graph(router, adapter)

    nodes = list(graph.nodes.keys())
    assert "evidence_graph" in nodes, f"evidence_graph not in nodes: {nodes}"


def test_agentic_graph_node_ordering():
    """evidence_graph should be between plan_executor and sufficient_context."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = build_agentic_graph(router, adapter)

    node_list = list(graph.nodes.keys())
    plan_idx = node_list.index("plan_executor")
    evidence_idx = node_list.index("evidence_graph")
    sufficient_idx = node_list.index("sufficient_context")

    assert plan_idx < evidence_idx < sufficient_idx, (
        f"Expected plan_executor < evidence_graph < sufficient_context, "
        f"got {node_list}"
    )


def test_unified_graph_has_evidence_graph_node():
    """Unified graph should include evidence_graph node."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = build_unified_graph(router, adapter)

    nodes = list(graph.nodes.keys())
    assert "evidence_graph" in nodes, f"evidence_graph not in nodes: {nodes}"


def test_unified_graph_node_ordering():
    """evidence_graph should be between plan_executor and sufficient_context."""
    router = ModelRouter()
    adapter = VectorStoreAdapter()
    graph = build_unified_graph(router, adapter)

    node_list = list(graph.nodes.keys())
    plan_idx = node_list.index("plan_executor")
    evidence_idx = node_list.index("evidence_graph")
    sufficient_idx = node_list.index("sufficient_context")

    assert plan_idx < evidence_idx < sufficient_idx, (
        f"Expected plan_executor < evidence_graph < sufficient_context, "
        f"got {node_list}"
    )
```

- [ ] **Step 2: Run graph wiring tests**

Run: `.venv/bin/python -m pytest tests/test_evidence_graph_node.py::test_agentic_graph_has_evidence_graph_node tests/test_evidence_graph_node.py::test_agentic_graph_node_ordering tests/test_evidence_graph_node.py::test_unified_graph_has_evidence_graph_node tests/test_evidence_graph_node.py::test_unified_graph_node_ordering -v`
Expected: 4 passed

- [ ] **Step 3: Run all evidence graph tests**

Run: `.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v`
Expected: 10 passed

- [ ] **Step 4: Ruff check**

Run: `.venv/bin/ruff check tests/test_evidence_graph_node.py`
Expected: All checks passed

- [ ] **Step 5: Commit**

```bash
git add tests/test_evidence_graph_node.py
git commit -m "test(evidence): add graph wiring tests for EvidenceGraphNode"
```

---

### Task 4: Final verification

- [ ] **Step 1: Run all tests that involve the changed files**

Run: `.venv/bin/python -m pytest tests/test_evidence_graph_node.py tests/test_agentic_nodes.py::TestSufficientContextNode tests/test_retrieval_loop.py -v`
Expected: All pass

- [ ] **Step 2: Full ruff check**

Run: `.venv/bin/ruff check src/graph/nodes/evidence_graph.py src/graph/orchestrator.py tests/test_evidence_graph_node.py`
Expected: All checks passed

- [ ] **Step 3: Mypy check**

Run: `.venv/bin/mypy src/graph/nodes/evidence_graph.py --ignore-missing-imports`
Expected: Success — no issues found

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A && git commit -m "chore: final polish for EvidenceGraphNode"
```
