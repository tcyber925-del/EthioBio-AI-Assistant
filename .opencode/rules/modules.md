# Modules — EthioSci AI Assistant

Read when: working on gamification, export, notifications, recovery plans, or Ralph PRD generation.

## Dashboard Gamification Widgets (`dashboard/src/components/gamification/`)

- **Component hierarchy**: `GamificationProfile` fetches from `/gamification/profile/{user_id}` and composes `XpCard`, `StreakWidget`, `MasteryProgressBar`, and `AchievementPanel`.
- **Backend API** at `src/api/gamification.py`: `GET /gamification/profile/{user_id}`, `POST /gamification/xp`, `POST /gamification/activity`, `GET /gamification/events/{user_id}`, `GET /gamification/achievements/{user_id}`.
- **API proxy**: Add `/gamification/:path*` rewrite in `dashboard/next.config.js`.
- **Adding a new widget**: Create component in `dashboard/src/components/gamification/`, import into `GamificationProfile`, add to render layout.
- **Achievement definitions** must match backend's `ACHIEVEMENT_DEFINITIONS` in `src/api/gamification.py`.
- **Single-page integration**: Drop `<GamificationProfile userId={id} />` into any page with a user ID.
- **TypeScript typecheck**: Run `npx tsc --noEmit` in `dashboard/`.

### Gamification Reward Integration

When adding XP rewards to a new activity type:

1. **Define the XP source** in `XP_SOURCES` dict in `src/api/gamification.py`.
2. **Wire into REST API**: call `award_xp(user_id, source, amount, meta, session)` → `update_streak()` → `check_achievements()`. Include `xp_awarded`, `level_up`, `new_level` in response schema.
3. **Wire into Telegram bot**: create `_save_<activity>_rewards()` helper following `_save_quiz_rewards` / `_save_tutor_rewards` pattern.
4. **Display feedback**: API → add XP fields to schema. Bot → check `context.user_data["last_xp_awarded"]` and `last_level_up`.

## Export Module (`src/export/`, `src/api/export.py`)

Generates downloadable DOCX and PDF files for quizzes and lesson plans.

- **DOCX**: Use `python-docx` `Document` with `BytesIO` buffer. The returned bytes are ZIP-compressed — do not assert text content directly in tests.
- **PDF**: Use `fpdf2` subclassing `FPDF`. Prefer `cell()` with `new_x="LMARGIN"` / `new_y="NEXT"` over `multi_cell()` for simple text.
- **Adding exportable types**: Add exporter to both `docx_exporter.py` and `pdf_exporter.py`, then add endpoint in `src/api/export.py`.
- When registering a new router in `main.py`, both the import and `app.include_router()` call must be added.

## Notifications Module (`src/api/notifications.py`, `src/notifications/`)

- **Model**: `NotificationPreference` (user_id UUID PK, email, email_verified, digest_frequency, milestone_alerts, review_reminders) in `src/database/models.py`.
- **API**: `GET/PUT /notifications/preferences/{user_id}`, `POST /notifications/preferences/{user_id}/verify` (send code), `POST /notifications/preferences/{user_id}/verify/{code}` (confirm).
- **Email service**: `src/notifications/email_service.py` — async SMTP via `asyncio.to_thread()`, settings-driven from `src.config.Settings.email_host|port|user|password|from|use_tls`.
- **Templates**: 3 Jinja2 HTML templates in `src/notifications/templates/`: `milestone_alert.html`, `digest.html`, `review_reminder.html`.
- **Digest script**: `scripts/send_digests.py` — cron-ready, sends daily/weekly digests.
- **Milestone email**: Sent from `POST /recovery/task/complete` at ≥10% progress intervals.
- **Router registration**: Add `notifications` to imports and `app.include_router(notifications.router)` in `src/main.py`.

## Recovery Plan Module (`src/api/recovery.py`, `src/schemas/recovery.py`, `src/database/models.py`)

- **Models**: `RecoveryPlan` (user_id, topic, total_tasks, completed_tasks, status) and `RecoveryTask` (plan_id, title, task_type, is_completed, xp_awarded).
- **XP sources**: `recovery_task_completion` (40 XP) and `recovery_milestone` (bonus at 3/5/10/15 tasks) in `XP_SOURCES` and `RECOVERY_MILESTONE_THRESHOLDS`.
- **Endpoints**: `POST /recovery/plan`, `GET /recovery/plan/{user_id}`, `POST /recovery/task/complete?task_id=&user_id=`, `GET /recovery/dashboard/{user_id}`.
- **Milestone email**: At ≥10% progress to verified email with milestone_alerts enabled.
- **Profile integration**: `GamificationProfileResponse` includes optional `recovery_progress`.
- **Frontend**: `RecoveryProgressCard.tsx` in student dashboard via `GamificationProfile`.
- **Dashboard visualizations** (in `dashboard/src/components/recovery/`):
  - `MasteryRadarChart.tsx` — Recharts radar chart (≥3 weak topics)
  - `ProgressTrendGraph.tsx` — Recharts line chart per topic
  - `TopicHeatmap.tsx` — CSS-grid heatmap of last 28 days
  - `LearningTree.tsx` — Expandable recursive topic tree
- **Recovery dashboard page**: `dashboard/src/app/recovery/page.tsx`.
- **Telegram bot**: `/recovery`, `/progress`, `recovery_complete_` callback.
- **Router registration**: Add `recovery` to imports and `app.include_router(recovery.router)` in `src/main.py`.

## Observability (`src/observability/`)

- **OTel tracing**: `otel_endpoint` env var (default None — in-memory only). Set to `http://jaeger:4317` in docker-compose.
- **Prometheus metrics**: `GET /metrics` — Counter/Gauge/Histogram registry; Prometheus scrapes on 15s interval.
- **Per-module health**: `GET /health/modules` — each guardrail module registers on startup.
- **Eval pipeline**: Async LLM-as-judge on ~10-20% sampled traffic, scores written as `gen_ai.evaluation.*` span attributes.
- **Instrumentation**: `@observe_guardrail(module, guardrail_type)` decorator wraps guardrail functions with OTel spans + counter metrics + health updates.
- **Dashboard stack**: Grafana (:3001, admin/ethiobio) + Prometheus (:9090) + Jaeger (:16686). Auto-provisioned datasource + EthioSci Overview dashboard.
- **Env guards**: `TRACELOOP_API_KEY` must be set for OpenLLMetry auto-instrumentation; code falls back gracefully.
- **New endpoint registration**: Add route + PlainTextResponse import in `src/main.py` for `/metrics`.

## Ralph PRD Generation (`scripts/ralph/`)

When converting a PRD to `prd.json`:

- Use the **Ralph skill** (`skills/ralph`) for the conversion format.
- **Must include** a non-empty top-level `"title"` field (validated by `ralph.sh`).
- Split large stories into iteration-sized pieces (schema → backend → UI).
- Every story must have `"Typecheck passes"` as the final acceptance criterion.
- UI stories must also include `"Verify in browser using Playwright browser tools"`.
