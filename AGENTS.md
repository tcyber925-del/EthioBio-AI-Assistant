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
- **Backend API** is at `src/api/gamification.py` — fully built with `GET /gamification/profile/{user_id}`, `POST /gamification/xp`, `POST /gamification/activity`, `GET /gamification/events/{user_id}`, `GET /gamification/achievements/{user_id}` endpoints.
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

## Notifications Module (`src/api/notifications.py`, `src/notifications/`)

The notifications module manages user email preferences and sends automated emails.

- **Model**: `NotificationPreference` (user_id UUID PK, email, email_verified, digest_frequency, milestone_alerts, review_reminders, verification fields) in `src/database/models.py`
- **API**: `GET/PUT /notifications/preferences/{user_id}`, `POST /notifications/preferences/{user_id}/verify` (send code), `POST /notifications/preferences/{user_id}/verify/{code}` (confirm)
- **Email service**: `src/notifications/email_service.py` — async SMTP via `asyncio.to_thread()`, settings-driven from `src.config.Settings.email_host|port|user|password|from|use_tls`
- **Templates**: 3 Jinja2 HTML templates in `src/notifications/templates/`: `milestone_alert.html`, `digest.html`, `review_reminder.html`
- **Digest script**: `scripts/send_digests.py` — cron-ready script that sends daily/weekly digests to opted-in users with opted-in users' mastery changes and due reviews
- **Milestone email**: Sent from `POST /recovery/task/complete` when plan progress reaches ≥10%, using `MILESTONE_EMAIL_THRESHOLD` constant
- **Router registration**: Add `notifications` to imports and `app.include_router(notifications.router)` in `src/main.py`
- **Config**: Email settings in `src/config.py` as `email_host`, `email_port`, `email_user`, `email_password`, `email_from`, `email_use_tls`

## Recovery Plan Module (`src/api/recovery.py`, `src/schemas/recovery.py`, `src/database/models.py`)

The recovery plan module tracks student remediation tasks and awards XP for completion.

- **Models**: `RecoveryPlan` (user_id, topic, total_tasks, completed_tasks, status) and `RecoveryTask` (plan_id, title, task_type, is_completed, xp_awarded) in `src/database/models.py`
- **XP sources**: `recovery_task_completion` (40 XP per task) and `recovery_milestone` (bonus XP at 3/5/10/15 tasks) — both defined in `XP_SOURCES` and `RECOVERY_MILESTONE_THRESHOLDS` in `src/api/gamification.py`
- **Endpoints**: `POST /recovery/plan` (create), `GET /recovery/plan/{user_id}` (list), `POST /recovery/task/complete?task_id=&user_id=` (complete task → awards XP + milestone checks + milestone email), `GET /recovery/dashboard/{user_id}` (combined: weak topics + active plans + recommendations)
- **Milestone email**: When a task completion pushes plan progress ≥10%, sends a milestone alert email to the user's verified email (if they have milestone_alerts enabled)
- **Profile integration**: `GamificationProfileResponse` includes optional `recovery_progress` field showing active plans, task counts, and overall progress %
- **Frontend**: `RecoveryProgressCard.tsx` shows recovery progress in the student dashboard via `GamificationProfile`
- **Dashboard visualizations** (in `dashboard/src/components/recovery/`):
  - `MasteryRadarChart.tsx` — Recharts radar chart shown when ≥3 weak topics
  - `ProgressTrendGraph.tsx` — Recharts line chart per topic
  - `TopicHeatmap.tsx` — CSS-grid heatmap of last 28 days
  - `LearningTree.tsx` — Expandable recursive topic tree
- **Recovery dashboard page**: `dashboard/src/app/recovery/page.tsx` — standalone page with student UUID selector, shows all 4 visualizations + plan timeline
- **Telegram bot commands**: `/recovery` (view plans/tasks), `/progress` (text bar charts), `recovery_complete_` callback (complete tasks)
- **Router registration**: Add `recovery` to imports and `app.include_router(recovery.router)` in `src/main.py`

## Adaptive Quiz Engine (`src/agents/adaptive_quiz.py`, `src/database/models.py`)

The adaptive quiz engine tracks individual question attempts and estimates student ability per topic using a Bayesian IRT model.

- **Models**:
  - `QuestionAttempt` (id, user_id, question_id, quiz_id, correct, time_spent, hints_used, attempt_number) — records every answer
  - `StudentAbility` (user_id + topic composite PK, ability_score, uncertainty, attempt_count) — per-topic IRT estimates
  - `Question.difficulty_score` — Float column (-1.0 easy, 0.0 medium, 1.0 hard) for numeric difficulty
- **Functions** (in `src/agents/adaptive_quiz.py`):
  - `record_attempt()` — records a question attempt with auto-incrementing attempt_number
  - `estimate_bayesian_ability()` — logit-based Bayesian ability estimation with prior weighting
  - `update_ability()` — upserts per-topic ability after a quiz submit
  - `get_ability()` — returns (ability_score, uncertainty, attempt_count) for a user+topic
  - `select_adaptive_questions()` — selects questions closest to `ability + 0.5` (optimal challenge)
  - `migrate_difficulty_scores()` — one-time migration from string to numeric difficulty
- **Adaptive quiz**: Pass `"adaptive": true` in `POST /quiz/generate` body to enable adaptive difficulty selection
- **Wiring**: `POST /quiz/submit` automatically records attempts and updates ability estimates

## Learning Recommendation Engine (`src/core/learning_intelligence/recommendation/`)

The recommendation engine produces prioritized educational actions from `LearnerSnapshot` data.

- **Models** at `recommendation/models/`: `LearningActionType` enum (9 values) and `LearningRecommendation` pydantic model (id, action_type, topic, priority_score, reason, explanation, generated_at, metadata)
- **Scoring** at `recommendation/scoring/`: `PriorityCalculator` class with `RAW_WEIGHTS` dict, `MAX_POSSIBLE_SCORE = 120`, `normalize()` (divides by 120, clamps 0-1), `deduplicate()` (merges by action_type+topic, keeps higher score), `score_and_sort()` (normalize → dedup → sort desc → top 5)
- **Rules** at `recommendation/rules/`: 5 async generators (`mastery_rules`, `recovery_rules`, `review_rules`, `misconception_rules`, `engagement_rules`) each taking `(snapshot: LearnerSnapshot) -> list[LearningRecommendation]`
- **Services** at `recommendation/services/`: `RecommendationEngine` (parallel gather → score_and_sort → ID assignment), `RecommendationService` (cache-first facade using CacheManager with `recommendations:` key prefix)
- **API** at `src/api/intelligence/router.py`: `GET /intelligence/recommendations/{user_id}` (top 5) and `GET /intelligence/next-action/{user_id}` (single best or `{}`)
- **Package convention**: Each sub-package (`models/`, `scoring/`, `rules/`, `services/`) has its own `__init__.py` re-exporting the public API
- **Test location**: Tests go in `tests/test_priority_calculator.py`, `tests/test_recommendation_rules.py`, `tests/test_recommendation_engine.py`, `tests/test_recommendation_service.py`

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
17. **`send_email()` silently returns False when unconfigured** — No error is raised if `email_host` is unset. Always check the return value or log the result.
18. **NotificationPreference has a 1:1 user_id PK** — There is no separate `id` column; `user_id` is the PK. Upsert on conflict or check existence before `PUT`.
19. **Milestone email fires at 10% progress intervals** — `MILESTONE_EMAIL_THRESHOLD = 10.0` means the alert triggers when completion percentage crosses 10%, 20%, 30%, etc. — not at every individual task completion.
20. **Adaptive quiz requires user_id for topic ability lookup** — `select_adaptive_questions()` falls back to random selection when `user_id` is not provided; adaptive mode only works when both `adaptive=true` and `user_id` are set.
21. **`requires_planning` gates Agentic RAG** — OrchestratorNode derives `requires_planning` from `subtasks` count, NOT from intent. Use `build_unified_graph()` for production.
22. **PlannerAgent requires `objective` field** — `Plan` model uses `objective` (not `query`); `ComplexityLevel` uses LOW/MEDIUM/HIGH enum values.
23. **QueryRewriter uses LLM with heuristic fallback** — When `router` is provided, uses LLM for rewriting; falls back to heuristic expansion. Check `retrieval_metadata["method"]` for "llm" or "heuristic".
24. **SearchFanout uses parallel retrieval** — Executes all index-query combinations concurrently via `asyncio.gather()`. Fallback to sequential on error.
25. **EvidenceGraph stores full chunk content** — Per ADR-0001, evidence records store complete text (not just IDs) for auditability. `EvidenceRecord` is defined in `src/database/models.py`.

## Agentic RAG Pipeline (`src/graph/nodes/`, `src/core/evidence/`, `src/agents/planner/`)

The EthioBio AI Assistant includes a Google-style Multi-Agent Agentic RAG platform for complex educational queries.

### Architecture

```
orchestrator → planner → plan_executor → query_rewriter → search_fanout
                  │                        │                   │
                  │                   (per subtask)        (parallel)
                  │                                           │
                  └─────────────────────────────────────────→ sufficient_context
                                                                      │
                                                              (gap? rewrite/replan)
                                                                      │
                                                              tutor → claim_verifier → safety
                                                                      │
                                                              (revise/finalize/reject)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentState` | `src/graph/state.py:73` | 60 fields with safe defaults, backward-compatible |
| `PlannerAgent` | `src/agents/planner/planner.py` | Generates execution plans via LLM |
| `PlanExecutor` | `src/graph/nodes/plan_executor.py` | Iterates subtasks, manages execution |
| `QueryRewriter` | `src/graph/nodes/query_rewriter.py` | LLM-based query expansion with heuristic fallback |
| `SearchFanout` | `src/graph/nodes/search_fanout.py` | Parallel retrieval via `asyncio.gather()` |
| `SufficientContextNode` | `src/graph/nodes/sufficient_context.py` | Heuristic coverage evaluation |
| `ClaimVerifierNode` | `src/graph/nodes/claim_verifier.py` | Claim extraction and verification |
| `EvidenceGraph` | `src/core/evidence/graph.py` | PostgreSQL CRUD, session-scoped |
| `EvidenceSelector` | `src/core/evidence/selector.py` | Selects evidence for Tutor |
| `ConfidenceScore` | `src/core/evidence/scoring.py` | Weighted confidence calculation |
| `CoverageAnalysis` | `src/core/evidence/scoring.py` | Coverage gap detection |
| `EvidenceSummary` | `src/core/evidence/summarizer.py` | Evidence summarization |
| `AgentResult` | `src/graph/nodes/agent_result.py` | Standardized agent results |
| `PipelineMonitor` | `src/core/monitoring.py` | Trace-level observability |

### Entry Points

```python
from src.graph.orchestrator import build_unified_graph, build_graph

# Production (with monitoring)
graph = build_unified_graph(retriever, router)
result = await graph.ainvoke(state)

# Legacy (simple pipeline)
graph = build_graph(retriever, router)
result = await graph.ainvoke(state)
```

### Tests

```bash
# Unit tests (32 tests)
pytest tests/test_agentic_nodes.py -v

# Planner tests (20 tests)
pytest tests/agents/test_planner.py -v

# Benchmarks (9 tests)
pytest tests/test_benchmarks.py -v
```

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
