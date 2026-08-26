# Error Handling — Usage Guide

Shipped error layer for the EthioSci dashboard (Next.js 14 App Router). Read this file
before touching any `catch`, `setError`, or `_fetch*` call site. Written against the
shipped code (Tasks 02–15); the design spec lives at
`../docs/superpowers/specs/2026-08-11-error-handling-design.md` and the audit at
`../docs/error-handling-audit.md`.

## 1. The invariant

Every API failure becomes an `AppError` at the client boundary, and every user-facing
error string is a next-intl catalog key. Errors never cross the boundary as raw text,
and user text never comes from error objects.

```
API boundary                                   normalize                    UI
fetchWithTimeout  ── throw ─────────────┐
fetchWithAuthJson ── throw ─────────────┼──▶ normalizeHttpError  ┐
voiceTurnFetch    ── onError(AppError) ─┤                        ├──▶ AppError ──▶ useErrorMessage ──▶ user
streamFetch       ── onError(AppError) ─┼──▶ normalizeStreamError┤                   ▲
catch (err)       ── throw ─────────────┴──▶ normalizeException ─┘                   │
                                                          ErrorAlert / ErrorState / ErrorBanner / FieldError
```

- `fetchWithTimeout` (`src/lib/fetch.ts`) — JSON API calls; non-ok throws
  `normalizeHttpError(res.status, text)`.
- `fetchWithAuth` / `fetchWithAuthJson` (`src/lib/fetchWithAuth.ts`) — cookie-session
  calls with 401 refresh; `fetchWithAuthJson` throws `normalizeHttpError` on non-ok.
- `streamFetch` (`src/lib/fetch.ts`) — SSE AI streams; failures arrive via
  `callbacks.onError(err: AppError)`.
- `voiceTurnFetch` (`src/lib/voice-turn.ts`) — voice POST + SSE; failures via
  `callbacks.onError`, network throws via `normalizeException` (aborts are silent).
- Everything else (component `catch`) must run `normalizeException(err)` before
  storing in state — never store `err.message`, never render it.

## 2. `AppError` shape and the 11 categories

Type in `src/lib/errors/AppError.ts`:

```ts
interface AppError {
  category: ErrorCategory;              // one of the 11 below (always set)
  code?: string;                        // backend code, e.g. "auth_invalid_credentials"
  status?: number;                      // HTTP status where available
  retryable: boolean;                   // per classification table
  retryAfter?: number;                  // context.retry_after (429), number-gated
  fieldErrors?: Record<string, string[]>; // validation: field → catalog keys
  params?: Record<string, unknown>;     // safe ICU params — always {} from the normalizer
  requestId?: string;                   // declared, never populated by shipped normalizers
  cause?: unknown;                      // NEVER rendered — dev/debug only
}
```

There is **no `message` field**. User text is always resolved from catalogs.

Categories (`ERROR_CATEGORIES`): `authentication`, `authorization`, `validation`,
`conflict`, `not_found`, `rate_limit`, `network`, `server`, `service`, `client`,
`unknown`.

Field semantics (verified against shipped code):

| Field | Semantics |
|-------|-----------|
| `code` | Backend code, preserved only when the body is `{"error": {code: string, ...}}`. Looked up against `KNOWN_CODES` then `UPLOAD_CODES` (§4). Unlisted codes fall through to status/category text. |
| `status` | HTTP status. Gated against the `SHIPPED_HTTP` whitelist for the `errors.http.*` tier (§4). |
| `retryable` | Drives retry UI: `ErrorState` hides its button when `false`; `ErrorAlert` callers gate `onRetry` on it. |
| `retryAfter` | From `error.context.retry_after` (number only). No render site in the app — informational. |
| `fieldErrors` | Field → catalog-key arrays from 422 Pydantic `detail[]` (§6). Built by the normalizer; consumed only via `FieldError`. |
| `params` | Always `{}` from `normalizeHttpError` — backend strings can never flow into messages. |
| `cause` | Original error, set by `normalizeException`. Never rendered, never logged in prod (§10). |

## 3. Classification table

Source of truth: `fromHttpStatus` (`AppError.ts`) + `normalizeError.ts`.

| Input | Category | Retryable | Notes |
|-------|----------|-----------|-------|
| HTTP 401 | `authentication` | no | refresh flow in `fetchWithAuth` (§7) |
| HTTP 403 | `authorization` | no | |
| HTTP 404 | `not_found` | no | components may suppress via `category === "not_found"` (GamificationProfile) |
| HTTP 409 | `conflict` | no | |
| HTTP 422 | `validation` | no | Pydantic `detail[]` → `fieldErrors` (§6) |
| HTTP 429 | `rate_limit` | yes | `retryAfter` from `context.retry_after` |
| HTTP 500/502/503/504/599 | `server` | yes | |
| any other 4xx | `client` | no | |
| other statuses | `unknown` | no | |
| `AbortError` / `TimeoutError` (by `name`) | `network` | yes | `normalizeException` |
| `TypeError` matching `/fetch\|network\|failed/i` | `network` | yes | `normalizeException` |
| anything else thrown | `unknown` | no | `cause` set to the original error |
| SSE `chunk.error` (streamFetch) | `service` | yes | `normalizeStreamError(code)` keeps the code |
| SSE `chunk.error` (voice-turn) | `service` | yes | code dropped — category text only |
| missing response body in a stream | `service` | yes | `code: "no_response_body"` |
| unparseable JSON body from `fetchWithAuthJson` | `service` | yes | `code: "malformed_response"` |

`{"error": {code, detail, context}}` bodies: only `code` (string) and
`context.retry_after` (number) survive; `detail` and `context` are never preserved.
`{"detail": "string"}`, `{"error": "string"}`, plain text, and malformed JSON all
classify by status only. Other `error.*` / `detail.*` fields never reach the UI.

## 4. Message resolution order

`src/hooks/useErrorMessage.ts` — `errorMessageKeys` returns a catalog key + params;
`useErrorMessage(error)` translates it (or `""` for `null`/`undefined` — nullish
resolves to nothing, so conditional rendering `{error && <ErrorAlert .../>}` handles
the empty case). The actual chain:

```
error.code ∈ KNOWN_CODES   → errors.codes.<code>        (7 codes: auth_invalid_credentials,
                                                         auth_invalid_otp, auth_otp_expired,
                                                         auth_token_expired, auth_refresh_expired,
                                                         auth_user_inactive, rate_limit_exceeded)
error.code ∈ UPLOAD_CODES  → errors.upload.<code>       (unsupported_type, too_large — Task 12 tier)
error.status ∈ SHIPPED_HTTP → errors.http.<status>      (whitelist: 400, 401, 403, 404, 409, 422, 429, 500)
category === "unknown"     → errors.generic
otherwise                  → errors.categories.<category>
```

Notes on the shipped chain (differs from the written design):

- The whitelist `SHIPPED_HTTP` covers only 8 statuses; 502/503/504 (server) fall
  through to the `server` category key.
- `UPLOAD_CODES` sits between code and HTTP tiers — upload codes are client-side
  (`retryable: false`) and must not be masked by the HTTP tier.
- `errorMessageKeys` never passes ICU params — `params` is always `undefined` in
  practice; only `FieldError` interpolates (`{field}`).
- The hook is client-only (uses `useTranslations`). Non-React code should call
  `errorMessageKeys` and translate at the nearest component.

## 5. Adding a new error code

1. Backend: emit the code in the `{"error": {code, ...}}` envelope (e.g. a new
   `AuthError`-style code in `src/core/errors.py`).
2. Frontend catalog: add `errors.codes.<code>` to **both** `messages/en.json` and
   `messages/am.json` in the same PR (Amharic translation included).
3. If it needs a specific message (not category text), add the code to `KNOWN_CODES`
   in `useErrorMessage.ts` — plus a unit test in
   `src/hooks/__tests__/useErrorMessage.test.tsx`.
4. Gate: `node scripts/check-i18n.mjs --strict` (package script `npm run i18n:check`).
   Strict mode fails on en→am parity gaps, duplicate keys, code-referenced keys
   missing from `en.json`, and unknown non-en keys. New EN keys without AM fail CI
   (`dashboard-i18n` job).
5. Codes that are transient/rare can ship catalog-only (category text is the fallback)
   — only codes users will actually see merit a custom key.

## 6. Validation mapping — `FieldError`

422 details (`{"detail": [{loc, msg, type}]}`) are flattened by `normalizeHttpError`:

- Field key: `loc` items joined with `.`, after dropping `body`/`query`/`path`
  segments (e.g. `loc: ["body", "email"]` → `email`).
- Message key: `type` mapped through `VALIDATION_TYPE_MAP`
  (`missing` → `errors.validation.missing`, `string_type`, `integer_type`,
  `value_error`; anything else → `errors.validation.generic`). Raw `msg` strings from
  the backend are never kept.

`FieldError` (`src/components/ui/errors/FieldError.tsx`):

```tsx
export function FieldError({ id, field, messages, className = "" }: FieldErrorProps) {
  if (!messages.length) return null;
  return (
    <span id={id} aria-live="polite" className={`text-sm text-red-400 block mt-1 ${className}`}>
      {messages.map((key, i) => (
        <span key={`${key}-${i}`} className="block">{t(key, { field })}</span>
      ))}
    </span>
  );
}
```

- Render one `FieldError` per field below the input, pass `field` = the dotted loc
  path (it fills `{field}` in the message).
- Messages are catalog keys indexed with `${key}-${i}` (stable keys, no raw text).
- `aria-live="polite"` announces additions; associate the input via
  `aria-describedby={id}`.

## 7. 401 / session-handling rules

`src/lib/fetchWithAuth.ts` is the only place that recovers 401s (Bearer clients like
`fetchWithTimeout` do **not** refresh):

1. First 401 on any `fetchWithAuth` call → `singleFlightRefresh()` — one module-level
   promise shared by all concurrent 401s (no refresh storms).
2. **No-redirect paths** (`NO_REDIRECT_PREFIXES`): `/login`, `/auth/refresh`,
   `/auth/token`, `/auth/request-otp`, `/auth/verify-otp`, `/auth/register`,
   `/auth/logout`, `/auth/oauth` — these return the 401 Response without refreshing.
3. Refresh OK → the original request is retried exactly once; a second 401 falls
   through to redirect.
4. Refresh failed → `redirectToLogin()`: guarded by `typeof window`, skips when the
   current path already starts with `/login`, then
   `window.location.href = '/login?next=' + encodeURIComponent(current)`.

Login page consumption: `safeNextPath(window.location.search, window.location.origin)`
re-validates `next` before `router.push` (see `login/page.tsx:53,90`).

`safeNextPath` (`src/lib/safeNextPath.ts`):

- Rejects any target whose origin differs from the app origin (kills `//evil.com`,
  `https://evil.com/x`, userinfo trickery, encoded protocol-relative forms).
- Rejects targets whose pathname starts with `/login`.
- Returns a same-origin `pathname + search + hash` (always begins with `/`), or
  `null`. **Use it for any future redirect that reads a URL parameter.**

Auth quirk: `isAuthenticated()` (`src/lib/auth.ts`) checks the `auth_ready=1` cookie,
which `setToken()` writes on login. It is a client-side flag — the edge middleware
gates SSR on the HTTP-only `access_token` cookie instead. Do not conflate the two.

## 8. Component recipes

All four components export from `@/components/ui/errors` (`src/components/ui/errors/`).

| Component | When | Props | Retry behavior |
|-----------|------|-------|----------------|
| `ErrorState` | Full-page / block data-load failure | `error`, `title?`, `onRetry?`, `retrying?` | Button rendered **only when `error.retryable`** |
| `ErrorBanner` | Widget-level inline failure (page shell stays loaded), session-expiry messaging | `error` (required, non-null), `onAction?`, `actionLabel?` | Button rendered whenever `onAction` is passed |
| `ErrorAlert` | Form / action / upload failures inside a layout | `error`, `title?`, `onRetry?`, `retrying?` | Button rendered whenever `onRetry` is passed — **caller must gate on `error.retryable`** |
| `FieldError` | Per-field validation | `id`, `field`, `messages` | — |

All render `role="alert"` and resolve text via `useErrorMessage` — no component ever
renders raw error content.

Recipes from shipped code:

```tsx
// Full-page load failure (StudentDashboard, TeacherDashboard, AdminDashboard)
if (error) return <ErrorState error={error} title={t("load_error")} onRetry={() => void fetchData()} />;

// Widget failure: keep the shell, surface an inline banner (StudentDashboard quiz widget:
// ErrorBanner error={widgetError} actionLabel={tc("retry")} onAction={() => void loadAttempts()})

// Form failure (login page): {error && <ErrorAlert error={error} title={t("error")} />}

// Action with retryable gating (upload page):
{error && (
  <ErrorAlert
    error={error}
    onRetry={error.retryable ? () => void handleSubmit() : undefined}
    retrying={uploading}
  />
)}

// Catch convention everywhere:
} catch (err) {
  setError(normalizeException(err));
}
```

DashboardLayout widget patterns (two-tier, from `dashboard-v2/dashboards/`):

- **Top-level fetch** → `ErrorState` (full-page, retry refetches the primary data).
- **Per-widget / per-child fetch** → `ErrorBanner` in place of that widget;
  already-loaded data and the page shell stay visible. ParentDashboard and
  SchoolDashboard follow this for per-child/per-school data; the shell must never
  blank when a widget refresh fails (covered by
  `StudentDashboard.test.tsx` / `ParentDashboard.test.tsx`).

Boundaries: `src/app/error.tsx` (segment) and `src/app/global-error.tsx` (root, with
its own `<html>`) show catalog text (`errors.error_title`, `errors.boundary_message`)
plus a Refresh Page action. They never show `error.message`; the `error` object is
dev-only logged behind `process.env.NODE_ENV !== "production"`.

## 9. Stream errors

`streamFetch` (`src/lib/fetch.ts`):

- Non-ok response → `onError(normalizeHttpError(status, text))`.
- Missing body reader → `onError({category: "service", code: "no_response_body", retryable: true})`.
- SSE chunks: `chunk.error` is checked **before** status/delta/done handling and
  short-circuits the stream via `onError(normalizeStreamError(chunk.error))` →
  `{category: "service", code, retryable: true}`. Error strings can never reach
  `onStatus`/`onToken` handlers.
- Malformed SSE lines are skipped silently.

`voiceTurnFetch` (`src/lib/voice-turn.ts`) mirrors this, except `chunk.error` drops
the code (`{category: "service", retryable: true}`) and user aborts
(`AbortError`) are silent — no error callback for cancelled voice turns.

Consumption contract (ask page `src/app/(dashboard)/ask/page.tsx`):

- Render stream errors via `ErrorAlert` only — catalog text. `chunk.error` and any
  deltas/chunk content never reach the DOM.
- `normalizeStreamError` codes are typically not in `KNOWN_CODES`, so users see the
  `service` category message ("This service is temporarily unavailable…").
- Retry is offered when `error.retryable` (all stream errors are).

## 10. Security rules

From the Task 15 audit (commit `96a4481`, `docs/error-handling-audit.md` §9):

- **Never log or display:** `detail` bodies, `error.context`, tokens/JWTs,
  `Authorization` headers, cookies, API/provider keys, `cause`, request bodies.
  Structured logging may include `code`/`status`/`category` only.
- `error.tsx` / `global-error.tsx` console calls are dev-only
  (`process.env.NODE_ENV !== "production"`); production builds log nothing.
- `normalizeHttpError` strips detail bodies at the boundary: only `code` (string) and
  `context.retry_after` (number) survive; `params` is hardcoded `{}` — backend strings
  cannot be smuggled into messages.
- `cause` is set by `normalizeException` and kept in state, but nothing renders it.
- Never store/read credentials in `localStorage`/`sessionStorage` — the JWT lives in
  memory (`_tokenCache`) and the HTTP-only `access_token` cookie.

Known follow-ups (tracked, do not reintroduce):

- [#103](https://github.com/EthioBio/ethiobio/issues/103) — stale
  `localStorage('ethiobio_token')` reads in workspace browse pages (dead, latent).
- [#104](https://github.com/EthioBio/ethiobio/issues/104) — oauth callback renders
  raw `oauth_error` query param; redirect guard should route through `safeNextPath`.
- [#105](https://github.com/EthioBio/ethiobio/issues/105) — unsanitized
  `dangerouslySetInnerHTML` markdown (XSS surface for model content).

## 11. The "Never" rules (from the design spec §Mission)

```
AppError ──never──▶ user
  ├── err.message          × (there is no message field — catalog keys only)
  ├── [object Object]      × (the original bug: json.error object rendered raw)
  ├── raw backend text     × (detail/error bodies never preserved or rendered)
  └── provider names       × (service category text, never provider specifics)
```

A failure is user-visible only as catalog text: `errors.codes.*` → `errors.http.*` →
`errors.categories.*` → `errors.generic`.

## 12. Regression tests

- Unit/component: `src/lib/__tests__/AppError.test.ts`,
  `src/lib/__tests__/normalizeError.test.ts`,
  `src/hooks/__tests__/useErrorMessage.test.tsx`,
  `src/components/ui/errors/__tests__/*`.
- E2E (Task 14, include in any error-layer change):
  - `e2e/login-error.spec.ts` — invalid credentials show a **translated** error, not
    raw backend text; successful login navigates.
  - `e2e/session-expiry.spec.ts` — expired session redirects to `/login` with `next`;
    no redirect loop when already on `/login`.
- Gates: `npx tsc --noEmit`, `npm run lint`, `npm run test`,
  `node scripts/check-i18n.mjs --strict`.