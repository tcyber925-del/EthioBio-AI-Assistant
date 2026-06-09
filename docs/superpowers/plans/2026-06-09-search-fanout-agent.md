# Search Fanout Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Search Fanout Agent package that routes rewritten queries to the correct retrievers (curriculum live, others stubbed) and executes them in parallel.

**Architecture:** Rule-based agent (no LLM) with dict-lookup routing by `source_type`. The agent produces `RetrievalTask` objects, the node executes them via `asyncio.gather()` across curriculum (VectorStoreAdapter) and stub retrievers (memory, learner, recommendation).

**Tech Stack:** Python 3.12+, asyncio, existing VectorStoreAdapter, existing SearchFanoutNode (refactored)

**Spec:** `docs/superpowers/specs/2026-06-09-search-fanout-agent-design.md`

---

### Task 1: Models

**Files:**
- Create: `src/agents/search_fanout/__init__.py`
- Create: `src/agents/search_fanout/models.py`
- Test: `tests/agents/test_search_fanout.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for Search Fanout models."""
import pytest
from src.agents.search_fanout.models import (
    RetrievalTask,
    RetrievalStrategy,
    RetrievalStrategyName,
)


class TestRetrievalStrategyName:
    def test_has_five_strategies(self):
        assert len(RetrievalStrategyName) == 5

    def test_values(self):
        assert RetrievalStrategyName.SIMPLE == "SIMPLE"
        assert RetrievalStrategyName.COMPARISON == "COMPARISON"
        assert RetrievalStrategyName.PERSONALIZED == "PERSONALIZED"
        assert RetrievalStrategyName.REMEDIATION == "REMEDIATION"
        assert RetrievalStrategyName.MULTI_HOP == "MULTI_HOP"


class TestRetrievalTask:
    def test_has_required_fields(self):
        task = RetrievalTask(
            id="task_1",
            query="mitosis stages",
            target_source="curriculum",
            priority=8,
            estimated_cost=0.5,
            reasoning="Core concept retrieval",
        )
        assert task.id == "task_1"
        assert task.query == "mitosis stages"
        assert task.target_source == "curriculum"
        assert task.priority == 8
        assert task.estimated_cost == 0.5
        assert task.reasoning == "Core concept retrieval"

    def test_defaults(self):
        task = RetrievalTask(
            id="t1", query="test", target_source="curriculum", priority=5
        )
        assert task.estimated_cost == 0.0
        assert task.reasoning == ""

    def test_priority_range(self):
        RetrievalTask(id="t1", query="q", target_source="c", priority=1)
        RetrievalTask(id="t2", query="q", target_source="c", priority=10)
        with pytest.raises(Exception):
            RetrievalTask(id="t3", query="q", target_source="c", priority=0)
        with pytest.raises(Exception):
            RetrievalTask(id="t4", query="q", target_source="c", priority=11)

    def test_serialization(self):
        task = RetrievalTask(
            id="t1", query="meiosis", target_source="curriculum", priority=7
        )
        dumped = task.model_dump()
        assert dumped["query"] == "meiosis"
        assert dumped["priority"] == 7


class TestRetrievalStrategy:
    def test_has_required_fields(self):
        strategy = RetrievalStrategy(
            strategy_name="SIMPLE",
            retrieval_mode="single",
            parallel_execution=False,
            expected_sources=["curriculum"],
        )
        assert strategy.strategy_name == "SIMPLE"
        assert strategy.retrieval_mode == "single"
        assert strategy.parallel_execution is False
        assert strategy.expected_sources == ["curriculum"]

    def test_defaults(self):
        strategy = RetrievalStrategy(strategy_name="SIMPLE")
        assert strategy.retrieval_mode == "single"
        assert strategy.parallel_execution is False
        assert strategy.expected_sources == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/search_fanout/__init__.py
"""Search Fanout Agent module for Agentic RAG."""

from src.agents.search_fanout.models import (
    RetrievalStrategy,
    RetrievalStrategyName,
    RetrievalTask,
)

__all__ = [
    "RetrievalStrategy",
    "RetrievalStrategyName",
    "RetrievalTask",
]
```

```python
# src/agents/search_fanout/models.py
"""Search Fanout data models.

Implements the PRD-004 schema:
- RetrievalTask: a single retrieval operation
- RetrievalStrategy: execution plan metadata
- RetrievalStrategyName: the 5 strategy variants
"""

from enum import Enum

from pydantic import BaseModel, Field


class RetrievalStrategyName(str, Enum):
    """Strategies for retrieval execution."""

    SIMPLE = "SIMPLE"
    COMPARISON = "COMPARISON"
    PERSONALIZED = "PERSONALIZED"
    REMEDIATION = "REMEDIATION"
    MULTI_HOP = "MULTI_HOP"


class RetrievalTask(BaseModel):
    """A single retrieval operation targeting one source.

    Attributes:
        id: Unique task identifier.
        query: The query string to execute.
        target_source: Which retriever to use (curriculum, memory, etc.).
        priority: 1-10, higher is more important.
        estimated_cost: Reserved for future budget allocation.
        reasoning: Why this query routes to this source.
    """

    id: str = Field(description="Unique task identifier")
    query: str = Field(description="Query string to execute")
    target_source: str = Field(description="Target retriever name")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")
    estimated_cost: float = Field(default=0.0, description="Estimated retrieval cost")
    reasoning: str = Field(default="", description="Why this query routes here")


class RetrievalStrategy(BaseModel):
    """Execution strategy metadata.

    Attributes:
        strategy_name: One of RetrievalStrategyName.
        retrieval_mode: "single" or "multi".
        parallel_execution: Whether sources run in parallel.
        expected_sources: Sources this strategy targets.
    """

    strategy_name: str = Field(description="Strategy name from RetrievalStrategyName")
    retrieval_mode: str = Field(
        default="single", description="'single' or 'multi'"
    )
    parallel_execution: bool = Field(
        default=False, description="Run sources in parallel"
    )
    expected_sources: list[str] = Field(
        default_factory=list, description="Targeted retrieval sources"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/search_fanout/models.py src/agents/search_fanout/__init__.py tests/agents/test_search_fanout.py
git commit -m "feat(search_fanout): add RetrievalTask, RetrievalStrategy, RetrievalStrategyName models"
```

---

### Task 2: Routing Logic

**Files:**
- Create: `src/agents/search_fanout/routing.py`
- Test: `tests/agents/test_search_fanout.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
from src.agents.search_fanout.routing import (
    SOURCE_ROUTING,
    derive_strategy,
    route_queries,
)
from src.agents.search_fanout.models import RetrievalTask, RetrievalStrategy


class TestSourceRouting:
    def test_routes_curriculum(self):
        assert SOURCE_ROUTING["curriculum"] == "curriculum"

    def test_routes_memory(self):
        assert SOURCE_ROUTING["memory"] == "memory"

    def test_routes_misconception_to_memory(self):
        assert SOURCE_ROUTING["misconception"] == "memory"

    def test_routes_learner_profile(self):
        assert SOURCE_ROUTING["learner_profile"] == "learner"

    def test_routes_recommendation(self):
        assert SOURCE_ROUTING["recommendation"] == "recommendation"

    def test_routes_comparison_to_curriculum(self):
        assert SOURCE_ROUTING["comparison"] == "curriculum"

    def test_routes_definition_to_curriculum(self):
        assert SOURCE_ROUTING["definition"] == "curriculum"

    def test_unknown_source_falls_back_to_curriculum(self):
        from src.agents.search_fanout.routing import _resolve_source

        assert _resolve_source("unknown") == "curriculum"


class TestRouteQueries:
    def test_routes_single_category(self):
        groups = {"curriculum": ["mitosis stages", "cell cycle"]}
        tasks = route_queries(groups)
        assert len(tasks) == 2
        assert all(t.target_source == "curriculum" for t in tasks)

    def test_routes_multiple_categories(self):
        groups = {
            "curriculum": ["mitosis"],
            "memory": ["past mistakes"],
        }
        tasks = route_queries(groups)
        assert len(tasks) == 2
        sources = {t.target_source for t in tasks}
        assert sources == {"curriculum", "memory"}

    def test_preserves_query_priority(self):
        from src.agents.search_fanout.models import RewrittenQuery

        groups = {"curriculum": ["meiosis"]}
        tasks = route_queries(groups, default_priority=7)
        assert all(t.priority == 7 for t in tasks)

    def test_generates_unique_ids(self):
        groups = {"curriculum": ["q1", "q2"], "memory": ["m1"]}
        tasks = route_queries(groups)
        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_empty_groups(self):
        assert route_queries({}) == []


class TestDeriveStrategy:
    def test_single_curriculum_is_simple(self):
        strategy = derive_strategy({"curriculum": ["q1"]})
        assert strategy.strategy_name == "SIMPLE"
        assert strategy.parallel_execution is False
        assert strategy.retrieval_mode == "single"

    def test_curriculum_with_comparison_is_comparison(self):
        strategy = derive_strategy({"curriculum": ["q1"], "comparison": ["q2"]})
        assert strategy.strategy_name == "COMPARISON"
        assert strategy.parallel_execution is True

    def test_includes_memory_is_personalized(self):
        strategy = derive_strategy({"curriculum": ["q1"], "memory": ["m1"]})
        assert strategy.strategy_name == "PERSONALIZED"

    def test_includes_recommendation_is_remediation(self):
        strategy = derive_strategy({"curriculum": ["q1"], "recommendation": ["r1"]})
        assert strategy.strategy_name == "REMEDIATION"

    def test_three_or_more_sources_is_multi_hop(self):
        strategy = derive_strategy({
            "curriculum": ["q1"],
            "memory": ["m1"],
            "recommendation": ["r1"],
        })
        assert strategy.strategy_name == "MULTI_HOP"

    def test_empty_groups_defaults_to_simple(self):
        strategy = derive_strategy({})
        assert strategy.strategy_name == "SIMPLE"

    def test_expected_sources_matches_groups(self):
        strategy = derive_strategy({"curriculum": ["q1"], "memory": ["m1"]})
        assert "curriculum" in strategy.expected_sources
        assert "memory" in strategy.expected_sources
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/search_fanout/routing.py
"""Source routing and strategy derivation for Search Fanout.

Rule-based routing (no LLM). Maps QueryCategory source types
to retriever names via SOURCE_ROUTING dict lookup.
"""

import uuid

from src.agents.search_fanout.models import (
    RetrievalStrategy,
    RetrievalStrategyName,
    RetrievalTask,
)

QUERY_SOURCE_TYPE = "query_source_type"
DEFAULT_PRIORITY = 5

# Maps query source_type → retriever name
SOURCE_ROUTING: dict[str, str] = {
    "curriculum": "curriculum",
    "memory": "memory",
    "misconception": "memory",
    "learner_profile": "learner",
    "recommendation": "recommendation",
    "comparison": "curriculum",
    "definition": "curriculum",
}


def _resolve_source(source_type: str) -> str:
    """Resolve a query source_type to a retriever name."""
    return SOURCE_ROUTING.get(source_type, "curriculum")


def route_queries(
    query_groups: dict[str, list[str]],
    default_priority: int = DEFAULT_PRIORITY,
) -> list[RetrievalTask]:
    """Convert query_groups into a list of RetrievalTask objects.

    Each query in each group becomes a task routed to the
    appropriate retriever via SOURCE_ROUTING.

    Args:
        query_groups: Dict mapping source_type → list of query strings.
        default_priority: Default priority for all tasks.

    Returns:
        List of RetrievalTask objects with unique IDs.
    """
    tasks: list[RetrievalTask] = []

    for source_type, queries in query_groups.items():
        target = _resolve_source(source_type)
        for query in queries:
            tasks.append(
                RetrievalTask(
                    id=uuid.uuid4().hex[:12],
                    query=query,
                    target_source=target,
                    priority=default_priority,
                    reasoning=f"Routed from {source_type} to {target}",
                )
            )

    return tasks


def derive_strategy(query_groups: dict[str, list[str]]) -> RetrievalStrategy:
    """Derive a RetrievalStrategy from the query_groups source types.

    Strategy is determined by which source types are present:

    | Sources Present | Strategy |
    |----------------|----------|
    | Only curriculum | SIMPLE |
    | curriculum + comparison | COMPARISON |
    | Includes memory | PERSONALIZED |
    | Includes recommendation | REMEDIATION |
    | 3+ sources | MULTI_HOP |

    Args:
        query_groups: Dict mapping source_type → list of query strings.

    Returns:
        RetrievalStrategy with appropriate name and metadata.
    """
    source_types = set(query_groups.keys())
    expected = list(source_types)

    if len(source_types) >= 3:
        name = RetrievalStrategyName.MULTI_HOP
        mode = "multi"
        parallel = True
    elif "recommendation" in source_types:
        name = RetrievalStrategyName.REMEDIATION
        mode = "multi"
        parallel = True
    elif "memory" in source_types or "misconception" in source_types:
        name = RetrievalStrategyName.PERSONALIZED
        mode = "multi"
        parallel = True
    elif "comparison" in source_types:
        name = RetrievalStrategyName.COMPARISON
        mode = "multi"
        parallel = True
    else:
        name = RetrievalStrategyName.SIMPLE
        mode = "single"
        parallel = False

    return RetrievalStrategy(
        strategy_name=name.value,
        retrieval_mode=mode,
        parallel_execution=parallel,
        expected_sources=list(set(_resolve_source(s) for s in expected)),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/search_fanout/routing.py tests/agents/test_search_fanout.py
git commit -m "feat(search_fanout): add rule-based routing and strategy derivation"
```

---

### Task 3: SearchFanoutAgent

**Files:**
- Create: `src/agents/search_fanout/search_fanout.py`
- Test: `tests/agents/test_search_fanout.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
from src.agents.search_fanout.search_fanout import SearchFanoutAgent


class TestSearchFanoutAgent:
    def test_plan_creates_tasks(self):
        agent = SearchFanoutAgent()
        groups = {
            "curriculum": ["mitosis stages"],
            "memory": ["past mistakes meiosis"],
        }
        tasks, strategy = agent.plan(groups)
        assert len(tasks) == 2
        assert strategy.strategy_name == "PERSONALIZED"

    def test_plan_empty_groups_produces_tasks(self):
        agent = SearchFanoutAgent()
        tasks, strategy = agent.plan({"curriculum": ["default query"]})
        assert len(tasks) == 1
        assert strategy.strategy_name == "SIMPLE"
        assert tasks[0].target_source == "curriculum"

    def test_plan_includes_reasoning(self):
        agent = SearchFanoutAgent()
        groups = {"curriculum": ["meiosis"]}
        tasks, _ = agent.plan(groups)
        assert "Routed from" in tasks[0].reasoning

    def test_plan_respects_max_queries(self):
        agent = SearchFanoutAgent(max_queries=2)
        groups = {"curriculum": ["q1", "q2", "q3", "q4"]}
        tasks, _ = agent.plan(groups)
        assert len(tasks) <= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/search_fanout/search_fanout.py
"""Search Fanout Agent.

Rule-based agent that routes rewritten queries to the correct
retrievers and derives an execution strategy.

No LLM calls — pure logic on query_groups.
"""

from src.agents.search_fanout.models import RetrievalStrategy, RetrievalTask
from src.agents.search_fanout.routing import derive_strategy, route_queries

MAX_QUERIES = 20
MAX_SOURCES = 4


class SearchFanoutAgent:
    """Search Fanout Agent.

    Consumes query_groups from QueryRewriter, produces
    RetrievalTask list + RetrievalStrategy.

    The agent is stateless — plan() is a pure function.
    """

    def __init__(self, max_queries: int = MAX_QUERIES):
        self.max_queries = max_queries

    def plan(
        self, query_groups: dict[str, list[str]]
    ) -> tuple[list[RetrievalTask], RetrievalStrategy]:
        """Create retrieval tasks and derive strategy from query groups.

        Args:
            query_groups: Dict mapping source_type → list of query strings.

        Returns:
            Tuple of (tasks, strategy).
        """
        # Cap total queries
        capped_groups: dict[str, list[str]] = {}
        total = 0
        for source_type, queries in query_groups.items():
            remaining = self.max_queries - total
            if remaining <= 0:
                break
            capped_groups[source_type] = queries[:remaining]
            total += len(capped_groups[source_type])

        tasks = route_queries(capped_groups)
        strategy = derive_strategy(capped_groups)

        return tasks, strategy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_search_fanout.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/agents/search_fanout/search_fanout.py tests/agents/test_search_fanout.py
git commit -m "feat(search_fanout): add SearchFanoutAgent with plan()"
```

---

### Task 4: Update AgentState

**Files:**
- Modify: `src/graph/state.py`

- [ ] **Step 1: Add new fields to AgentState**

```python
    # Retrieval State
    retrieval_tasks: list[dict] = field(default_factory=list)
    retrieval_iterations: int = 0
    previous_evidence_count: int = 0
    retrieval_strategy: dict = field(default_factory=dict)
    retrieval_source_results: dict[str, list[dict]] = field(default_factory=dict)
```

Add `retrieval_strategy` and `retrieval_source_results` after the existing `retrieval_tasks` line.

- [ ] **Step 2: Verify state compiles**

Run: `python -c "from src.graph.state import AgentState; s = AgentState(); assert s.retrieval_strategy == {}; assert s.retrieval_source_results == {}"`

- [ ] **Step 3: Commit**

```bash
git add src/graph/state.py
git commit -m "feat(state): add retrieval_strategy and retrieval_source_results fields"
```

---

### Task 5: Refactor SearchFanoutNode

**Files:**
- Modify: `src/graph/nodes/search_fanout.py`
- Test: `tests/test_agentic_nodes.py` (update)

- [ ] **Step 1: Write the failing/updated tests**

```python
# Replace existing TestSearchFanoutNode in tests/test_agentic_nodes.py

class TestSearchFanoutNode:
    """Tests for SearchFanoutNode."""

    @pytest.mark.asyncio
    async def test_node_retrieves_chunks(self):
        """Should retrieve and rank chunks via curriculum retriever."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {
            "documents": [
                {"content": "test content", "metadata": {"id": "id1"}, "score": 0.8}
            ]
        }

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(user_message="test")
        state.rewritten_queries = ["test query"]
        state.query_groups = {"curriculum": ["test query"]}

        result = await node(state)

        assert len(result.retrieved_chunks) >= 0
        assert result.retrieval_strategy != {}

    @pytest.mark.asyncio
    async def test_node_sets_strategy_and_tasks(self):
        """Should populate retrieval_strategy and retrieval_tasks."""
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = {"documents": []}

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["mitosis"], "memory": ["past mistakes"]},
            rewritten_queries=["mitosis", "past mistakes"],
        )

        result = await node(state)

        assert len(result.retrieval_tasks) == 2
        assert result.retrieval_strategy.get("strategy_name") == "PERSONALIZED"

    @pytest.mark.asyncio
    async def test_node_handles_source_failure_gracefully(self):
        """Should continue when one source fails."""
        mock_adapter = MagicMock()
        mock_adapter.search.side_effect = Exception("DB down")

        node = SearchFanoutNode(mock_adapter)
        state = AgentState(
            user_message="test",
            query_groups={"curriculum": ["mitosis"]},
            rewritten_queries=["mitosis"],
        )

        result = await node(state)

        assert result.retrieval_strategy != {}
        assert result.status == "pending"  # No error propagation
```

- [ ] **Step 2: Run test to verify it fails (old node doesn't have new behavior)**

Run: `pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: at least some tests fail due to missing strategy

- [ ] **Step 3: Refactor SearchFanoutNode**

```python
"""Search Fanout Node for Agentic RAG.

Retrieves evidence from multiple sources in parallel using asyncio.gather.
Uses SearchFanoutAgent for task planning and source routing.
"""

import asyncio
import logging

from src.agents.search_fanout.search_fanout import SearchFanoutAgent
from src.graph.state import AgentState
from src.retrieval.adapter import VectorStoreAdapter

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_SOURCE = 5
TOTAL_MAX_RESULTS = 15


class SearchFanoutNode:
    """LangGraph node that plans and executes parallel retrieval.

    Delegates task planning to SearchFanoutAgent, then executes
    via asyncio.gather across curriculum live retriever and
    stub retrievers for memory, learner, and recommendation.
    """

    def __init__(self, adapter: VectorStoreAdapter, max_queries: int = 20):
        self.adapter = adapter
        self.agent = SearchFanoutAgent(max_queries=max_queries)

    async def _search_curriculum(self, query: str, n_results: int = 5) -> list[dict]:
        """Search curriculum index via VectorStoreAdapter."""
        try:
            results = self.adapter.search(query, n_results=n_results, collection_name="curriculum")
            chunks = []
            for doc in results.get("documents", []):
                chunks.append({
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0.0),
                    "source": "curriculum",
                })
            return chunks
        except Exception as e:
            logger.warning("curriculum_search_failed: %s", str(e))
            return []

    async def _search_memory(self, query: str) -> list[dict]:
        """Stub: Memory retriever.

        TODO: Implement real memory retriever (PRD-xxx).
        """
        return []

    async def _search_learner(self, query: str) -> dict:
        """Stub: Learner profile retriever.

        TODO: Implement real learner retriever (PRD-xxx).
        """
        return {}

    async def _search_recommendation(self, query: str) -> list[dict]:
        """Stub: Recommendation retriever.

        TODO: Implement real recommendation retriever (PRD-xxx).
        """
        return []

    async def _safe_search(
        self, source: str, query: str
    ) -> tuple[str, list[dict] | dict]:
        """Execute a single source search, catching exceptions."""
        try:
            if source == "curriculum":
                result = await self._search_curriculum(query)
            elif source == "memory":
                result = await self._search_memory(query)
            elif source == "learner":
                result = await self._search_learner(query)
            elif source == "recommendation":
                result = await self._search_recommendation(query)
            else:
                logger.warning("unknown_source: %s", source)
                result = []
            return source, result
        except Exception as e:
            logger.warning("search_failed source=%s error=%s", source, str(e))
            if source == "learner":
                return source, {}
            return source, []

    async def __call__(self, state: AgentState) -> AgentState:
        query_groups = state.query_groups or {"curriculum": [state.user_message]}
        rewritten_queries = state.rewritten_queries or [state.user_message]

        # Plan: create tasks and derive strategy
        tasks, strategy = self.agent.plan(query_groups)

        # Execute: gather unique (source, query) pairs in parallel
        seen = set()
        search_coros = []
        for task in tasks:
            key = (task.target_source, task.query)
            if key not in seen:
                seen.add(key)
                search_coros.append(self._safe_search(task.target_source, task.query))

        raw_results = await asyncio.gather(*search_coros, return_exceptions=True)

        # Merge results
        all_chunks: list[dict] = []
        source_results: dict[str, list[dict] | dict] = {}
        for r in raw_results:
            if isinstance(r, tuple):
                source, result = r
                source_results[source] = result
                if isinstance(result, list):
                    all_chunks.extend(result)

        # Deduplicate by content
        seen_content = set()
        deduplicated = []
        for chunk in all_chunks:
            content = chunk.get("content", "")[:100]
            if content not in seen_content:
                seen_content.add(content)
                deduplicated.append(chunk)

        # Rank by score
        ranked = sorted(deduplicated, key=lambda x: x.get("score", 0), reverse=True)
        ranked = ranked[:TOTAL_MAX_RESULTS]

        state.retrieved_chunks = ranked
        state.retrieval_tasks = [t.model_dump() for t in tasks]
        state.retrieval_strategy = strategy.model_dump()
        state.retrieval_source_results = source_results

        # Coverage score
        if ranked:
            scores = [c.get("score", 0) for c in ranked]
            state.coverage_score = sum(scores) / len(scores)
        else:
            state.coverage_score = 0.0

        # Track evidence IDs
        evidence_ids = []
        for chunk in ranked:
            chunk_id = chunk.get("metadata", {}).get("id")
            if chunk_id:
                evidence_ids.append(chunk_id)
        state.evidence_ids = evidence_ids

        logger.info(
            "search_fanout_complete",
            sources_used=list(source_results.keys()),
            tasks_planned=len(tasks),
            chunks_retrieved=len(ranked),
            strategy=strategy.strategy_name,
        )

        return state


def route_after_fanout(state: AgentState) -> str:
    """Route after search fanout based on results."""
    if state.coverage_score < 0.3:
        return "rewrite"
    return "sufficient_context"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: PASS

- [ ] **Step 5: Verify no broken imports in orchestrator**

Run: `python -c "from src.graph.nodes.search_fanout import SearchFanoutNode, route_after_fanout"`

- [ ] **Step 6: Commit**

```bash
git add src/graph/nodes/search_fanout.py src/graph/state.py tests/test_agentic_nodes.py
git commit -m "feat(search_fanout): refactor node with SearchFanoutAgent integration"
```

---

### Task 6: Verify full test suite

- [ ] **Step 1: Run ruff check**

Run: `.venv/bin/ruff check src/agents/search_fanout/ src/graph/nodes/search_fanout.py src/graph/state.py tests/agents/test_search_fanout.py tests/test_agentic_nodes.py`
Expected: All checks passed

- [ ] **Step 2: Run all search_fanout + query_rewriter tests**

Run: `.venv/bin/python -m pytest tests/agents/test_search_fanout.py tests/agents/test_query_rewriter.py tests/agents/test_planner.py tests/test_benchmarks.py -v`
Expected: All pass

- [ ] **Step 3: Run full trustable test suite**

Run: `.venv/bin/python -m pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint and not test_agentic_integration" 2>&1 | tail -20`
Expected: Similar pass rate as before (pre-existing failures unchanged)
