# Error-Handling Audit — EthioSci Dashboard Frontend

Date: 2026-08-11 · Mode: read-only audit · Task 01 of 17 (design: `docs/superpowers/specs/2026-08-11-error-handling-design.md`, plan: `docs/superpowers/plans/2026-08-11-error-handling.md`)

Scope: `dashboard/` (Next.js 14 App Router + next-intl en/am + vitest). Consumed by Tasks 08–13 (migrations + raw-error sweep).

---

## 1. API clients & entry points

### Client inventory

| Client | Location | Behavior |
|--------|----------|----------|
| `fetchWithAuth` | `src/lib/fetchWithAuth.ts` | Plain `fetch` with `credentials: "include"`; on 401 → POST `/auth/refresh` → retry once; refresh fails → hard redirect to `/login` (`window.location.href`, no guards) and throws `new Error("Session expired")`. No timeout, no error-shape parsing. |
| `fetchWithTimeout` | `src/lib/fetch.ts:5-30` | Adds 30s AbortController timeout, injects `Authorization: Bearer` from `_tokenCache`, cache-busts with `_t=`, throws `Error(json.detail \|\| json.error \|\| HTTP ${res.status})` on non-ok. **Bug site:** `json.error` is an object per the backend `{"error": {...}}` contract → `new Error(object)` → `[object Object]` visible to users. |
| `streamFetch` | `src/lib/fetch.ts:51-126` | SSE consumer for agent streams. Same raw `json.detail \|\| json.error` pattern in the non-ok path (`:73`), delivered through `callbacks.onError`. |
| `voice-turn.ts` | `src/lib/voice-turn.ts:55` | Duplicated copy of the raw `json.detail \|\| json.error` error extraction (non-ok path of voice turn POST), through `callbacks.onError`. |

### Consumers (`from '@/lib/fetchWithAuth'` — 53 files)

```
src/app/(dashboard)/admin/agents/page.tsx
src/app/(dashboard)/admin/content/lesson/[id]/page.tsx
src/app/(dashboard)/admin/content/page.tsx
src/app/(dashboard)/admin/content/quiz/[id]/page.tsx
src/app/(dashboard)/admin/layout.tsx
src/app/(dashboard)/admin/monitoring/page.tsx
src/app/(dashboard)/admin/page.tsx
src/app/(dashboard)/admin/review/page.tsx
src/app/(dashboard)/admin/schools/page.tsx
src/app/(dashboard)/admin/users/page.tsx
src/app/(dashboard)/ask/page.tsx
src/app/(dashboard)/assessment-studio/page.tsx
src/app/(dashboard)/assignments/[id]/grade/[submissionId]/page.tsx
src/app/(dashboard)/assignments/[id]/page.tsx
src/app/(dashboard)/assignments/my/[id]/page.tsx
src/app/(dashboard)/assignments/my/page.tsx
src/app/(dashboard)/assignments/new/page.tsx
src/app/(dashboard)/assignments/page.tsx
src/app/(dashboard)/classroom/[id]/page.tsx
src/app/(dashboard)/classroom/page.tsx
src/app/(dashboard)/dashboard/page.tsx
src/app/(dashboard)/diagrams/page.tsx
src/app/(dashboard)/digital-twin/page.tsx
src/app/(dashboard)/intervention-analytics/page.tsx
src/app/(dashboard)/knowledge-graph/page.tsx
src/app/(dashboard)/lessons/[id]/page.tsx
src/app/(dashboard)/lessons/page.tsx
src/app/(dashboard)/monitoring/page.tsx
src/app/(dashboard)/parent/page.tsx
src/app/(dashboard)/quiz/history/[id]/page.tsx
src/app/(dashboard)/quiz/history/page.tsx
src/app/(dashboard)/quiz/take/[id]/page.tsx
src/app/(dashboard)/quiz/take/page.tsx
src/app/(dashboard)/quizzes/[id]/page.tsx
src/app/(dashboard)/quizzes/page.tsx
src/app/(dashboard)/recovery/page.tsx
src/app/(dashboard)/student/page.tsx
src/app/(dashboard)/students/[id]/page.tsx
src/app/(dashboard)/students/page.tsx
src/app/(dashboard)/unit-plans/[id]/page.tsx
src/app/(dashboard)/unit-plans/page.tsx
src/app/(dashboard)/workspace/browse/[id]/page.tsx
src/app/(dashboard)/workspace/browse/page.tsx
src/app/(dashboard)/workspace/layout.tsx
src/app/(dashboard)/workspace/page.tsx
src/app/(dashboard)/workspace/processing/page.tsx
src/app/(dashboard)/workspace/search/page.tsx
src/components/ActivityFeed.tsx
src/components/agents/ExecutionPanel.tsx
src/components/agents/ReflectionTable.tsx
src/components/dashboard-v2/dashboards/AdminDashboard.tsx
src/components/dashboard-v2/dashboards/ParentDashboard.tsx
src/components/dashboard-v2/dashboards/SchoolDashboard.tsx
src/components/dashboard-v2/dashboards/StudentDashboard.tsx
src/components/dashboard-v2/dashboards/TeacherDashboard.tsx
src/components/gamification/GamificationProfile.tsx
src/components/icon-palette/IconPalette.tsx
src/components/learning/ContinueLearningFeed.tsx
src/components/learning/ExamReadinessCard.tsx
src/components/misconceptions/MisconceptionPanel.tsx
src/components/ModelSelector.tsx
src/hooks/useConversationHistory.ts
src/lib/voice-turn.ts
src/app/(marketing)/login/page.tsx
src/app/(marketing)/page.tsx
```

(64 distinct consumer files; both libs are consumable from any page/component — no central error handling exists at any boundary.)

### Consumers (`from '@/lib/fetch'` — 11 files, `fetchWithTimeout` / `streamFetch`)

```
src/app/(dashboard)/ask/page.tsx        (+ streamFetch: SSE agent stream)
src/app/(dashboard)/diagrams/page.tsx
src/app/(dashboard)/students/[id]/page.tsx
src/app/(marketing)/login/page.tsx
src/app/(marketing)/page.tsx
src/components/ActivityFeed.tsx
src/components/icon-palette/IconPalette.tsx
src/components/learning/ContinueLearningFeed.tsx
src/components/learning/ExamReadinessCard.tsx
src/components/ModelSelector.tsx
src/hooks/useConversationHistory.ts
```

### Other entry points

- **All `catch (` blocks (55 files):** every one of them eventually renders `err.message` (RAW_UI) or `String(err)`.
- **`initAuth()`/`getToken()`/`clearToken()`/`setToken()` consumers:** login + oauth callback (`setToken`), `layout.tsx` bootstraps (`getToken`), `ask/page.tsx` (`initAuth`), `Sidebar.tsx`, `SidebarV2.tsx` (`clearToken`), plus Bearer-token users of `TTSPlayButton`, `QuizVoiceButton`, `VoiceRecorderButton`, `useConversationHistory`, `admin/layout.tsx`, `workspace/upload/page.tsx`.

### Direct raw-`fetch` spots that duplicate the error-shape logic

- `src/lib/voice-turn.ts:55` — `json.detail || json.error` (copy of fetch.ts pattern).
- `src/app/(dashboard)/workspace/upload/page.tsx:80` — inline `throw new Error(json.detail || json.error || HTTP status)` (third copy; upload is not routed through any client) — **migrated (Task 12: `normalizeHttpError` + `ErrorAlert`, no raw extraction)**.

---

## 2. Auth mechanism

- `src/lib/auth.ts` — client-side JWT cache `_tokenCache` + `_decodedCache`; cookies `auth_ready=1` and `user_role` set via `setToken()` (1-day expiry); `clearToken()` POSTs `/auth/logout` (fire-and-forget, no await/error handling); `initAuth()` calls `/auth/me` and swallows failures; whole module is browser-only (no SSR guard).
- `src/middleware.ts` — edge middleware; redirects to `/login` when `access_token` cookie is missing for non-public, non-`/auth`, non-`/api` paths. Note: the cookie that gates SSR (`access_token`) differs from the client flag (`auth_ready`); the client refresh flow lives only in `fetchWithAuth`.
- `src/lib/fetchWithAuth.ts` — 401 → `/auth/refresh` → retry, else hard `window.location.href = "/login"` + throw `Error("Session expired")`. No redirect guard for repeated refresh loops; no handling of refresh-specific error codes (`auth_refresh_expired` etc.).
- Bearer-based clients (`fetchWithTimeout`, voice, TTS, conversation history) have **no** 401 recovery: a stale cached token produces a 401 whose `json.error` object becomes `[object Object]`.

---

## 3. Backend error formats (verified against `src/core/errors.py`, `src/main.py`, `src/api/admin.py`)

- `src/core/errors.py` defines `AppError` rendering as `{"error": {code, detail, context}}` via `to_dict()` (`errors.py:19`). Subclasses: `AuthError`→401 codes `auth_*`, `RateLimitError`→429 `rate_limit_exceeded` (+ `context.retry_after`), `NotFoundError`→404 `not_found_*`, `ConflictError`→409 `conflict_*`.
- FastAPI `HTTPException` → `{"detail": "string"}` (many routes, some leaky `detail=str(e)` 500s, e.g. `src/api/admin.py`: lines 153, 203, 228, 268, 279, 329, 372, 407, 649, 691).
- Pydantic validation 422 → `{"detail": [{loc, msg, type}]}`.
- Ad-hoc `{"error": "string"}` at `src/main.py:518` (503 "bot not ready") and `src/main.py:524` (403 "forbidden").
- Sanitized 500 `{error: {code: "internal_error", detail: "An unexpected error occurred"}}` handler at `src/main.py:371-377`.
- Known backend codes (enumerated): `auth_invalid_credentials, auth_invalid_token, auth_invalid_refresh, auth_invalid_ticket, auth_missing_token, auth_missing_refresh, auth_refresh_expired, auth_refresh_reused, auth_token_expired, auth_otp_expired, auth_otp_invalid, auth_user_inactive, auth_login_required, auth_invalid_payload, auth_internal_api_key_not_configured, auth_invalid_internal_api_key, conflict_email, conflict_oauth_identity_conflict, not_found_user, not_found_telegram_id, not_found_provider, rate_limit_exceeded, internal_error`

**Consequence for the frontend:** three mutually incompatible error shapes (`{"error": {code,detail,context}}`, `{"detail": "string"}`, `{"detail": [...]}`) plus plain-text bodies — every consumer must normalize, and the current `json.detail || json.error` reads the *object* branch when an `AppError` is involved, producing `[object Object]`.

---

## 4. Error UI inventory

**No shared error components exist.** Greps for `ErrorBanner|ErrorAlert|ErrorCard|ErrorMessage|ErrorState|AlertBanner|InlineError` within `src/components/` and `src/lib/` return zero results; there is no `components/shared/`, no error boundary (`error.tsx`) anywhere under `src/app/`, and no error i18n namespace beyond inline `t('...')` fallbacks scattered per page.

Every page/component rolls its own `useState<string | null>(null)` + `setError(err.message ...)` + inline `<p>{error}</p>` / `alert()` pattern. i18n coverage is inconsistent: some pages translate fallbacks (`t('error_load')`), most render English-only server strings.

---

## 5. Raw-rendering locations table (file · line · class)

Classes: `RAW_UI` (rendered user-facing — must migrate later), `LOGGING` (console — safe), `DERIVED` (used for branching), `RAW_SRC` (raw `json.detail || json.error` extraction site feeding UI — the `[object Object]` bug sites).

| File | Lines | Class |
|------|-------|-------|
| `src/lib/fetch.ts` | 21 (throw), 73 (onError) | `RAW_SRC` (bug site: `json.error` is object) |
| `src/lib/voice-turn.ts` | 55 | `RAW_SRC` (duplicate of bug site) |
| `src/app/(dashboard)/workspace/upload/page.tsx` | 80 (throw), 95 | `RAW_SRC`, `RAW_UI` — migrated (Task 12) |
| `src/app/(marketing)/login/page.tsx` | 52, 70, 89 | `RAW_UI` |
| `src/app/(marketing)/login/oauth/callback/page.tsx` | 40 | backend-driven via `setToken` (no inline error path; 401 → fetchWithAuth redirect) |
| `src/app/(dashboard)/students/page.tsx` | 36 | `RAW_UI` |
| `src/app/(dashboard)/students/[id]/page.tsx` | 34 | `RAW_UI` |
| `src/app/(dashboard)/dashboard/page.tsx` | 62 | `RAW_UI` |
| `src/components/dashboard-v2/dashboards/StudentDashboard.tsx` | 122 | `RAW_UI` |
| `src/components/dashboard-v2/dashboards/TeacherDashboard.tsx` | 51 | `RAW_UI` |
| `src/components/dashboard-v2/dashboards/AdminDashboard.tsx` | 51 | `RAW_UI` |
| `src/components/dashboard-v2/dashboards/ParentDashboard.tsx` | 61 | `RAW_UI` |
| `src/components/dashboard-v2/dashboards/SchoolDashboard.tsx` | 69 | `RAW_UI` |
| `src/app/(dashboard)/admin/agents/page.tsx` | 37 | `RAW_UI` |
| `src/app/(dashboard)/admin/monitoring/page.tsx` | 27 | `RAW_UI` |
| `src/app/(dashboard)/admin/users/page.tsx` | 51, 71, 87 | `RAW_UI` |
| `src/app/(dashboard)/admin/schools/page.tsx` | 35, 56 | `RAW_UI` |
| `src/app/(dashboard)/admin/review/page.tsx` | 57, 76 | `RAW_UI` |
| `src/app/(dashboard)/admin/content/page.tsx` | 49, 59 | `RAW_UI` |
| `src/app/(dashboard)/admin/content/quiz/[id]/page.tsx` | 43 | `RAW_UI` |
| `src/app/(dashboard)/admin/content/lesson/[id]/page.tsx` | 64 | `RAW_UI` |
| `src/app/(dashboard)/admin/page.tsx` | 32 | `RAW_UI` |
| `src/app/(dashboard)/admin/layout.tsx` | 25 | `RAW_UI` |
| `src/app/(dashboard)/ask/page.tsx` | 24 (`isServerError`), 355 | `DERIVED`, `RAW_UI` |
| `src/app/(dashboard)/lessons/page.tsx` | 58, 113 | `RAW_UI` |
| `src/app/(dashboard)/lessons/[id]/page.tsx` | 67, 79 | `RAW_UI` |
| `src/app/(dashboard)/unit-plans/page.tsx` | 58, 111 | `RAW_UI` |
| `src/app/(dashboard)/unit-plans/[id]/page.tsx` | 58 | `RAW_UI` |
| `src/app/(dashboard)/quizzes/page.tsx` | 46, 88 | `RAW_UI` |
| `src/app/(dashboard)/quizzes/[id]/page.tsx` | 45, 57 | `RAW_UI` |
| `src/app/(dashboard)/quiz/take/page.tsx` | 53, 105 | `RAW_UI` |
| `src/app/(dashboard)/quiz/take/[id]/page.tsx` | 72, 114 | `RAW_UI` |
| `src/app/(dashboard)/quiz/history/page.tsx` | 40 | `RAW_UI` |
| `src/app/(dashboard)/quiz/history/[id]/page.tsx` | 53 | `RAW_UI` |
| `src/app/(dashboard)/assignments/page.tsx` | 44 | `RAW_UI` |
| `src/app/(dashboard)/assignments/[id]/page.tsx` | 48, 58 (`alert`, `catch (err: any)`) | `RAW_UI` |
| `src/app/(dashboard)/assignments/my/page.tsx` | 33 | `RAW_UI` |
| `src/app/(dashboard)/assignments/my/[id]/page.tsx` | 36, 56 | `RAW_UI` |
| `src/app/(dashboard)/assignments/new/page.tsx` | 55 | `RAW_UI` |
| `src/app/(dashboard)/assignments/[id]/grade/[submissionId]/page.tsx` | 25, 44 | `RAW_UI` |
| `src/app/(dashboard)/classroom/page.tsx` | 47, 63 | `RAW_UI` |
| `src/app/(dashboard)/classroom/[id]/page.tsx` | 95 | `RAW_UI` |
| `src/app/(dashboard)/parent/page.tsx` | 92, 102 | `RAW_UI` |
| `src/app/(dashboard)/student/page.tsx` | 84 | `RAW_UI` |
| `src/app/(dashboard)/monitoring/page.tsx` | 58 | `RAW_UI` |
| `src/app/(dashboard)/intervention-analytics/page.tsx` | 57 | `RAW_UI` |
| `src/app/(dashboard)/assessment-studio/page.tsx` | 118 | `RAW_UI` |
| `src/app/(dashboard)/digital-twin/page.tsx` | 273, 345 (`{r.detail}` data-driven) | `RAW_UI` |
| `src/app/(dashboard)/knowledge-graph/page.tsx` | 95, 173, 200 | `RAW_UI` |
| `src/components/misconceptions/MisconceptionPanel.tsx` | 51, 69, 83 | `RAW_UI` |
| `src/app/(dashboard)/recovery/page.tsx` | 248 (`setError`), 428, 455 (`{n.message}`/`{rec.message}` data-driven) | `RAW_UI` |
| `src/app/(dashboard)/diagrams/page.tsx` | 101, 134, 175 (`setError`), 196 (`setSketchError`) | `RAW_UI` |
| `src/app/(dashboard)/workspace/page.tsx` | 48 | `RAW_UI` |
| `src/app/(dashboard)/workspace/browse/page.tsx` | 61, 96, 108, 118 (three `alert()`) | `RAW_UI` |
| `src/app/(dashboard)/workspace/browse/[id]/page.tsx` | 88 | `RAW_UI` |
| `src/app/(dashboard)/workspace/search/page.tsx` | 45 | `RAW_UI` |
| `src/app/(dashboard)/workspace/processing/page.tsx` | 38 | `RAW_UI` |
| `src/components/agents/ExecutionPanel.tsx` | 48 | `RAW_UI` |
| `src/components/agents/ReflectionTable.tsx` | 61 | `RAW_UI` |
| `src/components/ActivityFeed.tsx` | 52 | `RAW_UI` |
| `src/components/gamification/GamificationProfile.tsx` | 63 | `RAW_UI` |
| `src/components/learning/ContinueLearningFeed.tsx` | 86 | `RAW_UI` |
| `src/components/learning/ExamReadinessCard.tsx` | 88 | `RAW_UI` |
| `src/components/icon-palette/IconPalette.tsx` | 74, 93, 115, 145 | `RAW_UI` |
| `src/components/VoiceRecorderButton.tsx` | 91, 118 | `RAW_UI` |
| `src/components/QuizVoiceButton.tsx` | 88 | `RAW_UI` |
| `src/hooks/useVoiceTurn.ts` | 142 | `RAW_UI` |
| `src/components/ModelSelector.tsx` | 36 (`console.error('Failed to load models:', e)`) | `LOGGING` |
| `src/app/(marketing)/page.tsx` | 67 (`console.log` stats fallback) | `LOGGING` |
| `src/app/(dashboard)/recovery/page.tsx` | 234 | `LOGGING` |
| `src/app/(dashboard)/assessment-studio/page.tsx` | 60 | `LOGGING` |
| `src/app/(dashboard)/knowledge-graph/page.tsx` | 127 | `LOGGING` |
| `src/app/(dashboard)/lessons/page.tsx` | 70 | `LOGGING` |
| `src/app/(dashboard)/unit-plans/page.tsx` | 70 | `LOGGING` |
| `src/app/(dashboard)/workspace/layout.tsx` | 34 | `LOGGING` |
| `src/app/(dashboard)/quiz/take/[id]/page.tsx` | 298 (`onError={console.error}`) | `LOGGING` |

Counts: ~98 `RAW_UI` sites, 3 `RAW_SRC` bug sites (fetch.ts ×2, voice-turn.ts, upload — ALL eliminated: fetch.ts Task 05, upload Task 12, voice-turn Task 13-D), 9 `LOGGING`, 1 `DERIVED` pair (ask). Additional anti-pattern: `catch (err: any)` with implicit `any` (`fetch.ts`-adjacent callers, `assignments/[id]/page.tsx:58`) bypasses type-safe error narrowing — also eliminated (Tasks 11-13).

---

## 6. Feature surfaces to migrate (Tasks 08–13)

| Surface | Files | Notes |
|---------|-------|-------|
| Login / OAuth | `login/page.tsx`, `login/oauth/callback/page.tsx`, `src/middleware.ts`, `fetchWithAuth.ts` | `setToken` on success; three `RAW_UI` error sites; hard redirect on refresh failure |
| Students list + detail | `students/page.tsx`, `students/[id]/page.tsx` | `RAW_UI` at :36 / :34; Bearer via `fetchWithTimeout` in detail — migrated (Task 09) |
| v2 dashboards | `dashboard-v2/dashboards/*.tsx` (5 files) + `dashboard/page.tsx` | per-dashboard `setError` — migrated (Task 10) |
| Ask / voice / workspace | `ask/page.tsx`, `voice-turn.ts`, `useVoiceTurn.ts`, `VoiceRecorderButton.tsx`, `QuizVoiceButton.tsx`, `workspace/*` (6 pages) | `streamFetch` + `RAW_SRC` bug sites; `alert()` in browse — migrated (Tasks 11 + 13-D: ask page + voice hooks/components + workspace browse/processing; `voice-turn.ts` raw extraction eliminated in Task 13-D) |
| Uploads in workspace | `workspace/upload/page.tsx` | — migrated (Task 12: dropzone/file-input validation → `AppError` + `errors.upload.*` keys; server failures → `normalizeHttpError`/`normalizeException` + ErrorAlert with retry for network errors; raw upload body never rendered; registry gained the `errors.upload.*` code tier) |
| Raw-error sweep (Task 13) | 45 files (see §5 counts line + batches below) | — migrated in 5 batches: A1 `05e8be0` (lessons, unit-plans, quiz/take+history, recovery, intervention-analytics, knowledge-graph, diagrams), A2 `a498f09` (student, parent, classroom, assignments ×6, quizzes), B1 `075b7b7` (admin ×9 + layout), B2 `46d5c40` (agents, gamification, misconceptions, learning, ActivityFeed, IconPalette, TTSPlayButton), C `857df0a` (workspace page/browse/[id]/search, dashboard, digital-twin scan, assessment-studio, monitoring, oauth/callback), D `67d6587` (voice-turn.ts `RAW_SRC` → structured `AppError`; askQuestion + `recorder.onstop` network-throw escapes caught; quiz STT errors surfaced; TTSPlayButton `audio.onerror` surfaced; +7 voice-turn tests). Final sweep search: only `ExecutionPanel.tsx:120` (`JSON.stringify` of agent result output — data display, not error) and `normalizeError.ts:59` (internal network-sniffing — normalizer internals) remain; zero user-facing raw error rendering.

§5 classification table final state: every `RAW_UI` row migrated; `RAW_SRC` sites all eliminated (fetch.ts Task 05, voice-turn.ts Task 13-D, upload Task 12); `LOGGING` rows kept as-is (console-only); `DERIVED` kept: `digital-twin/page.tsx:273,345` (`{r.detail}` — server-provided recommendation fields, data not errors), `recovery/page.tsx:428,455` (`{n.message}`/`{rec.message}` — data-driven rows), `recovery` silent `catch {}` (history fetch, mark-all-read), `parent/page.tsx:110` weekly-summary `.catch(() => {})`, `quizzes/page.tsx` generation `task.error` reason text discarded (structured AppError shown instead), `GamificationProfile` 404 suppression via `category === 'not_found' || status === 404`. Pre-existing gaps logged (not part of sweep): `admin/content` + `admin/content/quiz/[id]` + `admin/content/lesson/[id]` PATCH `toggleStatus`/`updateStatus` unhandled rejections; `MisconceptionPanel` resolve-action errors invisible when profile loaded; `admin/layout.tsx` HTTP 403 responses resolve as `authorized` (fetchWithAuth semantics, unchanged); ask `playTTS` raw `throw new Error(`HTTP ${res.status}`)` — caught and silently swallowed by design. Open follow-ups under consideration: quiz page still swallows nothing (fixed Task 13-D), TTSPlayButton `audio.onerror` has no Error object source (still silent reset, flagged), `quiz/take/page.tsx` dead `genStatus` state. |

---

## 7. Test infrastructure

- **vitest**: `vitest.config.ts` — jsdom, `globals: true`, `@`→`src` alias, `vitest.setup.ts` (jest-dom), excludes `e2e/` and `playwright/`. Existing component tests e.g. `src/components/dashboard-v2/dashboards/__tests__/StudentDashboard.test.tsx`.
- **Playwright**: `playwright.config.ts` — testDir `./e2e`, `BASE_URL` env (default `http://localhost:3000`), single chromium project, CI retries ×2. Executed suite: `e2e/landing-page.spec.ts`, `e2e/login-error.spec.ts`, `e2e/session-expiry.spec.ts` (3 specs). Note: `playwright/recovery-visuals.spec.ts` lives outside the configured `testDir` and is **not currently executed**.
- **CI**: lint + typecheck, vitest (`-m "not slow"` runs apply to backend; dashboard job runs `npm run i18n:check` strict + vitest + lint + `tsc --noEmit` per `package.json` scripts).
- `dashboard/docs/error-handling.md` → new usage guide (Task 16).

---

## 8. Recommended migration sequence

1. **Foundation (Tasks 02–07):** normalize error type (single `AppErrorInfo` shape: `code`, `detail`, `context`, `status`; parse all three backend shapes + text), fix `RAW_SRC` bug sites in `fetch.ts` / `voice-turn.ts` / `upload/page.tsx`, shared error i18n namespace (en + am), shared `<ErrorBanner/>` component, central `parseApiError()` in `src/lib/errors.ts`.
2. **Login → OAuth (Task 08):** highest traffic; auth codes already enumerated; gate for `auth_refresh_expired` etc.
3. **Students list + detail (Task 09):** simple list/detail CRUD surfaces.
4. **v2 dashboards (Task 10):** five dashboards + `dashboard/page.tsx`.
5. **Ask / voice / workspace (Task 11):** stream errors + `useVoiceTurn` + browse `alert()`s; introduces rate-limit + retry UX.
6. **Uploads in workspace (Task 12):** upload inline raw-extraction replacement; 413/429 handling.
7. **Raw-error sweep (Task 13):** remaining `RAW_UI` setError sites → shared banner; drop `err: any`; `LOGGING` sites left as-is (safe).
8. **Verify:** `npx tsc --noEmit && npm run lint && npm run i18n:check --strict`; extend vitest mock coverage for `parseApiError`.

---

### Inventory commands (reproducibility)

```bash
grep -rln "fetchWithTimeout\|fetchWithAuth\|streamFetch" src --include="*.ts" --include="*.tsx"
grep -rln "from '@/lib/fetch'\|from '@/lib/fetchWithAuth'" src --include="*.tsx" --include="*.ts"
rg -n "JSON.stringify\(|\.message\b|\.detail\b|\[object Object\]" src -g '*.tsx' -g '*.ts' -g '!**/__tests__/**'
rg -n "catch \(" src -g '*.tsx' -g '*.ts' -l
rg -n "console\.(error|warn|log)" src -g '*.tsx' -g '*.ts'
```

---

## 9. Security audit (Task 15) — 2026-08-12

Review-only sweep of `dashboard/src` (excl. `__tests__`). Commands:

```bash
rg -n "console\.(log|debug|error|info)\(" src -g '*.ts' -g '*.tsx' -g '!**/__tests__/**'
rg -n "localStorage|sessionStorage|document\.cookie" src -g '*.ts' -g '*.tsx'
rg -n "Authorization|Bearer|access_token|refresh_token" src -g '*.tsx' -g '*.ts'
```

### Checklist

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | No token/secret/credential ever logged or rendered | **PASS** | 11 console sites reviewed (error.tsx:12, global-error.tsx:12, marketing/page.tsx:67, lessons/page.tsx:73, unit-plans/page.tsx:73, ModelSelector.tsx:36, knowledge-graph/page.tsx:133, recovery/page.tsx:236, assessment-studio/page.tsx:63, workspace/layout.tsx:34, quiz/take/[id] voice `onError`): all log fetch error objects (AppError/Error), never headers/bodies/tokens. JWT held in memory `_tokenCache` (`src/lib/auth.ts:3`) + backend HTTP-only `access_token` cookie; client `setToken` writes only `auth_ready`/`user_role` (non-sensitive) cookies (`auth.ts:25-32`). `document.cookie` only inside storage helpers `auth.ts` + `cookies.ts` (NEXT_LOCALE). All 10 `Authorization: Bearer` sites (fetch.ts:16,56, fetchWithAuth via credentials, voice-turn.ts:9,44, useConversationHistory.ts:91, TTSPlayButton.tsx:38, VoiceRecorderButton.tsx:79,115, QuizVoiceButton.tsx:78, upload/page.tsx:90, ask/page.tsx:200) are request headers — never logged. |
| 2 | `error.cause` never rendered (dev-logged only behind NODE_ENV check) | **PASS** | `src/app/error.tsx:11-13` and `global-error.tsx:11-13` gate `console.error` behind `process.env.NODE_ENV !== "production"` (build-inlined; production builds log nothing). Rendered output is catalog-only (`errors.error_title`/`boundary_message`). `cause` is set by `normalizeException` (normalizeError.ts:57,62) and kept in state on the ask page, but the only renderer, `useErrorMessage` (hooks/useErrorMessage.ts:46-54), never touches `cause`/`params`/`requestId` — `errorMessageKeys` returns only allowlisted catalog keys. |
| 3 | `normalizeHttpError` does not preserve `detail` bodies; `params` cannot carry backend strings into messages | **PASS** | normalizeError.ts:43-51 extracts only `error.code` (string), `error.context.retry_after` (number-gated, `:18`), and 422 `loc` field names mapped through the `VALIDATION_TYPE_MAP` allowlist (`:3-8`). `params` is hardcoded `{}` (`:19`) — never populated from the body. `retryAfter` has zero render sites in `src` (grep: none). `fieldErrors` is built but never consumed anywhere (grep: only normalizeError.ts + AppError.ts type). `errorMessageKeys` (useErrorMessage.ts:22-31) maps `code`/`status`/`category` exclusively through fixed allowlists (`KNOWN_CODES`, `UPLOAD_CODES`, `SHIPPED_HTTP`) to static catalog strings — no interpolation params are ever passed to `t()`. |
| 4 | Stream errors carry codes; ask page renders only catalog text | **PASS** | `streamFetch` (fetch.ts:118-122) checks `chunk.error` **before** status/delta handling and short-circuits (`onError(normalizeStreamError(code))` → `{category:"service", code, retryable:true}`) — error strings can never reach `setStatusText`/`setAnswer`. voice-turn.ts:81-84 drops the code entirely (`{category:"service", retryable:true}`). Ask page renders errors only via `ErrorAlert` → `useErrorMessage` (ask/page.tsx:355-362); `normalizeStreamError` codes (e.g. backend codes) fall outside `KNOWN_CODES` → category catalog text (`errors.categories.service`). `chunk.error` never reaches the DOM. |
| 5 | OAuth callback: no code/token logging; tokens in cookies only | **PASS** (2 MINOR findings) | callback/page.tsx never logs `ticket`/`access_token`; `setToken(data.access_token)` (`:40`) → memory + cookies only, no localStorage. **Finding 1 (LOW):** raw `oauth_error` query param is rendered verbatim via `t('oauth_error_unknown', { code: error })` (`:58-59`) — attacker-craftable URL string reaches the user (React-escaped → no XSS, but unvalidated). **Finding 2 (LOW):** `data.redirect` guarded only by `startsWith('/')` (`:41`) — would accept `//evil.com`; currently safe only because backend `_validate_redirect_target` (src/api/oauth.py:118-133) blocks `//` and `\`. Hardening: route through `safeNextPath`. |
| 6 | `safeNextPath` open-redirect surface | **PASS** | safeNextPath.ts:1-12 parses `next` via `new URL(next, origin)` and requires exact origin equality + rejects `/login*`. Empirically verified (node): `//evil.com`, `https://evil.com/x`, `https://app.ethiobio.ai@evil.com`, `%2F%2Fevil.com` (decoded → `//evil.com` authority → rejected), `%5C%5Cevil.com` (decoded `\\` → `//evil.com` → rejected), `\login` → rejected; `../evil` and `\evil.com` resolve to same-origin paths (browsers parse `\evil.com` as an authority per WHATWG for special schemes → rejected there too). Returned value always begins with `/` and `router.push` resolves it internally — cross-origin navigation unreachable. |
| 7 | `fetchWithAuth` redirectToLogin `next` encoding | **PASS** | fetchWithAuth.ts:29-34 — `current` (pathname+search) is `encodeURIComponent`'d once; login page re-reads via `URLSearchParams` + `safeNextPath` (login/page.tsx:53,90). Crafted page paths (incl. `%2F`-encoded query payloads, which URLSearchParams decodes to protocol-relative forms) are origin-checked post-decode by `safeNextPath` — no smuggling possible. |
| 8 | TTSPlayButton / voice surfaces leak no provider keys | **PASS** | TTSPlayButton.tsx:33-43, VoiceRecorderButton.tsx:79,115, QuizVoiceButton.tsx:78, voice-turn.ts:9,44 send `Bearer` from `getToken()` only; errors are `AppError` (client/service) with no raw payloads; no logging, no keys in any state/UI. |
| 9 | No credentials in `localStorage`/`sessionStorage` | **FAIL (minor)** | Migration to HTTP-only cookies (commit `ac2cadf`) removed token writes, but two stale reads survive: `workspace/browse/page.tsx:129` and `workspace/browse/[id]/page.tsx:114` — `localStorage.getItem('ethiobio_token')` (always `null` today, dead code, but a latent credential-storage surface if anything ever writes the key again). Non-sensitive writes only: `ethiobio_active_workspace_id` (workspace/layout.tsx:31,40). |

### Observations (out of error-handling scope, filed separately)

- **DOM XSS surface in content rendering:** `MarkdownRenderer.tsx:21,30` runs `marked.parse(content)` (marked ^18.0.3 — no sanitizer) into `dangerouslySetInnerHTML`. Backend/model-controlled content (ask answers, lesson plans) renders raw HTML — prompt-injection → stored/reflected XSS. Not an error path, but adjacent (ask page renders AI answers through it; error-channel text is catalog-only and does not flow here).

### Findings → issues

- `workspace/browse` dead `localStorage('ethiobio_token')` reads (latent token-exposure surface) — LOW.
- oauth/callback: raw `oauth_error` param rendered + weak `startsWith('/')` redirect guard (backend contract currently protects) — LOW.
- Unsanitized `dangerouslySetInnerHTML` markdown (XSS surface for model content) — MEDIUM, observation.

All other checks PASS; no genuine credential leak found. Findings feed the Task 16 documentation; recommended follow-ups: remove stale localStorage reads, harden oauth/callback, sanitize markdown.