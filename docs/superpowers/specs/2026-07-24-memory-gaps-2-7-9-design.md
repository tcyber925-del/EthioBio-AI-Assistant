# Memory System Improvements: Gaps 2, 7, 9

## Overview

Address three gaps identified in comparison with mem0ai/mem0:

- **Gap 9**: Benchmarking harness (educational memory recall scenarios)
- **Gap 7**: Multi-signal score fusion (BM25 + RRF)
- **Gap 2**: Entity extraction and linking (NER per-turn + LLM consolidation)

Ordered by dependency: Gap 9 first (cheapest, regression safety net), Gap 7 second (BM25 can be tested with Gap 9), Gap 2 last (entity scoring ties into RRF from Gap 7).

---

## Gap 9 — Benchmarking

### What

A pytest scenario suite in `tests/benchmarks/test_memory_recall.py` with 6 scenarios. Each seeds the DB with known facts, then verifies that `ContextAssembler.assemble()` and/or `RetrievalOrchestrator.search()` return the expected information with correct rank ordering.

### Scenarios

| # | Name | What it tests | Setup | Assertion |
|---|------|---------------|-------|-----------|
| 1 | preference_recall | SemanticFact retrieval | Seed `SemanticFact("learning_style", "prefers diagrams", category="preference")` | `ContextAssembler.assemble()` output contains "prefers diagrams" |
| 2 | misconception_cross_session | Summarizer + cross-session recall | Seed 2 sessions: session 1 has turns about mitosis confusion + summary with low understanding; session 2 queries about mitosis | Context must contain the misconception and the low understanding level |
| 3 | mastery_progression | Multiple summaries with different understanding levels | Seed 3 summaries: "beginner" (oldest), "intermediate", "advanced" (newest) for same topic | Context must show "advanced" as current level, ranked highest |
| 4 | multi_topic_recall | CrossSessionRecall across topics | Seed 4 turns across 2 topics (genetics, mitosis) | Context for topic=mitosis returns only mitosis turns; no-topic query returns both |
| 5 | entity_linking | Entity match scoring | Seed a turn containing "struggles with Punnett squares" | Query "genetics difficulties" returns that turn in top results |
| 6 | recency_ranking | Recency weighting in retrieval | Seed 2 identical-conflict facts, one 20 days old, one 1 day old | Newer fact ranks higher |

### Implementation

- New file: `tests/benchmarks/test_memory_recall.py`
- Uses existing `conftest.py` fixtures (async session, test DB)
- Seeds via `SessionManager`, `CrossSessionRecall`, `SemanticFactManager`, `Summarizer` directly
- Each scenario is a standalone async test function
- Runs in CI (no `@pytest.mark.slow`)
- Assertions on string containment and score ordering

---

## Gap 7 — Multi-Signal Score Fusion

### What

Add PostgreSQL full-text search (tsvector/ts_rank) as a second retrieval signal, fuse via Reciprocal Rank Fusion (RRF).

### Changes

#### 1. Database migration

```sql
ALTER TABLE conversation_turns ADD COLUMN search_vector TSVECTOR
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX idx_conversation_turns_search
  ON conversation_turns USING GIN(search_vector);

ALTER TABLE memory_educational_summaries ADD COLUMN search_vector TSVECTOR
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(next_learning_goal, '') || ' ' || coalesce(topic, ''))) STORED;
CREATE INDEX idx_memory_summaries_search
  ON memory_educational_summaries USING GIN(search_vector);
```

#### 2. RetrievalOrchestrator enhancements

Add optional `db: AsyncSession` parameter to `search()`:

```
search(query, n_results=5, fetch_size=20, topic=None, user_id=None, db=None)
```

When `db` is provided:

1. **Vector search** (existing): ChromaDB query → rank A
2. **BM25 search**: `SELECT id, content_ts_headline, ts_rank(search_vector, query) AS rank FROM conversation_turns WHERE user_id = :uid AND search_vector @@ plainto_tsquery('english', :query) ORDER BY rank DESC LIMIT fetch_size` → rank B
3. **RRF fusion**: Combined score = `1/(60 + rank_a) + 1/(60 + rank_b)`
4. **Truncate to budget** (existing, unchanged)

#### 3. ContextAssembler wiring

`ContextAssembler` already holds a `db` reference — pass it to `retrieval.search()`.

#### 4. search_fanout._search_memory() rewrite

Replace crude keyword substring matching (`any(t in content_lower for t in terms)`) with `ts_rank()`:

```python
stmt = (
    select(ConversationTurn, func.ts_rank(ConversationTurn.search_vector, query).label("rank"))
    .where(
        ConversationTurn.user_id == user_id,
        ConversationTurn.search_vector.op("@@")(func.plainto_tsquery("english", query)),
    )
    .order_by(desc("rank"))
    .limit(10)
)
```

### Data flow

```
Query → ChomraDB (vector similarity) ──→ rank_a ──┐
                                                    ├── RRF → combined score → sorted → truncated
Query → PostgreSQL (ts_rank BM25) ────→ rank_b ────┘
```

### Rationale for RRF over weighted sum

- Signals have different score distributions (cosine 0..1, ts_rank arbitrary scale)
- RRF removes need to normalize/hyperparameter-tune weights
- Adding entity scores later (Gap 2) is a simple `+ 1/(60 + rank_c)`

---

## Gap 2 — Entity Extraction & Linking

### What

Two-stage entity extraction pipeline: light NER per turn (no LLM), LLM consolidation on session close.

### New module

`src/core/memory/entity_extractor.py`

### Stage 1 — Turn-level NER (real-time)

Called after each `CrossSessionRecall.record_turns()`.

- Uses spaCy `en_core_web_sm` for `PERSON`, `ORG`, `GPE` entities
- Custom rule-based matcher for educational concepts:
  - Biology term list (mitosis, meiosis, genetics, Punnett, photosynthesis, etc.)
  - Difficulty markers via dependency patterns ("struggles with X", "confused by Y", "understands Z")
- Upserts into `memory_entities` table

### New table

```sql
CREATE TABLE memory_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    entity_text VARCHAR(300) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- 'concept', 'difficulty', 'topic', 'person'
    mention_count INTEGER DEFAULT 1,
    first_mentioned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_mentioned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sessions_seen UUID[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);
CREATE INDEX idx_memory_entities_user_text ON memory_entities(user_id, entity_text);
CREATE INDEX idx_memory_entities_type ON memory_entities(entity_type);
CREATE INDEX idx_memory_entities_user_type ON memory_entities(user_id, entity_type);
```

### Stage 2 — Session-close LLM consolidation

Called in `Summarizer.summarize_session()` after the educational summary.

- Same conversation context as the summarization prompt
- Prompt: "Extract key concepts, difficulties, and relationships from this session"
- Response format: `{"entities": [{"text": "...", "type": "concept|difficulty", "relationships": [{"subject": "...", "relation": "...", "object": "..."}]}]}`
- Updates `memory_entities` mentions (increment count, add session_id to `sessions_seen`)
- Optionally writes relationships to `memory_entity_relations`

### Retrieval integration

New method `_entity_match_score(query, user_id)` in `RetrievalOrchestrator`:

1. Run NER on query text → extract query entities
2. For each query entity, look up matching `memory_entities` for this user
3. Return `min(1.0, match_count / 3)` as entity score

This becomes the 3rd RRF signal:
```
score = 1/(60 + rank_vector) + 1/(60 + rank_bm25) + 1/(60 + rank_entity)
```

### Dependencies

- `spacy>=3.7` added to `pyproject.toml`
- `en_core_web_sm` downloaded via post-install script or runtime lazy load
- LLM extraction reuses existing `ModelRouter` (no new infra)

### Pipeline integration points

| Hook | Where | What runs |
|------|-------|-----------|
| Turn recorded | `CrossSessionRecall.record_turns()` end | `EntityExtractor.extract_from_turn(text, user_id, db)` |
| Session closes | `Summarizer.summarize_session()` after summary | `EntityExtractor.extract_from_session(session, db)` |
| Search | `RetrievalOrchestrator.search()` | `_entity_match_score(query, user_id)` → RRF input |

---

## Implementation order

1. **Gap 9** (benchmarks) — write test suite against current system. Confirms baseline before changes.
2. **Gap 7** (BM25 + RRF) — add migration, rewires RetrievalOrchestrator, rewrites _search_memory.
3. **Gap 2** (entity extraction) — new module, new table, NER integration, LLM consolidation.

Each step adds to the benchmark suite to validate the improvement.

## ADR impact

- `0005-memory-event-flat-json.md` — unaffected
- New ADR needed for `memory_entities` table schema and entity extraction design decision
