# Spec: PRD-004 — Real Memory, Learner & Recommendation Retrievers

**Goal**: Replace 3 stubs in `SearchFanoutNode` with real DB-backed retrievers.

**Architecture**: Each retriever lives as a method on `SearchFanoutNode`, sharing the same `list[dict]` output contract as `_search_curriculum`. A `db_session_factory` parameter is added to `SearchFanoutNode.__init__()` (consistent with `EvidenceGraphNode`).

---

## 1. `_search_memory(query, user_id) → list[dict]`

**Source**: `ConversationTurn` + `MemoryEducationalSummary`

```python
SELECT FROM conversation_turns
WHERE user_id = ?
  AND (topic ILIKE '%query_term%' OR topic IS NULL)
ORDER BY created_at DESC
LIMIT 5
```

Score = recency factor (1.0 if today, 0.8 if this week, 0.5 otherwise).

Also fetches active `MemoryEducationalSummary` records for topic-matched summaries.

Chunk format:
```python
{
    "content": turn.content,  # or summary text
    "metadata": {"id": str(turn.id), "topic": turn.topic, "role": turn.role, "source_name": "conversation_turn"},
    "score": recency_score,
    "source": "memory",
}
```

---

## 2. `_search_learner(query, user_id) → list[dict]`

**Source**: `SnapshotService.get_snapshot()` — already aggregates:
- `StudentMastery` (per-topic scores, severity)
- `StudentAbility` (IRT estimates)
- `MisconceptionPattern` (active patterns)
- `UserGamification` (XP, level, streak)
- `SpacedRepetitionSchedule` (due reviews)

One chunk per data category per relevant topic. Score = `1.0 - severity_index` (mastery) or `0.8` (other).

Chunk format:
```python
{
    "content": "Topic 'Cell Biology': mastery=0.75 (good), attempts=12, ability=0.62",
    "metadata": {"id": "learner:mastery:cell_biology", "topic": "Cell Biology", "source_name": "student_mastery"},
    "score": 0.75,
    "source": "learner",
}
```

---

## 3. `_search_recommendation(query, user_id) → list[dict]`

**Source**: `RecommendationService.get_recommendations(user_id)`

Converts `LearningRecommendation` objects to chunks. Score = `recommendation.priority_score * 0.9`.

Chunk format:
```python
{
    "content": "Review topic 'Photosynthesis' (priority 0.85): Weak mastery, exam approaching",
    "metadata": {"id": "rec:REVIEW_TOPIC:photosynthesis", "action_type": "REVIEW_TOPIC", "topic": "Photosynthesis"},
    "score": 0.765,
    "source": "recommendation",
}
```

---

## 4. `SearchFanoutNode` changes

- `__init__` gains `db_session_factory: Optional[Callable[[], AsyncSession]] = None`
- Each retriever method acquires its own session via `async with db_session_factory() as session:`
- All three retrievers skip (return `[]`) when `user_id` is None (no user context)

## 5. Wiring changes

- `src/graph/orchestrator.py`: Add `from src.database.session import async_session_factory`, pass to `SearchFanoutNode(db_session_factory=async_session_factory)` in both graph builders
- Tests: Update `SearchFanoutNode` tests in `test_agentic_nodes.py` to mock DB sessions

## 6. Tests

- `test_search_memory`: Mock `ConversationTurn` query, verify topic matching and recency scoring
- `test_search_learner`: Mock `SnapshotService`, verify learner data serialization
- `test_search_recommendation`: Mock `RecommendationService`, verify recommendation conversion
- All three: verify `[]` returned when `user_id` is None
