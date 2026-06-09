# ADR-0003: Agentic RAG Architecture

## Status
Accepted

## Context
The EthioBio AI Assistant needs to handle complex queries that require multi-step reasoning, iterative retrieval, and evidence verification. The existing pipeline (Orchestrator → Retrieval → Tutor → Safety) is sufficient for simple queries but lacks the sophistication needed for complex educational questions.

## Decision
Implement a Google-style Multi-Agent Agentic RAG platform with the following components:

### Architecture Components

1. **QueryRewriter** (`src/graph/nodes/query_rewriter.py`)
   - Expands queries for better retrieval coverage
   - Supports cross-lingual expansion (English/Amharic)
   - Decomposes complex queries into sub-queries

2. **SearchFanout** (`src/graph/nodes/search_fanout.py`)
   - Retrieves evidence from multiple indices in parallel
   - Deduplicates and ranks results by score
   - Supports curriculum, evidence, and cross_session indices

3. **SufficientContextNode** (`src/graph/nodes/sufficient_context.py`)
   - Evaluates evidence sufficiency using heuristic scoring
   - Routes to tutor, rewrite (minor gaps), or replan (major gaps)
   - Threshold-based decision making

4. **ClaimVerifierNode** (`src/graph/nodes/claim_verifier.py`)
   - Extracts factual claims from tutor responses
   - Verifies claims against evidence
   - Calculates groundedness score
   - Routes to finalize, revise, or reject

5. **PipelineMonitor** (`src/core/monitoring.py`)
   - Trace ID generation
   - Node-level performance tracking
   - Structured logging for observability

### Graph Topology

```
orchestrator → planner → query_rewriter → search_fanout
    → sufficient_context → tutor → claim_verifier → safety
```

**Iterative Loops:**
- `SUFFICIENT_CONTEXT` → rewrite (minor gap) or replan (major gap)
- `CLAIM_VERIFIER` → revise (poor grounding) or finalize (good grounding)

### Routing Logic

```python
def _route_after_orchestrator(state: AgentState) -> str:
    if state.requires_planning and state.intent in ("tutor", "lesson_plan", "progress"):
        return "planner"
    if state.intent in ("tutor", "quiz", "lesson_plan"):
        return "retrieve"
    return "skip_retrieval"
```

## Consequences

### Positive
- Handles complex queries requiring multi-step reasoning
- Iterative retrieval improves evidence coverage
- Claim verification ensures factual accuracy
- Unified graph handles both simple and complex queries
- Monitoring provides observability into pipeline performance

### Negative
- Increased latency for complex queries (planner + multiple retrievals)
- Higher resource usage (multiple LLM calls for planning)
- More complex debugging with multiple routing paths

### Neutral
- Backward compatible with existing endpoints
- Gradual rollout via `requires_planning` flag
- Can disable agentic features per-query

## Implementation Details

### Files Modified
- `src/graph/orchestrator.py`: Added `build_unified_graph()`, `run_graph()` with monitoring
- `src/graph/nodes/claim_verifier.py`: Implemented actual claim verification
- `src/api/graph.py`: Updated `/status` endpoint with new topology

### Files Created
- `src/graph/nodes/query_rewriter.py`: Query expansion and decomposition
- `src/graph/nodes/search_fanout.py`: Multi-index retrieval
- `src/graph/nodes/sufficient_context.py`: Context sufficiency evaluation
- `src/core/monitoring.py`: Pipeline monitoring and observability
- `tests/test_agentic_nodes.py`: Unit tests for all agentic nodes
- `tests/test_agentic_integration.py`: Integration tests
- `tests/test_benchmarks.py`: Performance benchmarks

### Test Results
- `tests/test_agentic_nodes.py`: 32/32 passed
- `tests/test_agentic_integration.py`: Integration tests (requires Ollama)
- `tests/test_benchmarks.py`: Performance benchmarks

## Future Work
- Phase 2: LLM-based claim verification (replaces heuristic)
- Phase 3: Real-time reranking with cross-encoder
- Phase 4: EvidenceGraph with PostgreSQL storage
- Phase 5: A/B testing for routing thresholds