# Architecture — EthioBio AI Assistant

Read when: understanding the pipeline, adding/modifying graph nodes, working with evidence or planning.

## Unified LangGraph Pipeline

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
    └── "skip_retrieval" → tutor

tutor → hallucination → claim_verifier → route_after_verification
    ├── "finalize" → safety → END
    ├── "revise" → tutor (max 2 revisions)
    └── "reject" → safety → END
```

## Agentic RAG Architecture

```
orchestrator → planner → plan_executor → evidence_graph → sufficient_context
                  │                                              │
                  │                                         (gap?)
                  │                                     ┌──────┼──────┐
                  │                                  rewrite replan synthesis
                  │                                     │       │       │
                  └─────────────────────────────────────┘       │       │
                                                                 │       │
                                                           plan_executor │
                                                                         │
                                                                    synthesis → tutor → hallucination → claim_verifier
                                                                                                          │
                                                                                                    (verdict)
                                                                                                 ┌────┼────┐
                                                                                             finalize revise reject
                                                                                                 │       │      │
                                                                                              safety ←─────┘      │
                                                                                                 │               │
                                                                                                 └────←──────────┘
                                                                                                         (max 2)
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentState` | `src/graph/state.py:20` | 70+ fields with safe defaults, backward-compatible |
| `PlannerAgent` | `src/agents/planner/planner.py` | Generates execution plans via LLM |
| `PlanExecutor` | `src/graph/nodes/plan_executor.py` | Iterates subtasks, calls QueryRewriter + SearchFanout per subtask |
| `QueryRewriter` | `src/graph/nodes/query_rewriter.py` | LLM-based query expansion with heuristic fallback (called inside PlanExecutor) |
| `SearchFanout` | `src/graph/nodes/search_fanout.py` | Parallel retrieval via `asyncio.gather()` (called inside PlanExecutor) |
| `EvidenceGraphNode` | `src/graph/nodes/evidence_graph.py` | Persists, selects, and scores evidence records |
| `SufficientContextNode` | `src/graph/nodes/sufficient_context.py` | Heuristic coverage evaluation, routes to rewrite/replan/synthesis |
| `SynthesisNode` | `src/graph/nodes/synthesis.py` | LLM-based evidence synthesis into structured summary |
| `TutorNode` | `src/graph/nodes/tutor.py` | Dual-mode tutor (legacy prompt or agentic synthesis) |
| `HallucinationNode` | `src/graph/nodes/hallucination.py` | Analyzes response against citation map |
| `ClaimVerifierNode` | `src/graph/nodes/claim_verifier.py` | Claim extraction and verification, routes to finalize/revise/reject |
| `SafetyNode` | `src/graph/nodes/safety.py` | LLM safety check + citation/quote verification |
| `EvidenceGraph` | `src/core/evidence/graph.py` | PostgreSQL CRUD, session-scoped |
| `EvidenceSelector` | `src/core/evidence/selector.py` | Selects evidence for Tutor |
| `ConfidenceScore` | `src/core/evidence/scoring.py` | Weighted confidence calculation |
| `CoverageAnalysis` | `src/core/evidence/scoring.py` | Coverage gap detection |
| `EvidenceSummary` | `src/core/evidence/summarizer.py` | Evidence summarization |
| `PipelineMonitor` | `src/core/monitoring.py` | Trace-level observability |

## Key Abstractions

- **ProviderManager** (`src/llm/manager.py`) — Centralized orchestration with fallback chain (Ollama → OpenAI → Anthropic → OpenAI-compatible). Runtime model switching.
- **LLMProvider** (`src/llm/providers/base.py`) — Abstract interface. Implementations: `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`.
- **ModelRegistry** (`src/llm/registry.py`) — Auto-detects locally installed Ollama models via `/api/tags`.
- **ModelRouter** (`src/llm/router.py`) — Backward-compatible thin wrapper over `ProviderManager`.
- **VectorStoreAdapter** (`src/retrieval/adapter.py`) — ChromaDB wrapper. Swappable interface.
- **AgentState** (`src/graph/state.py`) — Fields: intent, user_message, grade_level, language, retrieved_chunks, draft, confidence, safety, status, error, trace_id, preferred_model, etc.

## Entry Points

```python
from src.graph.orchestrator import run_graph

result = await run_graph(user_message="What is mitosis?", grade_level=10)
```

## Tests

```bash
pytest tests/test_agentic_nodes.py -v           # Unit tests (32 tests)
pytest tests/agents/test_planner.py -v          # Planner tests (20 tests)
pytest tests/test_benchmarks.py -v              # Benchmarks (9 tests)
```
