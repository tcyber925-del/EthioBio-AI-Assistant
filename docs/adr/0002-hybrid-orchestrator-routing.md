# ADR-0002: Hybrid Orchestrator Routing

## Status

Accepted

## Context

A naive Agentic RAG approach would route every query through the Planner. But:

- Simple queries ("What is mitosis?") don't benefit from planning
- Socratic dialogue turns don't need re-planning
- Quiz generation already has its own retrieval logic
- Latency and cost increase with every LLM call

## Decision

Use a **hybrid router** in the Orchestrator:

1. **Fast heuristic classification** for obvious cases (simple patterns, complex patterns)
2. **LLM-based classification** only for ambiguous cases (heuristic = MEDIUM)
3. **Primary signal**: `requires_planning` (derived from complexity, memory, multi-hop, cross-session)
4. **Intent alone does NOT determine planning** — intent establishes capability, complexity determines routing

### Routing Algorithm

```python
# Step 1: Hard intent exclusion
if intent in HARD_EXCLUDED_INTENTS:
    requires_planning = False

# Step 2: Heuristic complexity classification
heuristic_label, heuristic_score = classify_complexity_heuristic(user_message)

# Step 3: Feature extraction
requires_memory = detect_requires_memory(user_message)
requires_multi_hop = detect_requires_multi_hop(user_message)
requires_cross_session = detect_requires_cross_session(user_message)

# Step 4: Routing decision
requires_planning = (
    heuristic_score >= 0.7
    or requires_memory
    or requires_multi_hop
    or requires_cross_session
)
```

### Phase 0 Override

`requires_planning` is always `False` in Phase 0. The classification logic is in place but routing still goes to the existing pipeline. The override is removed in Phase 1 when the Agentic pipeline is wired.

## Consequences

### Positive

- Lower latency for simple queries
- Lower cost (fewer LLM calls)
- Planner focuses on genuinely complex queries
- Extensible to new intents and patterns

### Negative

- Heuristic rules need maintenance as query patterns evolve
- Risk of misclassification (mitigated by the MEDIUM fallback to LLM)

### Mitigations

- Heuristic patterns are regular expressions, easy to update
- MEDIUM complexity defaults to LLM classification
- Phase 0 override provides safety during migration

## Related

- PRD-002: Planner Agent
- `src/graph/nodes/orchestrator.py`
- Q12: requires_planning Routing Matrix
