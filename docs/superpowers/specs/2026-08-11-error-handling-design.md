# EthioSci Frontend Error Handling Design

Date: 2026-08-11
Scope: `dashboard/` (Next.js 14 App Router frontend) only — backend contracts untouched.

## 1. Mission

Replace the dashboard's scattered, raw error handling with a centralized, typed,
catalog-driven error architecture: every API failure becomes an `AppError` at the
API-client boundary, and every user-facing error string is a next-intl catalog key
(en + am parity enforced by CI).

The known trigger bug: login (and other) failures render `[object Object]` because
the client does `json.detail || json.error` against the backend's structured
envelope `{"error": {"code", "detail", "context"}}` — `json.detail` is undefined,
so the `error` **object** becomes the thrown Error message and is rendered raw.

## 2. Context (verified during recon)

- Framework: Next.js 14 App Router, React 18, TypeScript, Tailwind, `next-intl` 4
  (locales `en` + `am`; `npm run i18n:check --strict` CI-enforced, full parity rule:
  new EN keys must ship with AM translations in the same PR).
- No axios, no React Query/SWR. Three raw-fetch clients:
  - `src/lib/fetch.ts` `fetchWithTimeout()` — JSON API calls; throws `Error(text)`
    on non-ok (BUG site).
  - `src/lib/fetch.ts` `streamFetch()` — SSE streaming for AI; `onError(string)`.
  - `src/lib/fetchWithAuth.ts` `fetchWithAuth()` — 401 → refresh → retry, else
    `window.location.href = "/login"`; no guards (refresh storms, redirect loops).
- Auth: cookie sessions, Bearer token via `getToken()` (`src/lib/auth.ts`), login at
  `src/app/(marketing)/login`, plus oauth routes.
- Error UI: raw `<p className="text-red-400">{error}</p>` and similar in ~69 files.
  No toast library, no error components, no `error.tsx`, no ErrorBoundary.
- UI primitives: `src/components/ui/` (Badge, Button, Card, PageHeader); design tokens
  `src/styles/design-system.ts`.
- Tests: vitest + @testing-library (jsdom), Playwright (2 specs only).
- Backend error formats (read-only reference):
  1. `{"error": {"code", "detail", "context"}}` — `src/core/errors.py` `AppError`
     subclasses: `AuthError`→401 `auth_*`, `RateLimitError`→429 `rate_limit_exceeded`
     (+ `context.retry_after`), `NotFoundError`→404 `not_found_*`,
     `ConflictError`→409 `conflict_*`, sanitized 500 `internal_error`.
  2. `{"detail": "..."}` — FastAPI `HTTPException` (many routes; some leaky
     `detail=str(e)` 500s, e.g. `src/api/admin.py`).
  3. `{"detail": [{loc, msg, type}]}` — Pydantic validation (422).
  4. `{"error": "string"}` — occasional ad-hoc (e.g. bot-not-ready).
  5. Plain text bodies, malformed JSON, SSE `chunk.error`.

## 3. Decisions (agreed)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Priority | Architecture first, then incremental feature migration with verification gates |
| D2 | Scope | Frontend-only (`dashboard/`); backend unchanged |
| D3 | Messages | Catalog-driven: `AppError` carries `code`/`category`/`params`, never a rendered string; text via `useTranslations('errors')` |
| D4 | Login bug | Fixed through the new architecture (first feature migration) |
| D5 | Session expiry | Hard redirect to `/login?next=<path>`, made safe (single-flight refresh; skip for login/refresh/oauth URLs; no redirect when already on `/login`) |
| D6 | Testing | Vitest backbone (normalizer, components, feature hooks) + 3 critical E2E specs (login success, login failure asserts translated UI, session-expiry redirect) |
| D7 | Migration breadth | Foundation + login/oauth → students → dashboards → AI (ask/workspace/voice) → uploads; raw-rendering sweep for the rest; follow-up tickets for stragglers |
| D8 | Layer shape | "Plain" — errors stay local to calling component; no global error provider/bus; Next-native `error.tsx`/`global-error.tsx` boundaries |

## 4. Architecture

### 4.1 Module layout (new files)

```
src/lib/errors/
  AppError.ts            type + isAppError() + fromHttpStatus() factory
  normalizeError.ts      normalizeError(input: unknown): AppError  (single gate)
  index.ts
src/hooks/useErrorMessage.ts          AppError → catalog string (ICU params)
src/components/ui/errors/
  ErrorAlert.tsx         form/action failures (title, message, optional retry)
  ErrorState.tsx         page/data-load failures (message + Try Again)
  FieldError.tsx         per-field, aria-describedby association
  ErrorBanner.tsx        application-level (e.g. session expired)
src/app/error.tsx        segment render-error fallback ("Something went wrong" + Refresh Page)
src/app/global-error.tsx root-layout fallback
```

### 4.2 `AppError` (src/lib/errors/AppError.ts)

```ts
type ErrorCategory =
  | "authentication" | "authorization" | "validation" | "conflict" | "not_found"
  | "rate_limit" | "network" | "server" | "service" | "client" | "unknown";

interface AppError {
  category: ErrorCategory;
  code?: string;              // backend code, e.g. "auth_invalid_credentials"
  status?: number;            // HTTP status where available
  retryable: boolean;         // per classification table
  retryAfter?: number;        // from context.retry_after (429)
  fieldErrors?: Record<string, string[]>;  // validation mapping (field → keys)
  params?: Record<string, unknown>;        // safe context params for ICU messages
  requestId?: string;         // where available
  cause?: unknown;            // never rendered
}
```

No `message` field — user text is always resolved from catalogs.

### 4.3 normalizeError (src/lib/errors/normalizeError.ts)

Inputs → `AppError`, in priority order (first match wins):

| Input | Category | Notes |
|-------|----------|-------|
| AbortError / timeout | `network` | retryable |
| `TypeError: fetch failed` / network | `network` | retryable |
| `{"error": {"code", "detail", "context"}}` | by code/status | code preserved; `context` → `params` (safe subset); `retry_after` → `retryAfter` |
| `{"detail": [{loc, msg, type}]}` (422) | `validation` | `loc` body path → `fieldErrors` keys; `type` → catalog key via `validation.<type>` mapping |
| `{"detail": "string"}` | by status | message never surfaced raw |
| `{"error": "string"}` | by status | |
| Plain text / malformed JSON | by status | |
| Any non-Error throw | `unknown` / `client` | conservative |

Status classification (retryability; mutations marked non-idempotent require feature-level confirmation before auto-retry):

| Status | Category | Retryable |
|--------|----------|-----------|
| 401 | `authentication` | no |
| 403 | `authorization` | no |
| 404 | `not_found` | no |
| 409 | `conflict` | no |
| 422 | `validation` | no |
| 429 | `rate_limit` | yes, with `retryAfter` |
| 500/502/503/504 | `server` | read-only: yes; mutations: no auto-retry |
| unknown pre-1xx/3xx oddities | `unknown` | conservative no |

Rule: `normalizeError` is pure, locale-free, and never logs detail bodies.

### 4.4 Client integration

- `fetchWithTimeout`: non-ok → `throw normalizeError(await res.text())` (response
  body variants all handled). No behavior change for ok responses.
- `streamFetch`: `onError?: (error: AppError) => void` (signature change; migrate its
  consumers: ask page, conversation sidebar, voice surfaces).
- `fetchWithAuth`:
  - Single-flight refresh: one module-level `refreshPromise` shared by concurrent 401s.
  - Skip refresh when the failing request URL is `/auth/refresh`, login, or oauth callbacks.
  - Refresh failure → `typeof window` guard + redirect to `/login?next=<current path>`;
    no redirect when already on `/login`; only ONE redirect (flag to prevent loops).

### 4.5 Message registry (catalog-driven)

New `errors` namespace in `messages/en.json` + `messages/am.json` (parity rule applies):

```
errors.codes.<backend_code>     — known codes, e.g. auth_invalid_credentials
errors.http.<status>            — fallback per status, e.g. http.500
errors.categories.<category>    — fallback per category
errors.validation.<type>        — Pydantic type → message (params: field, input)
errors.generic                  — final fallback
```

Resolution order in `useErrorMessage(error)`:
`codes.<code>` → `http.<status>` → `categories.<category>` → `generic`.
`fieldErrors` mapped per-field via `validation.<type>` with safe params (field label
from `loc`, never raw input values for secrets).

- `useErrorMessage` is a hook (needs `useTranslations`); server/utility call sites
  that must resolve strings get a small `errorMessageKeys(error)` helper returning
  the key + params instead (no translation in non-React code).
- New keys ship with en + am in the same PR; `i18n:check --strict` stays green.

### 4.6 Shared error components

All in `src/components/ui/errors/`, styled with `src/styles/design-system.ts` tokens
and existing Tailwind conventions; catalog-driven strings:

- `ErrorAlert` — `{ title?, message, retry? }`; `role="alert"`.
- `ErrorState` — page/data-load failures; `{ title?, message, onRetry, retrying? }`;
  `Try Again` button hidden when `retryable=false`.
- `FieldError` — per-field; `{ id, messages }`; input gets `aria-describedby={id}`;
  `aria-live="polite"`.
- `ErrorBanner` — application-level; used for session-expiry messaging where a page
  chooses inline presentation before redirect.
- Existing `Button` reused for retry actions.

### 4.7 Boundaries

- `src/app/error.tsx` — client component fallback for segment render errors
  ("Something went wrong", Refresh Page). Never shows `error.message` in prod.
- `src/app/global-error.tsx` — root layout fallback (same pattern; must render its
  own `<html>`).
- Review `not-found` behavior; leave as-is unless raw-error rendering found.
- Logging: structured, safe — `code`, `status`, `category`, `requestId` only;
  never `detail` bodies, tokens, headers, or stack traces to user-visible paths.

### 4.8 Feature migration order (each behind verification gates)

1. Auth: login, oauth callback, 401/session handling, logout.
2. Students: list/create/read/update/delete/search + details.
3. Dashboards: v2 role dashboards (top-level load errors, widget failures retain
   independent loading where architecture permits; refresh errors must not blank
   already-loaded data).
4. AI: ask page, conversation sidebar, workspace (browse/processing), voice —
   `AppError.category === "service"` message family; provider details never surfaced.
5. Uploads: workspace processing/browse.
6. Raw-rendering sweep: search `JSON.stringify(error|response)`, `error.detail`,
   `error.response`, raw `{error}` strings; classify; convert user-facing ones to
   the layer; leave developer-logging/telemetry occurrences; follow-up tickets for
   stragglers.

### 4.9 Loading/error/retry state contract

Every backend-dependent surface has one of:
`idle → loading → success` or `loading → error → retry`.
No infinite loading; no dead-end error without recovery where retry possible;
preserve loaded data on refresh failure instead of replacing with an error screen.

## 5. Security requirements

Never expose to users or logs: passwords, tokens, JWTs, cookies, API/provider keys,
connection strings, SQL, stack traces, filesystem paths, internal IPs, service names,
infrastructure detail, or raw `detail` bodies. `normalizeError` and components never
render `cause` or `params` content verbatim (params are whitelisted per message key
at catalog site, e.g. `{field}` only).

## 6. Testing strategy

- **Unit (vitest):** `normalizeError` for all formats × statuses (401 known/unknown
  code, 403, 404, 409, 422 envelope + Pydantic detail, 429 with/without retry_after,
  500/502/503/504, network, timeout/abort, malformed JSON, plain text, unknown),
  asserting category/message-key/status/code/fieldErrors/retryable/retryAfter;
  `useErrorMessage` resolution order; `errorMessageKeys`.
- **Component (vitest):** ErrorAlert (title/message/retry/a11y/no raw JSON),
  ErrorState (transition/retry/retry hidden), FieldError (association, multiple
  messages, a11y), `error.tsx` fallback.
- **Feature (vitest):** login failure → translated ErrorAlert (no `[object Object]`);
  `fetchWithAuth` single-flight + no-redirect-on-login + `?next=` preservation.
- **E2E (Playwright, 3 specs):** login success; login failure shows translated error;
  session-expiry redirects to `/login?next=...` with a single redirect.
- **Gates after every task:** `npx tsc --noEmit`, `npm run lint`,
  `npm run test`, `npm run i18n:check --strict`, `npm run build`, then Playwright
  after feature migrations. No check reported PASS unless executed.

## 7. Definition of Done

- [ ] `docs/error-handling-audit.md` written (read-only recon artifact)
- [ ] `AppError` + `normalizeError` exist with full unit coverage
- [ ] `errors.*` catalog keys exist in en + am; `i18n:check --strict` green
- [ ] All three fetch clients normalize; consumers compile; no raw strings thrown
- [ ] Shared error components exist, tested, a11y-correct
- [ ] `error.tsx` + `global-error.tsx` boundaries in place
- [ ] Auth (login/oauth/session-expiry) migrated; single-flight + safe redirect proven
- [ ] Students, dashboards, AI, uploads migrated per §4.8
- [ ] Raw-rendering sweep done; user-facing raw rendering eliminated; remaining
      occurrences classified (logging/telemetry only); tickets filed for stragglers
- [ ] 3 critical E2E specs pass
- [ ] `docs/error-handling.md` written (architecture, codes, usage rules)
- [ ] Security audit passed (no secret/infra leakage in UI or logs)
- [ ] Typecheck, lint, unit tests, i18n check, build, E2E all pass
- [ ] No unrelated regressions; diff reviewed task-by-task

## 8. Task sequence (execution protocol)

01 Audit (read-only, produces `docs/error-handling-audit.md`) →
02 `AppError` model + unit tests →
03 `normalizeError` + unit tests (all formats) →
04 Catalog keys (en+am) + `useErrorMessage`/`errorMessageKeys` + tests →
05 Client integration (`fetchWithTimeout`, `streamFetch`, `fetchWithAuth`
single-flight/safe-redirect) + verify all consumers →
06 Shared error components + tests →
07 Boundaries (`error.tsx`, `global-error.tsx`, not-found review) →
08 Auth feature migration →
09 Students migration →
10 Dashboards migration →
11 AI migration →
12 Uploads migration →
13 Raw-rendering sweep + classification →
14 E2E (3 specs) →
15 Security audit →
16 `docs/error-handling.md` →
17 Final verification (full gate suite) + full diff review.

After every task: run gates, inspect diff, fix regressions, report
(Task/Changes/Files/Tests/Verification/Issues/Next). Never report PASS unless run.