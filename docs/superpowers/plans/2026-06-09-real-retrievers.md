# PRD-004 Real Retrievers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 3 stub retrievers in SearchFanoutNode with real DB-backed implementations for memory, learner profile, and recommendations.

**Architecture:** Each retriever is a method on `SearchFanoutNode`. The node gains a `db_session_factory` parameter (consistent with `EvidenceGraphNode`). Memory queries `ConversationTurn`/`MemoryEducationalSummary`. Learner uses `SnapshotService` (already aggregates mastery, ability, misconceptions, gamification). Recommendations use `RecommendationService.get_recommendations()`.

**Tech Stack:** Python 3.12+, SQLAlchemy async, asyncio, existing learner/recommendation services

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `src/graph/nodes/search_fanout.py` | Add `db_session_factory` param, implement 3 retrievers |
| Modify | `src/graph/orchestrator.py` | Pass `async_session_factory` to `SearchFanoutNode` in both graph builders |
| Modify | `tests/test_agentic_nodes.py` | Update `TestSearchFanoutNode` tests with mocked DB sessions |

---

### Task 1: Add `db_session_factory` to SearchFanoutNode + implement `_search_memory`

**Files:**
- Modify: `src/graph/nodes/search_fanout.py`

**Context:** `SearchFanoutNode` currently takes `(adapter, max_queries)`. It needs a third parameter `db_session_factory` that is `Optional[Callable[[], AsyncSession]]`. All three retrievers use it to create sessions. The `_search_memory` method queries `ConversationTurn` and `MemoryEducationalSummary` by `user_id`, matching topic terms from the query.

- [ ] **Step 1: Write the failing test for `_search_memory`**

Add to `tests/test_agentic_nodes.py` inside or after `TestSearchFanoutNode`:

```python
@pytest.mark.asyncio
async def test_search_memory_returns_results():
    """Memory retriever should return ConversationTurn data."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    # Mock DB session with fake conversation turns
    mock_turn = MagicMock()
    mock_turn.id = "turn-1"
    mock_turn.content = "Student asked about cell division."
    mock_turn.topic = "Cell Division"
    mock_turn.role = "user"
    mock_turn.created_at = None  # will be handled in recency calc

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_turn]

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session

    adapter = VectorStoreAdapter()
    node = SearchFanoutNode(adapter, db_session_factory=mock_factory)

    chunks = await node._search_memory("cell division", user_id="user-1")

    assert len(chunks) >= 1
    assert chunks[0]["source"] == "memory"
    assert "cell division" in chunks[0]["content"].lower()


@pytest.mark.asyncio
async def test_search_memory_no_user_id():
    """Memory retriever should return [] when user_id is None."""
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    node = SearchFanoutNode(VectorStoreAdapter())
    chunks = await node._search_memory("test", user_id=None)
    assert chunks == []
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: At least the new tests fail (likely `TypeError: __init__()` unexpected keyword `db_session_factory`)

- [ ] **Step 3: Add `db_session_factory` to `__init__`**

Change `SearchFanoutNode.__init__` signature:

```python
class SearchFanoutNode:
    def __init__(
        self,
        adapter: VectorStoreAdapter,
        max_queries: int = 20,
        db_session_factory: Optional[Callable[[], AsyncSession]] = None,
    ):
        self.adapter = adapter
        self.agent = SearchFanoutAgent(max_queries=max_queries)
        self.db_session_factory = db_session_factory
```

Add the import:
```python
from collections.abc import Callable
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
```

- [ ] **Step 4: Implement `_search_memory`**

Replace the stub:

```python
async def _search_memory(self, query: str, user_id: Optional[str] = None) -> list[dict]:
    """Retrieve relevant conversation turns and educational summaries."""
    if not self.db_session_factory or not user_id:
        return []

    from src.database.models import ConversationTurn, MemoryEducationalSummary
    from sqlalchemy import select, desc

    from datetime import datetime, timezone

    factory = self.db_session_factory()
    async with factory as session:
        terms = [t.lower() for t in query.split() if len(t) > 3]

        stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.user_id == user_id)
            .order_by(desc(ConversationTurn.created_at))
            .limit(10)
        )
        result = await session.execute(stmt)
        turns = result.scalars().all()

        chunks = []
        now = datetime.now(timezone.utc)
        for turn in turns:
            content_lower = turn.content.lower()
            if terms and not any(t in content_lower for t in terms):
                continue

            age_days = (now - turn.created_at).days if turn.created_at else 365
            if age_days == 0:
                score = 1.0
            elif age_days < 7:
                score = 0.8
            elif age_days < 30:
                score = 0.5
            else:
                score = 0.2

            chunks.append({
                "content": turn.content,
                "metadata": {
                    "id": str(turn.id),
                    "topic": turn.topic or "",
                    "role": turn.role,
                    "source_name": "conversation_turn",
                },
                "score": score,
                "source": "memory",
            })

        # Also fetch educational summaries for topic context
        if terms:
            summary_stmt = (
                select(MemoryEducationalSummary)
                .where(MemoryEducationalSummary.user_id == user_id)
                .order_by(desc(MemoryEducationalSummary.created_at))
                .limit(3)
            )
            summary_result = await session.execute(summary_stmt)
            summaries = summary_result.scalars().all()
            for summary in summaries:
                content_lower = (summary.topic or "").lower()
                if not any(t in content_lower for t in terms):
                    continue
                chunks.append({
                    "content": summary.next_learning_goal or f"Summary for {summary.topic}",
                    "metadata": {
                        "id": str(summary.id),
                        "topic": summary.topic or "",
                        "source_name": "educational_summary",
                    },
                    "score": summary.confidence or 0.5,
                    "source": "memory",
                })

        return chunks
```

- [ ] **Step 5: Run tests to verify**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: At least the 2 new tests pass, existing ones may need updates

- [ ] **Step 6: Commit**

```bash
git add src/graph/nodes/search_fanout.py tests/test_agentic_nodes.py
git commit -m "feat(retrieval): add db_session_factory and _search_memory implementation"
```

---

### Task 2: Implement `_search_learner`

**Files:**
- Modify: `src/graph/nodes/search_fanout.py`
- Test: `tests/test_agentic_nodes.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_search_learner_returns_results():
    """Learner retriever should return mastery/ability data."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    mock_snapshot = MagicMock()
    mock_mastery = MagicMock()
    mock_mastery.topic = "Cell Biology"
    mock_mastery.average_score = 0.75
    mock_mastery.attempt_count = 12
    mock_mastery.severity = "good"
    mock_snapshot.mastery_by_topic = {"Cell Biology": mock_mastery}

    mock_ability = MagicMock()
    mock_ability.topic = "Cell Biology"
    mock_ability.ability_score = 0.62
    mock_snapshot.ability_by_topic = {"Cell Biology": mock_ability}

    mock_snapshot.misconceptions = []
    mock_snapshot.active_recovery_plans = []
    mock_snapshot.due_reviews = []

    mock_session = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session

    adapter = VectorStoreAdapter()
    node = SearchFanoutNode(adapter, db_session_factory=mock_factory)

    with patch(
        "src.graph.nodes.search_fanout.SnapshotService.get_snapshot",
        AsyncMock(return_value=mock_snapshot),
    ):
        chunks = await node._search_learner("cell biology", user_id="user-1")

    assert len(chunks) >= 1
    assert chunks[0]["source"] == "learner"
    assert "Cell Biology" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_search_learner_no_user_id():
    """Learner retriever should return [] when user_id is None."""
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    node = SearchFanoutNode(VectorStoreAdapter())
    chunks = await node._search_learner("test", user_id=None)
    assert chunks == []
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: New tests fail with `AttributeError` for missing `_search_learner` or `SnapshotService`

- [ ] **Step 3: Implement `_search_learner`**

Replace the stub:

```python
async def _search_learner(self, query: str, user_id: Optional[str] = None) -> list[dict]:
    """Retrieve learner profile data via SnapshotService."""
    if not self.db_session_factory or not user_id:
        return []

    from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService

    factory = self.db_session_factory()
    async with factory as session:
        snapshot_service = SnapshotService(session)
        snapshot = await snapshot_service.get_snapshot(user_id)

    if not snapshot:
        return []

    terms = [t.lower() for t in query.split() if len(t) > 3]
    chunks = []

    # Mastery data
    for topic, mastery in (snapshot.mastery_by_topic or {}).items():
        if terms and not any(t in topic.lower() for t in terms):
            continue
        severity_map = {"critical": 0.2, "moderate": 0.4, "mild": 0.6, "good": 0.8}
        score = severity_map.get(mastery.severity, 0.5) if hasattr(mastery, 'severity') else 0.5
        content = (
            f"Topic '{topic}': mastery={mastery.average_score:.2f} "
            f"({mastery.severity}), attempts={mastery.attempt_count}"
        )
        chunks.append({
            "content": content,
            "metadata": {
                "id": f"learner:mastery:{topic.lower().replace(' ', '_')}",
                "topic": topic,
                "source_name": "student_mastery",
            },
            "score": score,
            "source": "learner",
        })

    # Ability data
    for topic, ability in (snapshot.ability_by_topic or {}).items():
        if terms and not any(t in topic.lower() for t in terms):
            continue
        chunks.append({
            "content": f"Topic '{topic}': ability={ability.ability_score:.2f}, uncertainty={ability.uncertainty:.2f}",
            "metadata": {
                "id": f"learner:ability:{topic.lower().replace(' ', '_')}",
                "topic": topic,
                "source_name": "student_ability",
            },
            "score": min(1.0, ability.ability_score + 0.3),
            "source": "learner",
        })

    # Misconceptions
    for mc in (snapshot.misconceptions or []):
        if terms and not any(t in (mc.topic or "").lower() for t in terms):
            continue
        chunks.append({
            "content": f"Misconception in '{mc.topic}': {mc.pattern_description} (frequency={mc.frequency})",
            "metadata": {
                "id": f"learner:misconception:{mc.topic.lower().replace(' ', '_')}",
                "topic": mc.topic or "",
                "source_name": "misconception_pattern",
            },
            "score": min(0.7, mc.frequency * 0.15),
            "source": "learner",
        })

    return chunks
```

- [ ] **Step 4: Run tests to verify**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: Both new learner tests pass

- [ ] **Step 5: Commit**

```bash
git add src/graph/nodes/search_fanout.py tests/test_agentic_nodes.py
git commit -m "feat(retrieval): implement _search_learner using SnapshotService"
```

---

### Task 3: Implement `_search_recommendation`

**Files:**
- Modify: `src/graph/nodes/search_fanout.py`
- Test: `tests/test_agentic_nodes.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_search_recommendation_returns_results():
    """Recommendation retriever should return LearningRecommendation data."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    mock_rec = MagicMock()
    mock_rec.action_type = "REVIEW_TOPIC"
    mock_rec.topic = "Photosynthesis"
    mock_rec.priority_score = 0.85
    mock_rec.reason = "Weak mastery, exam approaching"
    mock_rec.id = "rec-1"

    mock_service = MagicMock()
    mock_service.get_recommendations = AsyncMock(return_value=[mock_rec])

    mock_session = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session

    adapter = VectorStoreAdapter()
    node = SearchFanoutNode(adapter, db_session_factory=mock_factory)

    with patch(
        "src.graph.nodes.search_fanout.RecommendationService",
        MagicMock(return_value=mock_service),
    ):
        chunks = await node._search_recommendation("photosynthesis", user_id="user-1")

    assert len(chunks) >= 1
    assert chunks[0]["source"] == "recommendation"
    assert "Photosynthesis" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_search_recommendation_no_user_id():
    """Recommendation retriever should return [] when user_id is None."""
    from src.graph.nodes.search_fanout import SearchFanoutNode
    from src.retrieval.adapter import VectorStoreAdapter

    node = SearchFanoutNode(VectorStoreAdapter())
    chunks = await node._search_recommendation("test", user_id=None)
    assert chunks == []
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: New tests fail for missing `_search_recommendation`

- [ ] **Step 3: Implement `_search_recommendation`**

Replace the stub:

```python
async def _search_recommendation(self, query: str, user_id: Optional[str] = None) -> list[dict]:
    """Retrieve recommendations via RecommendationService."""
    if not self.db_session_factory or not user_id:
        return []

    from src.core.learning_intelligence.recommendation.services.service import RecommendationService

    factory = self.db_session_factory()
    async with factory as session:
        service = RecommendationService(session)
        recommendations = await service.get_recommendations(user_id)

    if not recommendations:
        return []

    terms = [t.lower() for t in query.split() if len(t) > 3]
    chunks = []
    for rec in recommendations:
        topic_lower = (rec.topic or "").lower()
        if terms and not any(t in topic_lower for t in terms) and not any(t in rec.reason.lower() for t in terms):
            continue
        chunks.append({
            "content": f"Recommendation: {rec.reason}",
            "metadata": {
                "id": rec.id or f"rec:{rec.action_type}:{(rec.topic or 'unknown').lower().replace(' ', '_')}",
                "action_type": rec.action_type,
                "topic": rec.topic or "",
                "source_name": "recommendation_engine",
            },
            "score": rec.priority_score * 0.9,
            "source": "recommendation",
        })

    return chunks
```

- [ ] **Step 4: Run tests to verify**

Run: `.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v`
Expected: Both new recommendation tests pass

- [ ] **Step 5: Commit**

```bash
git add src/graph/nodes/search_fanout.py tests/test_agentic_nodes.py
git commit -m "feat(retrieval): implement _search_recommendation using RecommendationService"
```

---

### Task 4: Wire retrievers into `__call__` + update orchestrator

**Files:**
- Modify: `src/graph/nodes/search_fanout.py` (update `__call__` and `_safe_search`)
- Modify: `src/graph/orchestrator.py` (pass `db_session_factory`)

- [ ] **Step 1: Update `_safe_search` to pass `user_id`**

In `_safe_search`, change the memory/learner/recommendation calls to pass `state.user_id`:

```python
async def _safe_search(
    self, source: str, query: str, user_id: Optional[str] = None
) -> tuple[str, list[dict]]:
    try:
        if source == "curriculum":
            result = await self._search_curriculum(query)
        elif source == "memory":
            result = await self._search_memory(query, user_id=user_id)
        elif source == "learner":
            result = await self._search_learner(query, user_id=user_id)
        elif source == "recommendation":
            result = await self._search_recommendation(query, user_id=user_id)
        else:
            logger.warning("unknown_source: %s", source)
            result = []
        return source, result
    except Exception as e:
        logger.warning("search_failed source=%s error=%s", source, str(e))
        return source, []
```

- [ ] **Step 2: Update `__call__` to pass `state.user_id` to `_safe_search`**

Change the search coro list creation:

```python
search_coros.append(
    self._safe_search(task.target_source, task.query, user_id=state.user_id)
)
```

- [ ] **Step 3: Update `orchestrator.py` to pass `db_session_factory`**

In `src/graph/orchestrator.py`:

Add import:
```python
from src.database.session import async_session_factory
```

Find all `SearchFanoutNode(adapter)` calls (there should be 2 — one in `build_agentic_graph`, one in `build_unified_graph`). Change each from:

```python
SearchFanoutNode(adapter)
```

to:

```python
SearchFanoutNode(adapter, db_session_factory=async_session_factory)
```

- [ ] **Step 4: Update existing SearchFanout tests**

The existing tests in `TestSearchFanoutNode` create `SearchFanoutNode(adapter)` without the new parameter. They should work since the parameter is optional with `None` default. But `__call__` now passes `state.user_id` to `_safe_search`, which might be `None` — the retrievers handle that gracefully (return `[]`).

Run the tests to verify:
```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v
```

- [ ] **Step 5: Ruff check**

```bash
.venv/bin/ruff check src/graph/nodes/search_fanout.py src/graph/orchestrator.py tests/test_agentic_nodes.py
```

- [ ] **Step 6: Commit**

```bash
git add src/graph/nodes/search_fanout.py src/graph/orchestrator.py tests/test_agentic_nodes.py
git commit -m "feat(retrieval): wire real retrievers into SearchFanoutNode and orchestrator"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run all SearchFanout tests**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py::TestSearchFanoutNode -v
```
Expected: All tests pass

- [ ] **Step 2: Run full ruff check**

```bash
.venv/bin/ruff check src/graph/nodes/search_fanout.py src/graph/orchestrator.py tests/test_agentic_nodes.py
```
Expected: All checks passed

- [ ] **Step 3: Mypy check**

```bash
.venv/bin/mypy src/graph/nodes/search_fanout.py --ignore-missing-imports
```
Expected: Only pre-existing errors in other files

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A && git commit -m "chore: final polish for PRD-004 real retrievers"
```
