# Architecture — EthioSci AI Assistant

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
         safety ←───────────────────┘
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentState` | `src/graph/state.py:20` | 50+ fields with safe defaults, backward-compatible |
| `OrchestratorNode` | `src/graph/nodes/orchestrator.py:140` | LLM intent classification + heuristic complexity scoring |
| `PlannerNode` | `src/graph/nodes/planner.py:16` | Generates execution plans via `PlannerAgent` |
| `PlanExecutor` | `src/graph/nodes/plan_executor.py:24` | Iterates subtasks, calls QueryRewriter + SearchFanout per subtask |
| `QueryRewriterNode` | `src/graph/nodes/query_rewriter.py:20` | LLM-based query expansion with heuristic fallback |
| `SearchFanoutNode` | `src/graph/nodes/search_fanout.py:27` | Parallel retrieval via `asyncio.gather()` |
| `EvidenceGraphNode` | `src/graph/nodes/evidence_graph.py:26` | Persists, selects, and scores evidence records |
| `SufficientContextNode` | `src/graph/nodes/sufficient_context.py:75` | Heuristic coverage evaluation, routes to rewrite/replan/synthesis |
| `RetrievalNode` | `src/graph/nodes/retrieval.py:49` | Legacy 3-round curriculum search |
| `SkipRetrievalNode` | `src/graph/nodes/retrieval.py:147` | Sets empty chunks and context |
| `SynthesisNode` | `src/graph/nodes/synthesis.py:16` | LLM-based evidence synthesis |
| `TutorNode` | `src/graph/nodes/tutor.py:109` | Dual-mode tutor (legacy prompt or agentic synthesis) |
| `HallucinationNode` | `src/graph/nodes/hallucination.py:6` | Scans response against citation map |
| `ClaimVerifierNode` | `src/graph/nodes/claim_verifier.py:197` | LLM claim verification, routes to finalize/revise/reject |
| `SafetyNode` | `src/graph/nodes/safety.py:114` | LLM safety check + citation/quote verification |

## Key Abstractions

- **ProviderManager** (`src/llm/manager.py`) — Centralized orchestration with fallback chain (Ollama → OpenRouter → OpenAI → Anthropic → OpenAI-compatible). Runtime model switching.
- **CircuitBreaker** (`src/llm/circuit_breaker.py`) — Per-provider state machine (CLOSED→OPEN→HALF_OPEN). Threshold=5, recovery_timeout=30s, half_open_max=3.
- **LLMProvider** (`src/llm/providers/base.py`) — Abstract interface. Implementations: `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`, `OpenRouterProvider`.
- **ModelRegistry** (`src/llm/registry.py`) — Auto-detects locally installed Ollama models via `/api/tags`.
- **ModelRouter** (`src/llm/router.py`) — Backward-compatible thin wrapper over `ProviderManager`.
- **VectorStore** (`src/rag/vector_store.py`) — pgvector wrapper (ChromaDB removed). Delegating wrapper for backward compat.
- **TieredRateLimiter** (`src/guardrails/input/rate_limiter.py`) — 6 tiers (auth/otp/chat/write/read/internal) with Redis sorted sets.
- **AppError** (`src/core/errors.py`) — Base class for all structured API errors. Subclasses: `AuthError`, `RateLimitError`, `NotFoundError`, `ValidationError`, etc.

## Entry Points

```python
from src.graph.orchestrator import run_graph

result = await run_graph(user_message="What is mitosis?", grade_level=10)
```

## Tests

```bash
pytest tests/test_agentic_nodes.py -v           # Unit tests
pytest tests/agents/test_planner.py -v          # Planner tests
pytest tests/test_guardrails/ -v                # Guardrail tests
```

## Routing Logic

| Query Complexity | Pipeline | Nodes |
|------------------|----------|-------|
| Simple (fact lookup) | Direct | orchestrator → retrieve → tutor → hallucination → claim_verifier → safety |
| Complex (multi-hop) | Agentic | orchestrator → planner → plan_executor → evidence_graph → sufficient_context → synthesis → tutor → hallucination → claim_verifier → safety |
