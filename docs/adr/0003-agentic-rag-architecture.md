# ADR-0003: Agentic RAG Architecture

## Status
Accepted

## Context
The EthioBio AI Assistant needs to handle complex queries that require multi-step reasoning, iterative retrieval, and evidence verification. The existing pipeline (Orchestrator → Retrieval → Tutor → Safety) is sufficient for simple queries but lacks the sophistication needed for complex educational questions.

## Decision
Implement a Google-style Multi-Agent Agentic RAG platform with the following components:

### Architecture Components

1. **PlannerAgent** (`src/agents/planner/planner.py`)
   - Generates execution plans with subtasks via LLM
   - Determines complexity level and reasoning type
   - Fallback plan on LLM failure

2. **PlanExecutor** (`src/graph/nodes/plan_executor.py`)
   - Iterates subtasks sequentially
   - Calls QueryRewriter + SearchFanout per subtask
   - Appends retrieval feedback on re-entry loops

3. **QueryRewriter** (`src/graph/nodes/query_rewriter.py`)
   - Called inside PlanExecutor, not a separate graph node
   - Expands queries for better retrieval coverage
   - Generates source-aware query bundles (7 categories)
   - Heuristic decomposition fallback when LLM fails

4. **SearchFanout** (`src/graph/nodes/search_fanout.py`)
   - Called inside PlanExecutor, not a separate graph node
   - Parallel retrieval from 4 sources via `asyncio.gather()`
   - Sources: curriculum (ChromaDB), memory (PostgreSQL), learner profile, recommendations
   - Deduplicates and quality-filters results

5. **EvidenceGraphNode** (`src/graph/nodes/evidence_graph.py`)
   - Normalizes retrieval output into persisted, scored evidence
   - Deduplicates chunks, persists to PostgreSQL, runs EvidenceSelector
   - Populates `evidence_items` and `evidence_ids` for downstream nodes

6. **SufficientContextNode** (`src/graph/nodes/sufficient_context.py`)
   - Evaluates evidence sufficiency using heuristic scoring
   - Routes to synthesis (sufficient), rewrite (minor gap), or replan (major gap)
   - Threshold-based decision making (0.7 sufficiency threshold)

7. **SynthesisNode** (`src/graph/nodes/synthesis.py`)
   - LLM-based evidence synthesis into structured summary
   - Produces Key Facts, Cited Sources, Quoted Passages, Gaps, Quality

8. **TutorNode** (`src/graph/nodes/tutor.py`)
   - Dual-mode: legacy prompt or agentic synthesis with citation maps
   - Socratic mode, hint progression, learner-aware personalization
   - Misconception detection in responses

9. **HallucinationNode** (`src/graph/nodes/hallucination.py`)
   - Analyzes response text against citation map and evidence
   - Sets hallucination_rate and hallucination_report

10. **ClaimVerifierNode** (`src/graph/nodes/claim_verifier.py`)
    - Extracts factual claims from tutor responses (heuristic)
    - Verifies claims against evidence via verbatim quotes and citation IDs
    - Routes to finalize (≥0.6), revise (≥0.3, max 2 attempts), reject (<0.3)

11. **SafetyNode** (`src/graph/nodes/safety.py`)
    - LLM safety check for factual accuracy and grade-appropriateness
    - Citation pattern verification and verbatim quote verification
    - Sets requires_teacher_review for low-scoring responses

12. **PipelineMonitor** (`src/core/monitoring.py`)
    - Trace ID generation
    - Node-level performance tracking
    - Structured logging for observability

### Graph Topology

```
orchestrator → _route_after_orchestrator
    │
    ├── "planner" → plan_executor → evidence_graph → sufficient_context
    │       └── route_after_sufficiency:
    │           ├── "synthesis" → synthesis → tutor
    │           ├── "rewrite" → plan_executor
    │           └── "replan" → planner
    │
    ├── "retrieve" → tutor
    │                    │
    └── "skip_retrieval" → tutor
                             │
                  tutor → hallucination → claim_verifier
                      └── route_after_verification:
                          ├── "finalize" → safety → END
                          ├── "revise" → tutor (max 2)
                          └── "reject" → safety → END
```

**Iterative Loops:**
- `SUFFICIENT_CONTEXT` → rewrite (minor gap) → plan_executor, or replan (major gap) → planner
- `CLAIM_VERIFIER` → revise (poor grounding, max 2) → tutor, or finalize → safety
- `QueryRewriter` and `SearchFanout` run **inside** PlanExecutor per subtask, not as separate graph nodes

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
- `src/graph/nodes/orchestrator.py`: Hybrid routing (heuristic + LLM complexity scoring)
- `src/graph/nodes/claim_verifier.py`: Claim extraction, verification, revision loop
- `src/graph/nodes/tutor.py`: Dual-mode legacy/agentic tutor with revision feedback
- `src/api/graph.py`: Updated `/status` endpoint with new topology

### Files Created
- `src/graph/nodes/planner.py`: Planning node (wraps PlannerAgent)
- `src/graph/nodes/plan_executor.py`: Subtask iteration with per-step QueryRewriter + SearchFanout
- `src/graph/nodes/query_rewriter.py`: Query expansion and decomposition
- `src/graph/nodes/search_fanout.py`: Multi-source parallel retrieval
- `src/graph/nodes/evidence_graph.py`: Evidence persistence, dedup, and selection
- `src/graph/nodes/sufficient_context.py`: Context sufficiency evaluation
- `src/graph/nodes/synthesis.py`: Evidence synthesis into structured summary
- `src/graph/nodes/hallucination.py`: Response hallucination analysis
- `src/graph/nodes/safety.py`: LLM safety check + citation/quote verification
- `src/graph/state.py`: AgentState with 70+ fields for agentic RAG
- `src/core/monitoring.py`: Pipeline monitoring and observability
- `src/core/evidence/`: Evidence persistence (graph.py), selection (selector.py), scoring (scoring.py), summarization (summarizer.py), deduplication (deduplication.py)
- `src/core/loops/`: RetrievalLoopController and FeedbackProcessor
- `src/agents/planner/`: PlannerAgent with Plan/SubTask models
- `src/agents/synthesis.py`: TutorSynthesisAgent for evidence-to-summary
- `src/agents/tutor/tutor.py`: Agentic Tutor with citation extraction
- `tests/test_agentic_nodes.py`: Unit tests for all agentic nodes
- `tests/test_agentic_integration.py`: Integration tests
- `tests/test_benchmarks.py`: Performance benchmarks
- `tests/test_retrieval_loop.py`: Loop controller tests
- `tests/test_evidence_graph_node.py`: Evidence node tests
- `tests/journeys/`: End-to-end journey tests

### Test Results
- `tests/test_agentic_nodes.py`: ~32 passed
- `tests/test_agentic_integration.py`: ~7 integration tests
- `tests/test_benchmarks.py`: ~9 performance benchmarks
- `tests/test_retrieval_loop.py`: ~15 loop controller tests
- `tests/test_evidence_graph_node.py`: ~9 evidence graph tests
- `tests/journeys/`: 3 journey tests (weak genetics, misconception correction, study plan)

## Future Work
- Phase 2: LLM-based claim verification (replaces heuristic extraction)
- Phase 3: Real-time reranking with cross-encoder
- Phase 4: Revision feedback tracking in the dashboard
- Phase 5: A/B testing for routing thresholds