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

## Dashboard Gamification Widgets (`dashboard/src/components/gamification/`)

The dashboard gamification module displays XP, streaks, mastery levels, and achievements in the Next.js frontend.

- **Component hierarchy**: `GamificationProfile` fetches from `/gamification/profile/{user_id}` and composes `XpCard`, `StreakWidget`, `MasteryProgressBar`, and `AchievementPanel`.
- **Backend API** is at `src/api/gamification.py` — fully built with `/gamification/profile/{user_id}`, `/gamification/events/{user_id}`, `/gamification/achievements/{user_id}` endpoints.
- **API proxy**: Add `/gamification/:path*` rewrite in `dashboard/next.config.js` to connect frontend to backend.
- **Adding a new widget**: Create component in `dashboard/src/components/gamification/`, import into `GamificationProfile`, add to render layout.
- **Achievement definitions** must match backend's `ACHIEVEMENT_DEFINITIONS` in `src/api/gamification.py` — the frontend `GamificationProfile` component has a duplicate list for locked/unlocked display.
- **Single-page integration**: Drop `<GamificationProfile userId={id} />` into any page that has a user ID (e.g., student detail page).
- **TypeScript typecheck**: Run `npx tsc --noEmit` in `dashboard/` to verify all gamification components.

## Export Module (`src/export/`, `src/api/export.py`)

The export module generates downloadable DOCX and PDF files for quizzes and lesson plans.

- **DOCX**: Use `python-docx` `Document` with `BytesIO` buffer. The returned bytes are ZIP-compressed — do not assert text content directly in tests.
- **PDF**: Use `fpdf2` subclassing `FPDF`. Prefer `cell()` with `new_x="LMARGIN"` / `new_y="NEXT"` over `multi_cell()` for simple text to avoid edge-case failures.
- **Adding exportable types**: Add exporter to both `docx_exporter.py` and `pdf_exporter.py`, then add endpoint in `src/api/export.py`.
- When registering a new router in `main.py`, both the import and `app.include_router()` call must be added.

## Gamification Reward Integration

When adding XP rewards to a new activity type:

1. **Define the XP source** in `XP_SOURCES` dict in `src/api/gamification.py` (amount is the "configurable trigger")
2. **Wire into REST API**: In the endpoint handler, call `award_xp(user_id, source, amount, meta, session)` then `update_streak()` then `check_achievements()`. Include `xp_awarded`, `level_up`, `new_level` in the response schema.
3. **Wire into Telegram bot**: Create a `_save_<activity>_rewards()` helper following the `_save_quiz_rewards`/`_save_tutor_rewards` pattern (look up user by telegram_id, award XP in async session, store in `context.user_data`).
4. **Display feedback**: For API responses, add XP fields to the response schema. For bot, check `context.user_data["last_xp_awarded"]` and `last_level_up` and append to response text.

## Recovery Plan Module (`src/api/recovery.py`, `src/schemas/recovery.py`, `src/database/models.py`)

The recovery plan module tracks student remediation tasks and awards XP for completion.

- **Models**: `RecoveryPlan` (user_id, topic, total_tasks, completed_tasks, status) and `RecoveryTask` (plan_id, title, task_type, is_completed, xp_awarded) in `src/database/models.py`
- **XP sources**: `recovery_task_completion` (40 XP per task) and `recovery_milestone` (bonus XP at 3/5/10/15 tasks) — both defined in `XP_SOURCES` and `RECOVERY_MILESTONE_THRESHOLDS` in `src/api/gamification.py`
- **Endpoints**: `POST /recovery/plan` (create), `GET /recovery/plan/{user_id}` (list), `POST /recovery/task/complete?task_id=&user_id=` (complete task → awards XP + milestone checks), `GET /recovery/dashboard/{user_id}` (combined: weak topics + active plans + recommendations)
- **Profile integration**: `GamificationProfileResponse` includes optional `recovery_progress` field showing active plans, task counts, and overall progress %
- **Frontend**: `RecoveryProgressCard.tsx` shows recovery progress in the student dashboard via `GamificationProfile`
- **Recovery dashboard page**: `dashboard/src/app/recovery/page.tsx` — standalone page with student UUID selector, shows weak topics with severity, active plans with task timeline, rule-based recommendations (prioritized: high/medium/low). Add both sidebar link and `/recovery/:path*` API rewrite.
- **Router registration**: Add `recovery` to imports and `app.include_router(recovery.router)` in `src/main.py`

## Key Gotchas

1. **`topic` filter in RetrievalFilter returns empty** — PDF chunks lack `topic` metadata. Use `grade_level` only; semantic search compensates.
2. **Hint progression shares pattern with socratic_mode** — add field to AgentState → wire through prompts (both TutorAgent and TutorNode) → expose in schemas → add bot UI. Use `_build_system_prompt()` factory pattern for prompt variants.
3. **Telegram rejects HTTP URLs** — use `callback_data` not `url` for inline buttons.
4. **Telegram 4096-char limit** — use `_reply_long()` (at `bot.py:313`) to split responses.
5. **Only one bot instance** — `pkill -f telegram.bot` then `deleteWebhook?drop_pending_updates=true` + `getUpdates?offset=999999999`.
6. **Quiz/Lesson callback patterns must anchor at end**: `^quiz$` not `^quiz` (prevents re-entry from grade buttons).
7. **`telegram_id` must be BIGINT** — large user IDs overflow Integer.
8. **QuizAgent generates from RAG context** — retrieves 5 ChromaDB chunks, injects into system prompt, instructs LLM to answer strictly from context (see `src/agents/quiz.py:54-58`).
9. **Bidirectional safety revision** — SafetyNode can route `"revise"` or `"reject"` back to TutorNode for regeneration.
10. **`api_base_url` vs `dashboard_url`** — `api_base_url` is for Telegram bot to reach FastAPI backend (`http://app:8000` in Docker). `dashboard_url` is for dashboard links (`http://localhost:3000`).
11. **Ollama model cache** — `OllamaProvider` and `ModelRegistry` both cache model lists. Use `POST /models/refresh` to clear both.
12. **`__model__:` system message convention** — OllamaProvider prepends `__model__:<name>` to system prompt for per-request model selection.
13. **`UsageInfo` TypedDict** — Provider responses include token usage as `UsageInfo` (`prompt_tokens`, `completion_tokens`, `total_tokens`).
14. **Misconception detection is heuristic** — Uses `re.split()` sentence splitting + keyword matching on LLM response text. No NLP model needed. Both TutorAgent and TutorNode have parallel `MISCONCEPTION_INDICATORS` lists and `detect_misconception()` helpers that must stay in sync.
15. **Weak topic detection** — After quiz submit, `analyze_quiz_attempt()` in `src/agents/weak_topic_detection.py` analyzes per-topic scores, updates/creates `StudentMastery` records, detects `MisconceptionPattern` from repeated wrong answers, and syncs `StudentProfile.weak_areas`/`topic_mastery`. Wire into endpoint AFTER gamification, BEFORE session.commit().
16. **`QuizAttempt.answers` is `Mapped[dict]` but stores list data** — when accessing, safely cast with `cast(list[Any], raw) if isinstance(raw, list) else []` to satisfy mypy.

## Ralph PRD Generation (`scripts/ralph/`)

When converting a PRD to `prd.json`:

- Use the **Ralph skill** (`skills/ralph`) for the conversion format
- **Must include** a non-empty top-level `"title"` field matching the feature name (validated by `ralph.sh`)
- Split large stories into iteration-sized pieces (schema → backend → UI order)
- Every story must have `"Typecheck passes"` as the final acceptance criterion
- UI stories must also include `"Verify in browser using Playwright browser tools"`

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
