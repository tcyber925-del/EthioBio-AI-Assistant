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
- **ModelRouter** (`src/llm/router.py`) — Ollama primary (gemma4:31b-cloud), OpenAI/Anthropic fallback. Confidence-based fallback when < 0.5.
- **VectorStoreAdapter** (`src/retrieval/adapter.py`) — ChromaDB wrapper. Swappable interface.
- **AgentState** (`src/graph/state.py`) — 20+ fields: intent, user_message, grade_level, language, retrieved_chunks, draft, confidence, safety, status, error, trace_id, etc.

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

## Testing

- `pytest` with `asyncio_mode = "auto"` (set in `pyproject.toml`)
- Tests mock `ModelRouter` and `VectorStoreAdapter` via `conftest.py` fixtures (`mock_router`, `mock_retriever`)
- Quiz/lesson tests mock `_call_llm` directly on the agent instance
- No CI, no pre-commit, no integration containers
- Endpoint tests (`test_chat_endpoint`, `test_quiz_generate_endpoint`) require a running Ollama

## Tooling Config

| Tool | Config |
|------|--------|
| Ruff | `line-length=100`, `select=E,F,I,N,W` |
| Mypy | `strict=false`, `ignore_missing_imports=true` |
| Python | 3.12+, async everywhere (asyncpg, httpx) |
| Dashboard | Next.js in `dashboard/`, built via `Dockerfile.dashboard` |

## References

- `README.md` — API endpoints, full setup guide
- `.env.example` — all env vars
- `docker-compose.yml` — service topology (postgres+pgvector, redis, ollama with GPU)
