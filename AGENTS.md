# EthioBio AI Assistant — Agent Instructions

This is an Obsidian PARA vault. The project codebase is at `1-Projects/p000-Active/EthioBio AI Assistant/`. The `.env`, `.venv`, and all source files live there — NOT at root.

## Architecture

LangGraph pipeline: **Orchestrator → (Retrieve | SkipRetrieval) → Tutor → Safety → (finalize | revise→Tutor)**

```
entry → orchestrator → needs_retrieval? → retrieve ─┐
                  │                       skip_retr. ─┤
                  └──────────────────────────────────→ tutor → safety → END / revise
```

Key abstractions:
- **ProviderManager** (`src/llm/manager.py`) — Centralized orchestration with fallback chain (Ollama → OpenAI → Anthropic → OpenAI-compatible). Runtime model switching.
- **LLMProvider** (`src/llm/providers/base.py`) — Abstract interface. Implementations: `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`.
- **ModelRegistry** (`src/llm/registry.py`) — Auto-detects locally installed Ollama models via `/api/tags`.
- **ModelRouter** (`src/llm/router.py`) — Backward-compatible thin wrapper over `ProviderManager`.
- **VectorStoreAdapter** (`src/retrieval/adapter.py`) — ChromaDB wrapper. Swappable interface.
- **AgentState** (`src/graph/state.py`) — 20+ fields: intent, user_message, grade_level, language, retrieved_chunks, draft, confidence, safety, status, error, trace_id, preferred_model, etc.

## Entrypoints

| What | How | Process |
|------|-----|---------|
| API server | `python -m src.main` (FastAPI :8000) | uvicorn |
| Telegram bot | `python -m src.telegram.bot` | PTB polling, separate process |
| Full stack | `docker compose up --build` | app + bot + postgres + redis + ollama + dashboard |
| CLI | `ethiobio` / `ethiobio-bot` | pyproject.toml `[project.scripts]` |

## Developer Commands

```bash
# Run
python -m src.main                                     # :8000
python -m src.telegram.bot                             # bot (in another terminal)

# Model management (API)
curl http://localhost:8000/models                      # list available models
curl http://localhost:8000/models/active               # get active model
curl -X POST http://localhost:8000/models/active -H "Content-Type: application/json" -d '{"model": "gemma4:31b-cloud"}'
curl http://localhost:8000/models/health               # provider health
curl -X POST http://localhost:8000/models/refresh      # refresh Ollama cache

# Test (endpoint tests hit real Ollama — skip for unit-only)
pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"

# Lint & typecheck
ruff check .
mypy src/

# Infra
docker compose up -d postgres redis
```

## Key Gotchas

1. **`topic` filter in RetrievalFilter returns empty** — PDF chunks lack `topic` metadata. Use `grade_level` only; semantic search compensates.
2. **Telegram rejects HTTP URLs** — use `callback_data` not `url` for inline buttons.
3. **Telegram 4096-char limit** — use `_reply_long()` (at `bot.py:313`) to split responses.
4. **Only one bot instance** — `pkill -f telegram.bot` then `deleteWebhook?drop_pending_updates=true` + `getUpdates?offset=999999999`.
5. **Quiz/Lesson callback patterns must anchor at end**: `^quiz$` not `^quiz` (prevents re-entry from grade buttons).
6. **`telegram_id` must be BIGINT** — large user IDs overflow Integer.
7. **QuizAgent generates from RAG context** — retrieves 5 ChromaDB chunks, injects into system prompt, instructs LLM to answer strictly from context (see `src/agents/quiz.py:54-58`).
8. **Bidirectional safety revision** — SafetyNode can route `"revise"` or `"reject"` back to TutorNode for regeneration.
9. **`api_base_url` vs `dashboard_url`** — `api_base_url` is for Telegram bot to reach FastAPI backend (`http://app:8000` in Docker). `dashboard_url` is for dashboard links (`http://localhost:3000`).
10. **Ollama model cache** — `OllamaProvider` and `ModelRegistry` both cache model lists. Use `POST /models/refresh` to clear both.
11. **`__model__:` system message convention** — OllamaProvider prepends `__model__:<name>` to system prompt for per-request model selection.
12. **`UsageInfo` TypedDict** — Provider responses include token usage as `UsageInfo` (`prompt_tokens`, `completion_tokens`, `total_tokens`).

## Testing

- `pytest` with `asyncio_mode = "auto"` (set in `pyproject.toml`)
- Tests mock `ProviderManager` and `VectorStoreAdapter` via `conftest.py` fixtures (`mock_router`, `mock_retriever`)
- Quiz/lesson tests mock `_call_llm` directly on the agent instance
- Provider tests (`tests/test_llm.py`) cover `LLMProvider` ABC, `OllamaProvider`, `ModelRegistry`, `ProviderManager`
- No CI, no pre-commit, no integration containers
- Endpoint tests (`test_chat_endpoint`, `test_quiz_generate_endpoint`) require a running Ollama

## Tooling Config

| Tool | Config |
|------|--------|
| Ruff | `line-length=100`, `select=E,F,I,N,W` |
| Mypy | `strict=false`, `ignore_missing_imports=true` |
| Python | 3.12+, async everywhere (asyncpg, httpx) |
| Dashboard | Next.js in `dashboard/`, built via `Dockerfile.dashboard` |
| Providers | Ollama (primary), OpenAI, Anthropic, OpenAI-compatible (LM Studio, vLLM) |

## References

- `README.md` — API endpoints, full setup guide
- `.env.example` — all env vars
- `docker-compose.yml` — service topology (postgres+pgvector, redis, ollama with GPU)
