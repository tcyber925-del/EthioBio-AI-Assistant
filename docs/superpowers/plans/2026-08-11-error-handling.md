# EthioBio Frontend Error Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize dashboard error handling into a typed `AppError` layer at the API-client boundary, with catalog-driven (en+am) user messages and shared error UX — fixing `[object Object]` login failures and raw backend text rendering.

**Architecture:** Three fetch clients (`fetchWithTimeout`, `streamFetch`, `fetchWithAuth`) become the only normalization gate, producing `AppError` objects that components resolve to next-intl catalog strings via `useErrorMessage`. Next-native `error.tsx`/`global-error.tsx` provide render boundaries. No global error provider; errors stay local to the calling component.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind, next-intl 4 (en+am parity CI-enforced via `scripts/check-i18n.mjs --strict`), vitest + @testing-library, Playwright. Repo: `dashboard/` (backend untouched).

**Design doc:** `docs/superpowers/specs/2026-08-11-error-handling-design.md`

**Amendments (execution):**
- Task 03: plan test listing grew 17 → 19 via two quality-review edge tests (`retry_after: 0` preserved; numeric `loc` segments stringified). Reference `normalizeException` hardened — name-based shape check instead of `instanceof Error` (legacy WebViews' `DOMException` doesn't inherit `Error`; abort must stay retryable). `SAFE_CONTEXT_KEYS` constant removed as dead code (`params` always `{}` per design §4.3). Implemented in `396b3ff`, hardened in `90d2e38`; full suite 68 passing at completion.

---

## File Structure

**New files:**
- `src/lib/errors/AppError.ts` — `ErrorCategory`, `AppError`, `isAppError`, `fromHttpStatus`
- `src/lib/errors/normalizeError.ts` — `normalizeHttpError`, `normalizeException`, `normalizeStreamError`
- `src/lib/errors/index.ts` — re-exports
- `src/hooks/useErrorMessage.ts` — `useErrorMessage`, `errorMessageKeys`
- `src/components/ui/errors/ErrorAlert.tsx`
- `src/components/ui/errors/ErrorState.tsx`
- `src/components/ui/errors/FieldError.tsx`
- `src/components/ui/errors/ErrorBanner.tsx`
- `src/components/ui/errors/index.ts`
- `src/app/error.tsx` — segment render-error fallback
- `src/app/global-error.tsx` — root-layout fallback
- `src/lib/__tests__/AppError.test.ts`
- `src/lib/__tests__/normalizeError.test.ts`
- `src/hooks/__tests__/useErrorMessage.test.ts(x)`
- `src/components/ui/errors/__tests__/ErrorAlert.test.tsx`
- `src/components/ui/errors/__tests__/ErrorState.test.tsx`
- `src/components/ui/errors/__tests__/FieldError.test.tsx`
- `src/lib/__tests__/fetchWithAuth.test.ts`
- `src/app/(marketing)/login/__tests__/LoginPage.test.tsx`
- `e2e/login-error.spec.ts`
- `e2e/session-expiry.spec.ts`

**Modified files:**
- `src/lib/fetch.ts` — normalize at boundary (Task 05)
- `src/lib/fetchWithAuth.ts` — single-flight refresh, safe redirect, `fetchWithAuthJson` (Task 05)
- `src/app/(marketing)/login/page.tsx` — ErrorAlert, no raw strings (Task 08)
- `src/app/(dashboard)/students/page.tsx` + `students/[id]/page.tsx` — ErrorState (Task 09)
- `src/app/(dashboard)/ask/page.tsx` — AppError onError, ErrorAlert (Tasks 05/11)
- `src/components/dashboard-v2/dashboards/*.tsx` — ErrorState/ErrorAlert (Task 10)
- `src/hooks/useVoiceTurn.ts`, `src/components/VoiceRecorderButton.tsx`, workspace pages — AI/upload migration (Tasks 11/12)
- `messages/en.json`, `messages/am.json` — `errors` namespace (Task 04)
- `dashboard/docs/error-handling.md` — usage guide (Task 16)

**Fixed type vocabulary (used in every task):**

```ts
export type ErrorCategory =
  | "authentication" | "authorization" | "validation" | "conflict" | "not_found"
  | "rate_limit" | "network" | "server" | "service" | "client" | "unknown";

export interface AppError {
  category: ErrorCategory;
  code?: string;                    // backend code, e.g. "auth_invalid_credentials"
  status?: number;                  // HTTP status where available
  retryable: boolean;
  retryAfter?: number;              // from context.retry_after (429)
  fieldErrors?: Record<string, string[]>; // field loc path → catalog key list
  params?: Record<string, unknown>; // safe ICU params ({field, seconds})
  requestId?: string;               // where available (reserved)
  cause?: unknown;                  // never rendered
}
```

Catalog keys are **full dotted keys** resolved through root `useTranslations()`:
`errors.codes.<code>` → `errors.http.<status>` → `errors.categories.<category>` → `errors.generic`.

Verification gates for every task (run the ones applicable; never claim PASS without running):
`npx tsc --noEmit` · `npm run lint` · `npm run test` · `npm run i18n:check --strict` · `npm run build`

---

## Task 01: Audit (read-only)

**Files:**
- Create: `docs/error-handling-audit.md`

- [ ] **Step 1: Inventory API clients and entry points**

Run, from `dashboard/`:

```bash
grep -rln "fetchWithTimeout\|fetchWithAuth\|streamFetch" src --include="*.ts" --include="*.tsx"
grep -rln "from '@/lib/fetch'\|from '@/lib/fetchWithAuth'" src --include="*.tsx" --include="*.ts"
```

Record every consumer file. Note `fetchWithTimeout` is used for both GET and POST;

- [ ] **Step 2: Inventory raw error rendering**

```bash
rg -n "JSON\.stringify\((error|response|err|res)\)|\.message\b|\.detail\b|\[object Object\]" src --include="*.tsx" --include="*.ts" -g '!**/__tests__/**'
rg -n "catch \(" src --include="*.tsx" --include="*.ts" -l
```

Classify each hit as: `RAW_UI` (rendered user-facing — must migrate), `LOGGING` (console — safe), `DERIVED` (used for branching, e.g. `isServerError`).

- [ ] **Step 3: Record backend error contract summary**

From the source (read-only): `src/core/errors.py` envelope `{"error": {code, detail, context}}`; FastAPI `detail: string`; Pydantic `detail: [{loc,msg,type}]`; sanitized 500 `internal_error` handler at `src/main.py:372-377`; ad-hoc `{"error": "string"}` at `src/main.py:518,524`. Known backend codes (already enumerated):

```text
auth_invalid_credentials, auth_invalid_token, auth_invalid_refresh, auth_missing_token,
auth_missing_refresh, auth_refresh_expired, auth_refresh_reused, auth_token_expired,
auth_otp_expired, auth_otp_invalid, auth_user_inactive, auth_login_required,
auth_invalid_payload, auth_internal_api_key_not_configured, auth_invalid_internal_api_key,
conflict_email, conflict_oauth_identity_conflict, not_found_user, not_found_telegram_id,
not_found_provider, rate_limit_exceeded, internal_error
```

- [ ] **Step 4: Write the audit document**

`docs/error-handling-audit.md` with sections: API clients & entry points; auth mechanism (middleware cookie `access_token`, `Bearer` token via `getToken()`, `fetchWithAuth` refresh); backend error formats; existing error UI inventory (no shared components exist — confirm); raw-rendering locations table (file, line, class: RAW_UI/LOGGING/DERIVED); feature surfaces to migrate (login/oauth, students, dashboards, ask/voice/workspace, uploads); test infrastructure (vitest globals+jsdom, `@` alias, jest-dom, Playwright with BASE_URL); recommended migration order (matches Tasks 08-12). Commit:

```bash
git add docs/error-handling-audit.md && git commit -m "docs(audit): error handling audit"
```

- [ ] **Step 5: Verify**

```bash
npx tsc --noEmit && npm run lint && npm run i18n:check --strict
```

Expected: all pass (no code changed; audit is documentation only).

---

## Task 02: AppError Model

**Files:**
- Create: `src/lib/errors/AppError.ts`
- Create: `src/lib/errors/index.ts`
- Test: `src/lib/__tests__/AppError.test.ts`

- [ ] **Step 1: Write the failing test**

`src/lib/__tests__/AppError.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { fromHttpStatus, isAppError } from "../errors/AppError";

describe("fromHttpStatus", () => {
  it("classifies common statuses", () => {
    expect(fromHttpStatus(401).category).toBe("authentication");
    expect(fromHttpStatus(401).retryable).toBe(false);
    expect(fromHttpStatus(403).category).toBe("authorization");
    expect(fromHttpStatus(404).category).toBe("not_found");
    expect(fromHttpStatus(409).category).toBe("conflict");
    expect(fromHttpStatus(422).category).toBe("validation");
    expect(fromHttpStatus(429).category).toBe("rate_limit");
    expect(fromHttpStatus(429).retryable).toBe(true);
    expect(fromHttpStatus(500).category).toBe("server");
    expect(fromHttpStatus(500).retryable).toBe(true);
    expect(fromHttpStatus(503).retryable).toBe(true);
    expect(fromHttpStatus(418).category).toBe("client");
    expect(fromHttpStatus(418).retryable).toBe(false);
    expect(fromHttpStatus(599).category).toBe("server");
  });
  it("preserves status", () => {
    expect(fromHttpStatus(401).status).toBe(401);
  });
});

describe("isAppError", () => {
  it("recognizes AppError-shaped values", () => {
    expect(isAppError(fromHttpStatus(500))).toBe(true);
  });
  it("rejects non-AppError values", () => {
    expect(isAppError(new Error("x"))).toBe(false);
    expect(isAppError(null)).toBe(false);
    expect(isAppError({ category: "server" })).toBe(false); // missing retryable
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/lib/__tests__/AppError.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement**

`src/lib/errors/AppError.ts`:

```ts
export type ErrorCategory =
  | "authentication"
  | "authorization"
  | "validation"
  | "conflict"
  | "not_found"
  | "rate_limit"
  | "network"
  | "server"
  | "service"
  | "client"
  | "unknown";

export interface AppError {
  category: ErrorCategory;
  code?: string;
  status?: number;
  retryable: boolean;
  retryAfter?: number;
  fieldErrors?: Record<string, string[]>;
  params?: Record<string, unknown>;
  requestId?: string;
  cause?: unknown;
}

const SERVER_STATUS = new Set<number>([500, 502, 503, 504, 599]);

export function fromHttpStatus(status: number): AppError {
  if (status === 401) return { category: "authentication", status, retryable: false };
  if (status === 403) return { category: "authorization", status, retryable: false };
  if (status === 404) return { category: "not_found", status, retryable: false };
  if (status === 409) return { category: "conflict", status, retryable: false };
  if (status === 422) return { category: "validation", status, retryable: false };
  if (status === 429) return { category: "rate_limit", status, retryable: true };
  if (SERVER_STATUS.has(status)) return { category: "server", status, retryable: true };
  if (status >= 400 && status < 500) {
    return { category: "client", status, retryable: false };
  }
  if (status >= 500) {
    return { category: "unknown", status, retryable: false };
  }
  return { category: "unknown", status, retryable: false };
}

export function isAppError(value: unknown): value is AppError {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.category === "string" && typeof v.retryable === "boolean";
}
```

`src/lib/errors/index.ts`:

```ts
export * from "./AppError";
export * from "./normalizeError";
```

**Plan amendment (post-review, Task 02):** the original `NON_RETRYABLE`-set version classified unlisted 4xx (e.g. 418) as `"unknown"`, contradicting its own test (expects `"client"`). Fixed: any 4xx that isn't one of the named statuses → `"client"`/non-retryable; 5xx not in `SERVER_STATUS` → `"unknown"`/non-retryable.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- src/lib/__tests__/AppError.test.ts`
Expected: PASS (5 tests)

Note: `import { normalizeError } from "../errors"` in index.ts requires `normalizeError.ts` to exist — create a minimal placeholder export now, replaced for real in Task 03:

`src/lib/errors/normalizeError.ts`:

```ts
// Task 03 replaces this with the full implementation.
export {};
```

- [ ] **Step 5: Typecheck + commit**

Run: `npx tsc --noEmit`
Commit:

```bash
git add src/lib/errors src/lib/__tests__/AppError.test.ts
git commit -m "feat(errors): AppError model with status classification"
```

---

## Task 03: normalizeHttpError / normalizeException / normalizeStreamError

**Files:**
- Modify: `src/lib/errors/normalizeError.ts`
- Test: `src/lib/__tests__/normalizeError.test.ts`

- [ ] **Step 1: Write the failing tests**

`src/lib/__tests__/normalizeError.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { normalizeException, normalizeHttpError, normalizeStreamError } from "../errors/normalizeError";

const envelope = (status: number, code: string, detail: string, context?: Record<string, unknown>) =>
  JSON.stringify({ error: { code, detail, context: context ?? {} } });

describe("normalizeHttpError — structured envelope", () => {
  it("401 with known code preserves code", () => {
    const err = normalizeHttpError(401, envelope(401, "auth_invalid_credentials", "Invalid email or password"));
    expect(err.category).toBe("authentication");
    expect(err.code).toBe("auth_invalid_credentials");
    expect(err.status).toBe(401);
    expect(err.retryable).toBe(false);
  });
  it("429 with retry_after carries retryAfter", () => {
    const err = normalizeHttpError(429, envelope(429, "rate_limit_exceeded", "Slow down", { retry_after: 42 }));
    expect(err.category).toBe("rate_limit");
    expect(err.retryable).toBe(true);
    expect(err.retryAfter).toBe(42);
  });
  it("retry_after 0 is preserved, not dropped", () => {
    const err = normalizeHttpError(429, envelope(429, "rate_limit_exceeded", "Slow down", { retry_after: 0 }));
    expect(err.retryAfter).toBe(0);
  });
  it("drops unsafe context params", () => {
    const err = normalizeHttpError(500, envelope(500, "internal_error", "boom", { retry_after: 5, secret: "hunter2" }));
    expect(err.params).toEqual({});
    expect(err.retryAfter).toBe(5);
  });
});

describe("normalizeHttpError — FastAPI string detail", () => {
  it("401 string detail", () => {
    const err = normalizeHttpError(401, JSON.stringify({ detail: "Incorrect username or password" }));
    expect(err.category).toBe("authentication");
    expect(err.status).toBe(401);
  });
  it("500 string detail never leaks into message surface", () => {
    const err = normalizeHttpError(500, JSON.stringify({ detail: "pg_dump failed (exit 1): FATAL: connection refused" }));
    expect(err.category).toBe("server");
    expect(err.cause).toBeUndefined();
  });
});

describe("normalizeHttpError — Pydantic validation", () => {
  it("maps loc to fieldErrors with catalog keys", () => {
    const body = JSON.stringify({
      detail: [
        { loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" },
        { loc: ["body", "email"], msg: "field required", type: "missing" },
      ],
    });
    const err = normalizeHttpError(422, body);
    expect(err.category).toBe("validation");
    expect(err.status).toBe(422);
    expect(err.fieldErrors).toEqual({
      email: ["errors.validation.value_error", "errors.validation.missing"],
    });
  });
  it("skips non-body loc segments and maps unknown types to generic", () => {
    const body = JSON.stringify({
      detail: [{ loc: ["query", "x"], msg: "boom", type: "weird_type" }],
    });
    const err = normalizeHttpError(400, body);
    expect(err.fieldErrors).toEqual({ x: ["errors.validation.generic"] });
  });
  it("stringifies numeric loc segments (list items)", () => {
    const body = JSON.stringify({
      detail: [{ loc: ["body", "items", 0, "name"], msg: "field required", type: "missing" }],
    });
    const err = normalizeHttpError(422, body);
    expect(err.fieldErrors).toEqual({ "items.0.name": ["errors.validation.missing"] });
  });
});

describe("normalizeHttpError — plain/ad-hoc/malformed", () => {
  it("ad-hoc {error: string}", () => {
    const err = normalizeHttpError(503, JSON.stringify({ error: "bot not ready" }));
    expect(err.category).toBe("server");
    expect(err.status).toBe(503);
    expect(err.retryable).toBe(true);
  });
  it("plain text body", () => {
    const err = normalizeHttpError(502, "Bad Gateway");
    expect(err.category).toBe("server");
  });
  it("malformed JSON", () => {
    const err = normalizeHttpError(500, "{not json");
    expect(err.category).toBe("server");
  });
  it("empty body", () => {
    const err = normalizeHttpError(401, "");
    expect(err.category).toBe("authentication");
  });
});

describe("normalizeException", () => {
  it("AbortError → network retryable", () => {
    const abort = new DOMException("The operation was aborted.", "AbortError");
    const err = normalizeException(abort);
    expect(err.category).toBe("network");
    expect(err.retryable).toBe(true);
  });
  it("fetch TypeError → network retryable", () => {
    const err = normalizeException(new TypeError("Failed to fetch"));
    expect(err.category).toBe("network");
    expect(err.retryable).toBe(true);
  });
  it("generic Error → unknown, cause preserved", () => {
    const original = new Error("whatever");
    const err = normalizeException(original);
    expect(err.category).toBe("unknown");
    expect(err.retryable).toBe(false);
    expect(err.cause).toBe(original);
  });
  it("non-Error throw (string) → unknown", () => {
    const err = normalizeException("boom");
    expect(err.category).toBe("unknown");
  });
});

describe("normalizeStreamError", () => {
  it("maps stream error codes to service category", () => {
    const err = normalizeStreamError("model_timeout");
    expect(err.category).toBe("service");
    expect(err.code).toBe("model_timeout");
    expect(err.retryable).toBe(true);
  });
  it("handles empty code", () => {
    const err = normalizeStreamError("");
    expect(err.category).toBe("service");
    expect(err.code).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test -- src/lib/__tests__/normalizeError.test.ts`
Expected: FAIL (no exports)

- [ ] **Step 3: Implement**

Replace the placeholder `src/lib/errors/normalizeError.ts`:

```ts
import { fromHttpStatus, type AppError } from "./AppError";

const VALIDATION_TYPE_MAP: Record<string, string> = {
  missing: "errors.validation.missing",
  string_type: "errors.validation.string_type",
  integer_type: "errors.validation.integer_type",
  value_error: "errors.validation.value_error",
};

function classifyHttp(status: number, body: unknown): AppError {
  const base = fromHttpStatus(status);
  if (typeof body === "object" && body !== null) {
    const b = body as Record<string, unknown>;
    const inner = b.error;
    if (typeof inner === "object" && inner !== null) {
      const e = inner as Record<string, unknown>;
      const context = (typeof e.context === "object" && e.context !== null ? e.context : {}) as Record<string, unknown>;
      const retryAfter = typeof context.retry_after === "number" ? context.retry_after : undefined;
      const error: AppError = { ...base, code: typeof e.code === "string" ? e.code : undefined, params: {} };
      if (retryAfter !== undefined) error.retryAfter = retryAfter;
      return error;
    }
    if (Array.isArray(b.detail)) {
      const fieldErrors: Record<string, string[]> = {};
      for (const item of b.detail as Array<Record<string, unknown>>) {
        const loc = item.loc;
        const type = typeof item.type === "string" ? item.type : "";
        const key = VALIDATION_TYPE_MAP[type] ?? "errors.validation.generic";
        if (!Array.isArray(loc) || loc.length === 0) continue;
        const field = loc
          .filter((s) => String(s) !== "body" && String(s) !== "query" && String(s) !== "path")
          .map((s) => String(s))
          .join(".");
        if (!field) continue;
        (fieldErrors[field] ??= []).push(key);
      }
      return { ...base, fieldErrors };
    }
  }
  return base;
}

export function normalizeHttpError(status: number, bodyText: string): AppError {
  if (!bodyText.trim()) return fromHttpStatus(status);
  try {
    const parsed: unknown = JSON.parse(bodyText);
    return classifyHttp(status, parsed);
  } catch {
    return fromHttpStatus(status);
  }
}

export function normalizeException(error: unknown): AppError {
  const name = typeof error === "object" && error !== null ? (error as { name?: unknown }).name : undefined;
  if (name === "AbortError" || name === "TimeoutError") {
    return { category: "network", retryable: true, cause: error };
  }
  if (error instanceof TypeError && /fetch|network|failed/i.test(error.message)) {
    return { category: "network", retryable: true, cause: error };
  }
  return { category: "unknown", retryable: false, cause: error };
}

export function normalizeStreamError(code: string): AppError {
  return { category: "service", code: code || undefined, retryable: true };
}
```

Notes for the engineer: the FastAPI string-detail case (`b.detail` is a string) falls through to `base` — no fieldErrors, no code — matching the tests above. The `detail` string is intentionally never surfaced (catalog-driven).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm run test -- src/lib/__tests__/normalizeError.test.ts`
Expected: PASS (all 19 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/errors/normalizeError.ts src/lib/__tests__/normalizeError.test.ts
git commit -m "feat(errors): normalize HTTP, exception, and stream failures"
```

---

## Task 04: Message Registry (catalog keys + hooks)

**Files:**
- Modify: `messages/en.json`, `messages/am.json` — add `errors` namespace
- Create: `src/hooks/useErrorMessage.ts`
- Test: `src/hooks/__tests__/useErrorMessage.test.tsx`

- [ ] **Step 1: Write the failing test**

`src/hooks/__tests__/useErrorMessage.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { errorMessageKeys } from "../useErrorMessage";

const error = {
  category: "authentication" as const,
  code: "auth_invalid_credentials",
  status: 401,
  retryable: false,
};

describe("errorMessageKeys", () => {
  it("resolves known codes to the codes.* key", () => {
    expect(errorMessageKeys(error).key).toBe("errors.codes.auth_invalid_credentials");
  });
  it("unknown code falls back to http.<status>", () => {
    expect(errorMessageKeys({ ...error, code: "bogus_xyz" }).key).toBe("errors.http.401");
  });
  it("no status falls back to categories.<category>", () => {
    expect(errorMessageKeys({ category: "network", retryable: true }).key).toBe("errors.categories.network");
  });
  it("complete fallback chain ends at errors.generic", () => {
    expect(errorMessageKeys({ category: "unknown", retryable: false }).key).toBe("errors.generic");
  });
});

describe("useErrorMessage (renders, no raw output)", () => {
  it("renders the catalog message for a known code", () => {
    let text = "";
    function Probe() {
      const { useErrorMessage } = require("../useErrorMessage");
      text = useErrorMessage(error);
      return null;
    }
    render(
      <NextIntlClientProvider locale="en" messages={{ errors: { codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." } } }}>
        <Probe />
      </NextIntlClientProvider>,
    );
    expect(text).toContain("Invalid email or password");
  });

  it("returns empty string for null/undefined", () => {
    const { useErrorMessage } = require("../useErrorMessage");
    let text = "x";
    function Probe() {
      text = useErrorMessage(null);
      return null;
    }
    render(
      <NextIntlClientProvider locale="en" messages={{}}>
        <Probe />
      </NextIntlClientProvider>,
    );
    expect(text).toBe("");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/hooks/__tests__/useErrorMessage.test.tsx`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement the hook**

`src/hooks/useErrorMessage.ts`:

```ts
"use client";

import { useTranslations } from "next-intl";
import type { AppError } from "@/lib/errors";

export interface MessageKey {
  key: string;
  params?: Record<string, unknown>;
}

const CATEGORY_KEY = (c: string): string => `errors.categories.${c}`;
const HTTP_KEY = (s: number): string => `errors.http.${s}`;
const CODE_KEY = (c: string): string => `errors.codes.${c}`;

export function errorMessageKeys(error: AppError): MessageKey {
  if (error.code) return { key: CODE_KEY(error.code) };
  if (error.status) return { key: HTTP_KEY(error.status) };
  return { key: CATEGORY_KEY(error.category) };
}

export function useErrorMessage(error: AppError | null | undefined): string {
  const t = useTranslations();
  if (!error) return "";
  const { key, params } = errorMessageKeys(error);
  return t(key, params);
}
```

Note: `useTranslations()` without an argument uses root messages — `t("errors.codes.auth_invalid_credentials")` resolves against the full catalog. Missing deep keys render their own key through next-intl's fallback, never crash; the fallback chain in `errorMessageKeys` guarantees we only pass keys we ship.

- [ ] **Step 4: Add the `errors` namespace to both catalogs**

Append to `messages/en.json` (top-level sibling of `"login"`):

```json
"errors": {
  "generic": "Something went wrong. Please try again.",
  "http": {
    "400": "The request could not be completed.",
    "401": "Your session is invalid or has expired. Please sign in again.",
    "403": "You don't have permission to do this.",
    "404": "The item you're looking for could not be found.",
    "409": "This action conflicts with existing data.",
    "422": "Please check the highlighted fields.",
    "429": "Too many requests. Please try again shortly.",
    "500": "Something went wrong on our side. Please try again in a moment."
  },
  "categories": {
    "authentication": "Please sign in to continue.",
    "authorization": "You don't have permission to do this.",
    "validation": "Please check your input and try again.",
    "conflict": "This action conflicts with existing data.",
    "not_found": "The item you're looking for could not be found.",
    "rate_limit": "Too many requests. Please try again shortly.",
    "network": "Please check your internet connection and try again.",
    "server": "Something went wrong on our side. Please try again in a moment.",
    "service": "This service is temporarily unavailable. Please try again in a moment.",
    "client": "The request could not be completed.",
    "unknown": "Something went wrong. Please try again."
  },
  "codes": {
    "auth_invalid_credentials": "Invalid email or password. Please check your credentials and try again.",
    "auth_invalid_otp": "The verification code is invalid. Please try again.",
    "auth_otp_expired": "The verification code has expired. Please request a new one.",
    "auth_token_expired": "Your session has expired. Please sign in again.",
    "auth_refresh_expired": "Your session has expired. Please sign in again.",
    "auth_user_inactive": "This account is inactive. Please contact support.",
    "rate_limit_exceeded": "Too many requests. Please try again shortly."
  },
  "validation": {
    "generic": "Please check the {field} field.",
    "missing": "Please fill in the {field} field.",
    "string_type": "Please enter valid text in the {field} field.",
    "integer_type": "Please enter a number in the {field} field.",
    "value_error": "Please enter a valid value for the {field} field."
  }
}
```

Append the identical structure to `messages/am.json` (parity rule — same keys, Amharic values):

```json
"errors": {
  "generic": "ይቅርታ፣ የሆነ ችግር ተፈጥሯል። እባክዎ እንደገና ይሞክሩ።",
  "http": {
    "400": "ጥያቄው ሊጠናቀቅ አልቻለም።",
    "401": "ክፍለ ጊዜዎ ጊዜው አልፎበታል ወይም የተሳሳተ ነው። እባክዎ እንደገና ይግቡ።",
    "403": "ይህን ለማድረግ ፈቃድ የለዎትም።",
    "404": "የፈለጉት ነገር ሊገኝ አልቻለም።",
    "409": "ይህ እርምጃ ካለው መረጃ ጋር ይጋጫል።",
    "422": "እባክዎ ምልክት የተደረገባቸውን መስኮች ያረጋግጡ።",
    "429": "በጣም ብዙ ጥያቄዎች። እባክዎ ትንሽ ቆይተው ይሞክሩ።",
    "500": "በእኛ በኩል ችግር ተፈጥሯል። እባክዎ ትንሽ ቆይተው ይሞክሩ።"
  },
  "categories": {
    "authentication": "ለመቀጠል እባክዎ ይግቡ።",
    "authorization": "ይህን ለማድረግ ፈቃድ የለዎትም።",
    "validation": "እባክዎ ያስገቡትን ይመልከቱ እና እንደገና ይሞክሩ።",
    "conflict": "ይህ እርምጃ ካለው መረጃ ጋር ይጋጫል።",
    "not_found": "የፈለጉት ነገር ሊገኝ አልቻለም።",
    "rate_limit": "በጣም ብዙ ጥያቄዎች። እባክዎ ትንሽ ቆይተው ይሞክሩ።",
    "network": "እባክዎ የበይነመረብ ግንኙነትዎን ያረጋግጡ እና እንደገና ይሞክሩ።",
    "server": "በእኛ በኩል ችግር ተፈጥሯል። እባክዎ ትንሽ ቆይተው ይሞክሩ።",
    "service": "አገልግሎቱ በአሁኑ ጊዜ አይገኝም። እባክዎ ትንሽ ቆይተው ይሞክሩ።",
    "client": "ጥያቄው ሊጠናቀቅ አልቻለም።",
    "unknown": "የሆነ ችግር ተፈጥሯል። እባክዎ እንደገና ይሞክሩ።"
  },
  "codes": {
    "auth_invalid_credentials": "ኢሜይል ወይም የይለፍ ቃል ትክክል አይደለም። እባክዎ ያረጋግጡ እና እንደገና ይሞክሩ።",
    "auth_invalid_otp": "የማረጋገጫ ኮዱ ትክክል አይደለም። እባክዎ እንደገና ይሞክሩ።",
    "auth_otp_expired": "የማረጋገጫ ኮዱ ጊዜው አልፏል። እባክዎ አዲስ ኮድ ይጠይቁ።",
    "auth_token_expired": "ክፍለ ጊዜዎ ጊዜው አልፏል። እባክዎ እንደገና ይግቡ።",
    "auth_refresh_expired": "ክፍለ ጊዜዎ ጊዜው አልፏል። እባክዎ እንደገና ይግቡ።",
    "auth_user_inactive": "ይህ መለያ አገልግሎት ላይ የለም። እባክዎ ድጋፍን ያግኙ።",
    "rate_limit_exceeded": "በጣም ብዙ ጥያቄዎች። እባክዎ ትንሽ ቆይተው ይሞክሩ።"
  },
  "validation": {
    "generic": "እባክዎ የ{field} መስክን ያርሙ።",
    "missing": "እባክዎ የ{field} መስክን ይሙሉ።",
    "string_type": "እባክዎ በ{field} መስክ ውስጥ የተሟላ ጽሑፍ ያስገቡ።",
    "integer_type": "እባክዎ በ{field} መስክ ውስጥ ቁጥር ያስገቡ።",
    "value_error": "እባክዎ ለ{field} መስክ ትክክለኛ እሴት ያስገቡ።"
  }
}
```

- [ ] **Step 5: Verify i18n parity**

Run: `npm run i18n:check --strict`
Expected: PASS (validate both catalogs parse; keys identical; no duplicates).

- [ ] **Step 6: Run the hook tests + typecheck, commit**

Run: `npm run test -- src/hooks/__tests__/useErrorMessage.test.tsx && npx tsc --noEmit`
Commit:

```bash
git add messages src/hooks
git commit -m "feat(errors): catalog-driven error message registry (en+am)"
```

---

## Task 05: API Client Integration

**Files:**
- Modify: `src/lib/fetch.ts` (throw `AppError`; `streamFetch` `onError` type)
- Modify: `src/lib/fetchWithAuth.ts` (single-flight refresh, safe redirect, `fetchWithAuthJson`, `normalizeStreamError` usage)
- Test: `src/lib/__tests__/fetchWithAuth.test.ts`

- [ ] **Step 1: Update `fetchWithTimeout` to throw `AppError`**

Replace the non-ok branch (lines 17-25) in `src/lib/fetch.ts`:

```ts
    if (!res.ok) {
      const text = await res.text().catch(() => "")
      throw normalizeHttpError(res.status, text)
    }
```

And update the import at the top:

```ts
import { normalizeHttpError } from "./errors"
```

- [ ] **Step 2: Change `streamFetch` `onError` to receive `AppError`**

In `src/lib/fetch.ts` change the callbacks type and the three error sites:

```ts
import { normalizeHttpError, normalizeStreamError } from "./errors"
import type { AppError } from "./errors"

export type StreamCallbacks = {
  onStatus?: (status: string) => void
  onToken?: (token: string) => void
  onAudio?: (base64: string) => void
  onMetadata?: (metadata: Record<string, unknown>) => void
  onError?: (error: AppError) => void
  onDone?: () => void
}
```

In `streamFetch`, non-ok branch:

```ts
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    callbacks.onError?.(normalizeHttpError(res.status, text))
    return
  }
```

In the reader-missing branch:

```ts
  if (!reader) {
    callbacks.onError?.({ category: "service", code: "no_response_body", retryable: true })
    return
  }
```

In the SSE loop, `chunk.error` branch:

```ts
        if (chunk.error) {
          callbacks.onError?.(normalizeStreamError(chunk.error))
          return
        }
```

- [ ] **Step 3: Rewrite `fetchWithAuth` with single-flight refresh + safe redirect; add `fetchWithAuthJson`**

Replace `src/lib/fetchWithAuth.ts`:

```ts
import { normalizeHttpError } from "./errors"

const REFRESH_URL = "/auth/refresh"
const NO_REDIRECT_PREFIXES = [
  "/login",
  "/auth/refresh",
  "/auth/token",
  "/auth/request-otp",
  "/auth/verify-otp",
  "/auth/register",
  "/auth/logout",
  "/auth/oauth",
]

let refreshPromise: Promise<boolean> | null = null

function singleFlightRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(REFRESH_URL, { method: "POST", credentials: "include" })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return
  const current = window.location.pathname + window.location.search
  if (current === "/login" || current.startsWith("/login/")) return
  window.location.href = `/login?next=${encodeURIComponent(current)}`
}

export { redirectToLogin }; // exported for tests; do not import elsewhere

function authorized(url: string, options: RequestInit = {}): [string, RequestInit] {
  const headers = { "Content-Type": "application/json", ...(options.headers ?? {}) }
  return [url, { ...options, credentials: "include", headers }]
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const [authUrl, authOpts] = authorized(url, options)
  let res = await fetch(authUrl, authOpts)
  if (res.status !== 401) return res
  if (NO_REDIRECT_PREFIXES.some((p) => url.startsWith(p))) return res
  const refreshed = await singleFlightRefresh()
  if (refreshed) {
    res = await fetch(authUrl, authOpts)
    if (res.status !== 401) return res
  }
  redirectToLogin()
  return res
}

export async function fetchWithAuthJson<T = unknown>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetchWithAuth(url, options)
  const text = await res.text().catch(() => "")
  if (!res.ok) throw normalizeHttpError(res.status, text)
  try {
    return (text ? JSON.parse(text) : null) as T
  } catch {
    throw { category: "service", code: "malformed_response", retryable: true } as const
  }
}
```

Notes: `credentials: "include"` keeps cookie-based auth; `fetchWithAuth` still returns the 401 `Response` after scheduling the redirect so callers can render error UI if the page survives the navigation. Multiple parallel 401s share one refresh (single-flight). Requests to login/refresh/oauth URLs never trigger refresh or redirect (no redirect loops).

- [ ] **Step 4: Write tests for `fetchWithAuth` behavior**

`src/lib/__tests__/fetchWithAuth.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchWithAuth } from "../fetchWithAuth";

const ok = (body = "{}") => ({ ok: true, status: 200, text: () => Promise.resolve(body) });

describe("fetchWithAuth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("returns non-401 responses untouched", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(ok() as any);
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith("/api/students", expect.objectContaining({ credentials: "include" }));
  });

  it("refreshes once and retries on 401", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve('{"error":{"code":"auth_token_expired"}}') } as any)
      .mockResolvedValueOnce(ok() as any) // refresh
      .mockResolvedValueOnce(ok() as any); // retry
    const res = await fetchWithAuth("/api/students");
    expect(res.status).toBe(200);
    expect(fetch).toHaveBeenCalledWith("/auth/refresh", expect.objectContaining({ method: "POST" }));
  });

  it("single-flights concurrent 401s (one refresh call)", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce(ok() as any) // refresh
      .mockResolvedValueOnce(ok() as any) // retry A
      .mockResolvedValueOnce(ok() as any); // retry B
    const [a, b] = await Promise.all([fetchWithAuth("/api/a"), fetchWithAuth("/api/b")]);
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    const refreshCalls = vi.mocked(fetch).mock.calls.filter(([u]) => u === "/auth/refresh");
    expect(refreshCalls.length).toBe(1);
  });

  it("does not refresh for login/refresh URLs", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    const res = await fetchWithAuth("/login");
    expect(res.status).toBe(401);
    expect(fetch).not.toHaveBeenCalledWith("/auth/refresh", expect.anything());
  });

  it("redirects to /login?next=... when refresh fails (once)", async () => {
    const spy = vi.spyOn(fwa, "redirectToLogin").mockImplementation(() => {});
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("skips redirect when already on /login", async () => {
    const spy = vi.spyOn(fwa, "redirectToLogin").mockImplementation(() => {});
    Object.defineProperty(window, "location", {
      value: { pathname: "/login", search: "", href: "http://x/login" },
      configurable: true,
    });
    vi.mocked(fetch)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any)
      .mockResolvedValueOnce({ status: 401, ok: false, text: () => Promise.resolve("x") } as any);
    await fetchWithAuth("/api/students");
    expect(spy).not.toHaveBeenCalled();
  });
});
```

Import at the top of the test file:

```ts
import * as fwa from "../fetchWithAuth";
```

Expected: PASS (6 tests). `redirectToLogin` is exported solely for this spy; the module's internal calls still use the same function object (no indirection), so `vi.spyOn` on the namespace works because `fetchWithAuth` references the exported binding in the same module.

- [ ] **Step 5: Run tests + typecheck**

Run: `npm run test -- src/lib/__tests__/fetchWithAuth.test.ts && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 6: Migrate `streamFetch` consumer `ask/page.tsx` minimal compile fix**

In `src/app/(dashboard)/ask/page.tsx` the `onError` callbacks currently receive strings. For Task 05, only make it compile with the new `onError?: (error: AppError) => void` signature — the full UI conversion happens in Task 11. The page's error state stays `string` for now; map the `AppError` to a safe provisional message using the page's existing root catalog access. The page already uses `tc` and `ta` handles (check the top of the file for the exact `useTranslations` namespaces). Add one merged translator call at top level:

```ts
const tRoot = useTranslations()
```

and at each of the three `onError` sites, replace the string assignment with:

```ts
onError: (err) => setError(tRoot(err.category === "network" ? "errors.categories.network" : "errors.generic"))
```

Do not call hooks inside the callbacks. `npx tsc --noEmit` must pass after this step.

- [ ] **Step 7: Verify consumers + commit**

Run: `npx tsc --noEmit && npm run lint && npm run test`
Expected: all pass (ask page compile fix included).
Commit:

```bash
git add src/lib/fetch.ts src/lib/fetchWithAuth.ts "src/app/(dashboard)/ask/page.tsx" src/lib/__tests__/fetchWithAuth.test.ts
git commit -m "feat(errors): normalize at API client boundary, safe auth redirect"
```

---

## Task 06: Shared Error Components

**Files:**
- Create: `src/components/ui/errors/ErrorAlert.tsx`, `ErrorState.tsx`, `FieldError.tsx`, `ErrorBanner.tsx`, `index.ts`
- Test: `src/components/ui/errors/__tests__/ErrorAlert.test.tsx`, `ErrorState.test.tsx`, `FieldError.test.tsx`

- [ ] **Step 1: Write failing tests**

`src/components/ui/errors/__tests__/ErrorAlert.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import { ErrorAlert } from "../ErrorAlert";

const messages = {
  errors: {
    generic: "Something went wrong. Please try again.",
    codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." },
    http: { "429": "Too many requests. Please try again shortly." },
  },
};

function renderAlert(props: React.ComponentProps<typeof ErrorAlert>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorAlert {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ErrorAlert", () => {
  it("renders the catalog message for a known code", () => {
    renderAlert({ error: { category: "authentication", code: "auth_invalid_credentials", status: 401, retryable: false } });
    expect(screen.getByText(/Invalid email or password/)).toBeInTheDocument();
  });
  it("renders the generic message for unknown errors", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
  });
  it("exposes an accessible alert role", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
  it("never renders raw JSON or object", () => {
    renderAlert({ error: { category: "unknown", retryable: false } });
    expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
  });
  it("fires the retry action when supplied", () => {
    const onRetry = vi.fn();
    renderAlert({ error: { category: "server", status: 500, retryable: true }, onRetry });
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
  it("hides the retry button when not supplied", () => {
    renderAlert({ error: { category: "authentication", status: 401, retryable: false } });
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
```

`src/components/ui/errors/__tests__/ErrorState.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import { ErrorState } from "../ErrorState";

const messages = {
  errors: { generic: "Something went wrong. Please try again." },
  common: { retry: "Retry" },
};

function renderState(props: React.ComponentProps<typeof ErrorState>) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorState {...props} />
    </NextIntlClientProvider>,
  );
}

describe("ErrorState", () => {
  it("shows message and retry for retryable errors", () => {
    const onRetry = vi.fn();
    renderState({ error: { category: "server", status: 500, retryable: true }, onRetry });
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });
  it("hides retry for non-retryable errors", () => {
    renderState({ error: { category: "not_found", status: 404, retryable: false }, onRetry: () => {} });
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
  it("supports an explicit title override", () => {
    renderState({ error: { category: "server", retryable: false }, title: "Couldn't load students", onRetry: () => {} });
    expect(screen.getByText("Couldn't load students")).toBeInTheDocument();
  });
});
```

`src/components/ui/errors/__tests__/FieldError.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { FieldError } from "../FieldError";

const messages = {
  errors: {
    validation: {
      missing: "Please fill in the {field} field.",
      value_error: "Please enter a valid value for the {field} field.",
    },
  },
};

describe("FieldError", () => {
  it("renders each message with the field param", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <FieldError id="email-error" field="email" messages={["errors.validation.missing", "errors.validation.value_error"]} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByText("Please fill in the email field.")).toBeInTheDocument();
    expect(screen.getByText("Please enter a valid value for the email field.")).toBeInTheDocument();
  });
  it("associates with the input via aria-describedby id", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <div>
          <input type="text" aria-describedby="email-error" />
          <FieldError id="email-error" field="email" messages={["errors.validation.missing"]} />
        </div>
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-describedby", "email-error");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test -- src/components/ui/errors`
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement components**

`src/components/ui/errors/ErrorAlert.tsx`:

```tsx
"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorAlertProps {
  error: AppError | null;
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}

export function ErrorAlert({ error, title, onRetry, retrying, className = "" }: ErrorAlertProps) {
  const t = useTranslations("errors");
  const message = useErrorMessage(error);
  if (!error) return null;
  return (
    <div
      role="alert"
      className={`flex items-start gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 ${className}`}
    >
      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium text-red-400">{title}</p>}
        <p>{message}</p>
      </div>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry} loading={retrying} className="flex-shrink-0">
          {t("retry")}
        </Button>
      )}
    </div>
  );
}
```

`src/components/ui/errors/ErrorState.tsx`:

```tsx
"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorStateProps {
  error: AppError | null;
  title?: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
}

export function ErrorState({ error, title, onRetry, retrying, className = "" }: ErrorStateProps) {
  const t = useTranslations();
  const message = useErrorMessage(error);
  if (!error) return null;
  return (
    <div role="alert" className={`text-center py-16 ${className}`}>
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" aria-hidden="true" />
      <p className="font-medium text-foreground">{title ?? t("errors.error_title")}</p>
      <p className="text-foreground-muted mt-1">{message}</p>
      {onRetry && error.retryable && (
        <Button onClick={onRetry} loading={retrying} className="mt-4">
          <RefreshCw className="w-4 h-4" aria-hidden="true" />
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}
```

`src/components/ui/errors/FieldError.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";

interface FieldErrorProps {
  id: string;
  field: string;
  messages: string[];
  className?: string;
}

export function FieldError({ id, field, messages, className = "" }: FieldErrorProps) {
  const t = useTranslations();
  if (!messages.length) return null;
  return (
    <span id={id} role="alert" aria-live="polite" className={`text-sm text-red-400 block mt-1 ${className}`}>
      {messages.map((key) => (
        <span key={key} className="block">
          {t(key, { field })}
        </span>
      ))}
    </span>
  );
}
```

`src/components/ui/errors/ErrorBanner.tsx`:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { useErrorMessage } from "@/hooks/useErrorMessage";
import type { AppError } from "@/lib/errors";

interface ErrorBannerProps {
  error: AppError;
  onAction?: () => void;
  actionLabel?: string;
}

export function ErrorBanner({ error, onAction, actionLabel }: ErrorBannerProps) {
  const t = useTranslations();
  const message = useErrorMessage(error);
  return (
    <div role="alert" className="flex items-center justify-between gap-4 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 text-sm text-red-400">
      <p>{message}</p>
      {onAction && (
        <Button variant="danger" size="sm" onClick={onAction}>
          {actionLabel ?? t("common.retry")}
        </Button>
      )}
    </div>
  );
}
```

`src/components/ui/errors/index.ts`:

```ts
export { ErrorAlert } from "./ErrorAlert";
export { ErrorState } from "./ErrorState";
export { FieldError } from "./FieldError";
export { ErrorBanner } from "./ErrorBanner";
```

The components reference catalog keys `errors.retry`, `errors.error_title`, `common.retry` — add to both catalogs in Step 4.

- [ ] **Step 4: Add the two extra keys to both catalogs**

In `messages/en.json` errors namespace add:

```json
  "retry": "Try again",
  "error_title": "Something went wrong"
```

In `messages/am.json` errors namespace add:

```json
  "retry": "እንደገና ይሞክሩ",
  "error_title": "የሆነ ችግር ተፈጥሯል"
```

(`common.retry` already exists — verify with `node -e "console.log(require('./messages/en.json').common.retry)"`.)

- [ ] **Step 5: Run tests + gates, commit**

Run: `npm run test -- src/components/ui/errors && npx tsc --noEmit && npm run i18n:check --strict`
Commit:

```bash
git add src/components/ui/errors messages
git commit -m "feat(errors): shared error UX components"
```

---

## Task 07: Global Error Boundaries

**Files:**
- Create: `src/app/error.tsx`, `src/app/global-error.tsx` (+ catalog keys)
- Test: `src/components/ui/errors/__tests__/ErrorBoundaryUI.test.tsx` (optional smoke — the files are Next-specific; component-level test of the fallback UI body)

- [ ] **Step 1: Implement `src/app/error.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errors");

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("route render error", error);
    }
  }, [error]);

  return (
    <div role="alert" className="min-h-[40vh] flex flex-col items-center justify-center text-center px-4">
      <AlertTriangle className="w-10 h-10 text-red-400 mb-3" aria-hidden="true" />
      <h1 className="text-lg font-semibold text-foreground">{t("error_title")}</h1>
      <p className="text-sm text-foreground-muted mt-1">{t("boundary_message")}</p>
      <button
        onClick={reset}
        className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors"
        type="button"
      >
        {t("refresh_page")}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Implement `src/app/global-error.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("errors");

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("global error", error);
    }
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen flex items-center justify-center bg-background">
        <div role="alert" className="text-center px-4">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" aria-hidden="true" />
          <h1 className="text-lg font-semibold text-foreground">{t("error_title")}</h1>
          <p className="text-sm text-foreground-muted mt-1">{t("boundary_message")}</p>
          <button onClick={reset} type="button" className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium">
            {t("refresh_page")}
          </button>
        </div>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Add catalog keys** (both catalogs, errors namespace)

```json
  "boundary_message": "We encountered an unexpected problem.",
  "refresh_page": "Refresh Page"
```

Amharic:

```json
  "boundary_message": "ያልተጠበቀ ችግር አጋጥሞናል።",
  "refresh_page": "ገጹን አድስ"
```

- [ ] **Step 4: Verify gates + commit**

Run: `npx tsc --noEmit && npm run i18n:check --strict && npm run build`
Expected: build passes; NODE_ENV=production build shows no console.error of runtime details to users (dev-only console is fine).
Commit:

```bash
git add src/app/error.tsx src/app/global-error.tsx messages
git commit -m "feat(errors): global route error boundaries"
```

---

## Task 08: Login / OAuth Migration (the trigger bug)

**Files:**
- Modify: `src/app/(marketing)/login/page.tsx`
- Test: `src/app/(marketing)/login/__tests__/LoginPage.test.tsx`

- [ ] **Step 1: Write the failing test (login failure shows translated Alert, never raw)**

`src/app/(marketing)/login/__tests__/LoginPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const messages = {
  login: {
    brand_short: "EthioBio", teacher_dashboard: "Teacher Dashboard", sign_in: "Sign In",
    create_account: "Create Account", email: "Email", password: "Password",
    email_placeholder: "you@school.edu", password_placeholder: "••••••••",
    register_as: "Register as", teacher: "Teacher", student: "Student", parent: "Parent",
    please_wait: "Please wait…", create_and_sign_in: "Create & Sign In",
    already_have_account: "Already have an account?", new_teacher: "New here?",
    continue_with_google: "Continue with Google", login_telegram: "Log in with Telegram",
    telegram_otp: "Telegram OTP", telegram_id: "Telegram ID", telegram_id_hint: "123456789",
    otp_code: "OTP Code", send_otp: "Send OTP", sending: "Sending…",
    verify_login: "Verify & Log In", verifying: "Verifying…", back_to_email: "Back",
    error: "Sign-in failed", telegram_error: "Telegram sign-in failed",
  },
  errors: {
    retry: "Try again",
    codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." },
    http: { "500": "Something went wrong on our side. Please try again in a moment." },
  },
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders a translated error alert on invalid credentials (no raw object)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ error: { code: "auth_invalid_credentials", detail: "Invalid email or password", context: {} } })),
    }));
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <LoginPage />
      </NextIntlClientProvider>,
    );
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() =>
      expect(screen.getByText(/Invalid email or password/)).toBeInTheDocument(),
    );
    expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
    expect(screen.queryByText("auth_invalid_credentials")).not.toBeInTheDocument();
  });

  it("renders a translated alert on backend 500", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve(JSON.stringify({ detail: "pg_dump failed (exit 1)" })),
    }));
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <LoginPage />
      </NextIntlClientProvider>,
    );
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "rightpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() => expect(screen.getByText(/Something went wrong on our side/)).toBeInTheDocument());
    expect(screen.queryByText(/pg_dump/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- "src/app/(marketing)/login/__tests__/LoginPage.test.tsx"`
Expected: FAIL — current page renders the raw string (`[object Object]` from the object Throw; the first test's expectations fail).

- [ ] **Step 3: Migrate the page**

In `src/app/(marketing)/login/page.tsx`:

- Import: `import { ErrorAlert } from "@/components/ui/errors"` and `import { normalizeException } from "@/lib/errors"`.
- Change state: `const [error, setError] = useState<AppError | null>(null)` where `AppError` type imported from `@/lib/errors`.
- Replace the two `catch (err: any) { setError(err.message) }` blocks and the OTP handlers' catch blocks with:

```ts
    } catch (err) {
      setError(normalizeException(err))
    }
```

- Replace the email-mode inline error block (lines ~114-119) with:

```tsx
            {error && <ErrorAlert error={error} onRetry={() => void handleSubmit({ preventDefault: () => {} } as React.FormEvent)} />}
```

  Simpler (no retry on login): `{error && <ErrorAlert error={error} />}`
- Replace the telegram-mode raw `<p>` (line ~249) with: `{error && <ErrorAlert error={error} />}`
- Add a translated title for the form error per the existing `t('error')` key: `title={t('error')}` for email mode, `title={t('telegram_error')}` for telegram mode — both keys already exist in `messages/login.*` (the test fixtures confirm `error` and `telegram_error`).

- [ ] **Step 4: Run tests + gates, commit**

Run: `npm run test -- "src/app/(marketing)/login/__tests__/LoginPage.test.tsx" && npx tsc --noEmit && npm run lint && npm run i18n:check --strict`
Commit:

```bash
git add "src/app/(marketing)/login"
git commit -m "fix(errors): login shows translated error UI instead of raw backend text"
```

Also verify no other consumer of `login` error state broke: `npm run test`

---

## Task 09: Students Migration

**Files:**
- Modify: `src/app/(dashboard)/students/page.tsx`, `src/app/(dashboard)/students/[id]/page.tsx`

- [ ] **Step 1: Migrate `students/page.tsx`**

- State: `const [error, setError] = useState<AppError | null>(null)`; import `AppError` and `ErrorState`/`normalizeException`.
- `fetchStudents`: replace `catch (err: unknown) { setError(err instanceof Error ? err.message : String(err)) }` with:

```ts
    } catch (err) {
      setError(normalizeException(err))
    }
```

- Replace the error return block with:

```tsx
  if (error) return (
    <ErrorState
      error={error}
      title={t("students_load_error")}
      onRetry={() => void fetchStudents()}
    />
  )
```

- Add to `messages/en.json` `common` namespace:

```json
  "students_load_error": "We couldn't load your students"
```

and to `messages/am.json`:

```json
  "students_load_error": "ተማሪዎችን መጫን አልቻልንም"
```

- [ ] **Step 2: Migrate `students/[id]/page.tsx`**

Open the file, locate its error state + catch handler, apply the same three-part pattern (AppError state, `normalizeException` catch, `ErrorState` with `common.students_load_error` handling for load failures, and for action failures — delete/save — use `ErrorAlert` with retry where retryable). Record any deviation in the audit doc checklist (mark `students/[id]`: migrated).

- [ ] **Step 3: Gates + commit**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run i18n:check --strict`
Commit:

```bash
git add "src/app/(dashboard)/students" messages
git commit -m "feat(errors): migrate students pages to error layer"
```

---

## Task 10: Dashboard Migration

**Files:**
- Modify: `src/components/dashboard-v2/dashboards/*.tsx` (StudentDashboard, TeacherDashboard, ParentDashboard, SchoolDashboard, AdminDashboard) and `src/components/dashboard-v2/AIInsightPanel.tsx`, `HeroSection.tsx` where they fetch/stream

- [ ] **Step 1: Audit the dashboards' fetch pattern**

Open each dashboard file; note every `fetchWithTimeout` call, `catch`, and error state. Dashboards fetch via `fetchWithTimeout` and client-side effects. Apply per-dashboard:

- [ ] **Step 2: Migrate top-level load errors**

For each dashboard: convert `error` state to `AppError | null`; catch → `normalizeException(err)`; render top-level failures with:

```tsx
<ErrorState error={error} title={t(loadErrorKey)} onRetry={() => void load()} />
```

where `loadErrorKey` is a dashboard-specific `v2.*` catalog key added to en+am (parity rule). HeroSection and per-widget failures: keep independent widget state; failed widgets render a compact `ErrorBanner` (or `ErrorAlert` with retry) while the rest of the dashboard stays rendered — do NOT let a single widget's error replace the page. Concrete per-widget pattern (e.g. in `StudentDashboard.tsx`, the insights/activity widgets):

```tsx
// widget-level: keep its own error state; the page shell keeps rendering
{insightError && (
  <ErrorBanner
    error={insightError}
    actionLabel={t("common.retry")}
    onAction={() => void loadInsights()}
  />
)}
```

If a dashboard component has no per-widget state and loading a widget throws into the page-level catch, keep the page-level `ErrorState` but preserve already-loaded data: render the error banner *above* the cached data instead of replacing it:

```tsx
  if (error && students.length === 0) {
    return <ErrorState error={error} title={t(loadErrorKey)} onRetry={() => void load()} />;
  }
  // data already loaded → keep rendering, surface the failure as a banner
  return (
    <div>
      {error && <ErrorBanner error={error} onAction={() => void load()} />}
      {/* existing dashboard content using cached data */}
    </div>
  );
```

- [ ] **Step 3: AIInsightPanel (streams via ask endpoint)**

If it uses `streamFetch`, its `onError` receives `AppError` (Task 05). Render `ErrorAlert` instead of raw error text; `category === "service"` → `v2.insight_service_error` key ("AI insights are temporarily unavailable", am: "የAI ግንዛቤዎች በአሁኑ ጊዜ አይገኙም").

- [ ] **Step 4: Gates + commit**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run i18n:check --strict`
Commit:

```bash
git add src/components/dashboard-v2 messages
git commit -m "feat(errors): migrate v2 dashboards to error layer"
```

---

## Task 11: AI Surfaces Migration (ask / conversation / voice / workspace)

**Files:**
- Modify: `src/app/(dashboard)/ask/page.tsx`, `src/components/ConversationSidebar.tsx`, `src/hooks/useVoiceTurn.ts`, `src/components/VoiceRecorderButton.tsx`, `src/components/QuizVoiceButton.tsx`

- [ ] **Step 1: Replace the provisional ask-page fix (Task 05)**

In `src/app/(dashboard)/ask/page.tsx`:

- Replace `useState<string | null>` error with `useState<AppError | null>`.
- Three `onError` sites now receive `AppError` directly: `onError={(err) => setError(err)}`.
- Replace the error render block (lines ~349-357, the raw `{error}` + `isServerError` text) with:

```tsx
      {error && (
        <ErrorAlert
          error={error}
          title={error.category === "service" ? tc("service_error_title") : tc("error")}
          onRetry={error.retryable ? () => void resendTurn() : undefined}
          retrying={retrying}
        />
      )}
```

- Remove `isServerError` (backend code sniffing) — category covers it. Add catalog keys to `messages/{en,am}.json` under the `ask` namespace (match the page's existing namespace — `tc` comes from `useTranslations('ask')`; confirm at the top of the file, adjust namespace name if different):

```json
  "service_error_title": "AI assistant unavailable"
```

en, am: `"service_error_title": "የAI ረዳት አይገኝም"`.

- [ ] **Step 2: ConversationSidebar / voice hooks**

`src/hooks/useVoiceTurn.ts` and `useConversationHistory.ts`: align any error strings with the same pattern (AppError state + ErrorAlert/ErrorBanner rendering at the caller). `VoiceRecorderButton`/`QuizVoiceButton` STT errors: `service` category → `ask.service_error_title` texts; never surface provider names (e.g. "addis-whisper") — confirm none are rendered.

- [ ] **Step 3: Workspace (browse/processing — AI generation + uploads)**

`src/app/(dashboard)/workspace/browse/page.tsx` and `processing/page.tsx`: locate all fetch/upload error handling; convert to the pattern; upload failures use `errors.http.*`/`errors.categories.*` (server/network) and precise user-correctable messages where the backend's 422 validation indicates file-type/size problems (`errors.validation.*` family). Never render provider/internal names or raw upload errors.

- [ ] **Step 4: Gates + commit**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run i18n:check --strict`
Commit:

```bash
git add "src/app/(dashboard)/ask" "src/app/(dashboard)/workspace" src/hooks src/components messages
git commit -m "feat(errors): migrate AI and voice surfaces to error layer"
```

---

## Task 12: Uploads Migration (workspace processing)

**Files:**
- Modify: `src/app/(dashboard)/workspace/browse/page.tsx` (upload dropzone), `src/app/(dashboard)/workspace/processing/page.tsx` + any `src/components/workspace*` helpers

- [ ] **Step 1: Locate upload error handling**

```bash
rg -n "upload|FormData|file" "src/app/(dashboard)/workspace" src/components --include="*.tsx" -l
```

- [ ] **Step 2: Convert upload failures**

- Client-side validation (file type/size) stays as client-side `AppError` construction: `{ category: "client", retryable: false, params: {} }` rendered via `ErrorAlert` with precise messages — add `errors.upload.*` keys (en+am): `unsupported_type` ("Unsupported file type. Please upload a supported document or image." / am: "ያልተደገፈ የፋይል አይነት። እባክዎ የሚደገፍ ሰነድ ወይም ምስል ይምጡ።"), `too_large` ("That file is too big." / am: "ፋይሉ በጣም ትልቅ ነው።").
- Server upload failures → `normalizeException`/`normalizeHttpError` via the client; render generic `errors.categories.server`/`network` text. Never display the raw upload error body.

- [ ] **Step 3: Gates + commit**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run i18n:check --strict`
Commit:

```bash
git add "src/app/(dashboard)/workspace" messages
git commit -m "feat(errors): migrate upload surfaces to error layer"
```

---

## Task 13: Raw Error Rendering Sweep

**Files:**
- Modify: files flagged RAW_UI in the Task 01 audit (convert), followed-up stragglers get GitHub issues
- Update: `docs/error-handling-audit.md` (mark resolved)

- [ ] **Step 1: Re-run the search**

```bash
rg -n "JSON\.stringify\((error|response|err|res)\)|\.detail\b|\{error\}" src --include="*.tsx" --include="*.ts" -g '!**/__tests__/**'
rg -n "setError\(|error &&|catch \(" src --include="*.tsx" -l
```

- [ ] **Step 2: Classify every hit**

RAW_UI (user-facing → convert now with the established pattern, or file a follow-up ticket with the file:line in the issue body; converting requires: AppError state + ErrorAlert/ErrorState/FieldError + normalizeException in catch + catalog keys en+am) vs LOGGING (keep; acceptable for `console.error` in dev tooling) vs DERIVED (keep — e.g. `isAppError`-style branching). Document the classification table in the audit doc.

- [ ] **Step 3: Convert all trivial RAW_UI hits**

A "trivial" conversion = string state → AppError state + one component swap + one catalog key. Apply to every trivial hit found. For non-trivial stragglers, file GitHub issues (one per page) via `gh issue create` with the template: title `[error-ux] Migrate <page> to AppError layer`, body containing the Audit §RAW_UI table row.

- [ ] **Step 4: Final search — no user-facing raw error rendering remains**

```bash
rg -n "JSON\.stringify\((error|response|err|res)\)" src --include="*.tsx" --include="*.ts" -g '!**/__tests__/**'
```

All remaining hits must be LOGGING/DERIVED (documented). Commit:

```bash
git add src docs/error-handling-audit.md
git commit -m "refactor(errors): eliminate raw error rendering from user-facing UI"
```

---

## Task 14: Critical E2E Specs

**Files:**
- Create: `e2e/login-error.spec.ts`, `e2e/session-expiry.spec.ts`

- [ ] **Step 1: Login success + failure spec**

`e2e/login-error.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";

test.describe("Login error handling", () => {
  test("invalid credentials show a translated error, not raw backend text", async ({ page }) => {
    await page.route("**/auth/token", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "auth_invalid_credentials", detail: "Invalid email or password", context: {} } }),
      }),
    );
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', "a@b.c");
    await page.fill('input[type="password"]', "wrong");
    await page.click('button[type="submit"]');
    await expect(page.getByText(/Invalid email or password/)).toBeVisible();
    await expect(page.getByText("[object Object]")).toBeHidden();
  });

test("successful login navigates to the dashboard", async ({ page }) => {
    await page.route("**/auth/token", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "set-cookie": "access_token=dummy-token;Path=/;HttpOnly" },
        body: JSON.stringify({ access_token: "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwicm9sZSI6InRlYWNoZXIifQ.x" }),
      }),
    );
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', "a@b.c");
    await page.fill('input[type="password"]', "right");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(new RegExp("/classroom"));
  });
```

Note: the `set-cookie` header matters — `src/middleware.ts` redirects to `/login` when the `access_token` cookie is absent, so the mocked login must plant it for the post-login navigation to survive. The `/classroom` page's own data fetches hit the real backend (same as the existing E2E suite, which runs against the local stack); this spec only mocks auth.

- [ ] **Step 2: Session-expiry spec**

`e2e/session-expiry.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";

test.describe("Session expiry", () => {
  test("expired session redirects to /login with next param", async ({ page }) => {
    await page.context().addCookies([{ name: "access_token", value: "expired", url: BASE_URL }]);
    await page.route("**/api/teacher/students", (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "auth_token_expired", detail: "x", context: {} } }) }),
    );
    await page.route("**/auth/refresh", (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "auth_refresh_expired", detail: "x", context: {} } }) }),
    );
    await page.goto(`${BASE_URL}/students`);
    await expect(page).toHaveURL(/\/login\?next=/);
  });

  test("no redirect loop when already on /login", async ({ page }) => {
    await page.context().addCookies([{ name: "access_token", value: "expired", url: BASE_URL }]);
    await page.route("**/auth/token", (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ error: { code: "auth_invalid_credentials", detail: "x", context: {} } }) }),
    );
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[type="email"]', "a@b.c");
    await page.fill('input[type="password"]', "wrong");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/login$/);
  });
});
```

- [ ] **Step 3: Run E2E**

Run (requires `npm run dev` or a built+started app; see `playwright.config.ts` webServer if configured):

```bash
npx playwright test e2e/login-error.spec.ts e2e/session-expiry.spec.ts
```

Expected: PASS against the running app (route mocks intercept backend so no live auth needed). If the config has no webServer, start the app in one terminal (`npm run dev` or `npm start` after `npm run build`) and set `BASE_URL`.

- [ ] **Step 4: Commit**

```bash
git add e2e
git commit -m "test(e2e): login failure and session-expiry error paths"
```

---

## Task 15: Security Audit

**Files:**
- Update: `docs/error-handling.md` (security section, Task 16) — this task is review-only; findings become issues

- [ ] **Step 1: Leak search**

```bash
rg -n "console\.(log|debug|error|info)\(" src --include="*.ts" --include="*.tsx" -g '!**/__tests__/**'
rg -n "localStorage|sessionStorage|document\.cookie" src --include="*.ts" --include="*.tsx"
rg -n "Authorization|Bearer|access_token|refresh_token" src --include="*.tsx" --include="*.ts"
```

- [ ] **Step 2: Review findings**

Verify: no token/secret/credential ever logged or rendered; `error.cause` never rendered (only dev-logged in `error.tsx` behind NODE_ENV check); `normalizeHttpError` doesn't preserve `detail` bodies; stream errors (`normalizeStreamError`) carry codes but the ask page renders only catalog text. File GitHub issues for anything unsafe found.

- [ ] **Step 3: Update audit doc security checklist**

Mark each item PASS/FAIL with evidence; commit:

```bash
git add docs/error-handling-audit.md
git commit -m "docs(security): error-handling security audit findings"
```

---

## Task 16: Documentation

**Files:**
- Create: `dashboard/docs/error-handling.md`

- [ ] **Step 1: Write the guide**

`dashboard/docs/error-handling.md` covering: the invariant (API boundary → `normalizeHttpError`/`normalizeException` → `AppError` → `useErrorMessage`/shared components → user); `AppError` shape + categories; classification table; resolution order (codes → http → categories → generic); how to add a new error code (backend code → `errors.codes.<code>` in en+am same PR); validation mapping; 401/session handling rules (single-flight, no-redirect paths); component usage recipes (ErrorAlert/ErrorState/FieldError/ErrorBanner/error.tsx); stream errors; security rules (never log/display detail bodies, tokens, cause; dev-only console). Include the "Never" diagrams from the spec §Mission.

- [ ] **Step 2: Commit**

```bash
git add dashboard/docs/error-handling.md
git commit -m "docs(errors): error handling usage guide"
```

---

## Task 17: Final Verification + Diff Review

**Files:** none (verification only)

- [ ] **Step 1: Full gate suite**

```bash
npx tsc --noEmit
npm run lint
npm run test
npm run i18n:check --strict
npm run build
npx playwright test e2e/login-error.spec.ts e2e/session-expiry.spec.ts
```

Expected: all PASS.

- [ ] **Step 2: Static sweep**

```bash
rg -n "JSON\.stringify\((error|response|err|res)\)" src --include="*.tsx" --include="*.ts" -g '!**/__tests__/**'
rg -n "\[object Object\]|undefined|null" src/components/ui/errors
```

All remaining hits: LOGGING/DERIVED only (per Task 13 classification).

- [ ] **Step 3: Diff review**

```bash
git log --oneline $(git merge-base HEAD origin/main)..HEAD
git diff --stat $(git merge-base HEAD origin/main)
```

Confirm: every commit belongs to this plan; no unrelated files changed (`git diff --name-only` reviewed line by line).

- [ ] **Step 4: Report**

Produce the final report: Task 01-17 status table, verification results (each command run + result), open follow-up tickets (straggler pages), and note that backend was untouched.

---

## Self-Review Notes (plan author, fixed inline)

- Spec §4.3 §4.4 are fully covered by Tasks 02/03/05; §4.5 by Task 04; §4.6 by Task 06; §4.7 by Task 07; §4.8 by Tasks 08-12; §4.9 covered inside Tasks 09/10 (ErrorState + preserve-loaded-data on refresh); §5 by Task 15; §6 by Tasks 02-14; DoD checklist maps 1:1 to Tasks 01-17.
- Type consistency: `AppError.category/status/code/retryable/retryAfter/fieldErrors/params/cause` used identically everywhere; export names fixed: `normalizeHttpError`, `normalizeException`, `normalizeStreamError`, `isAppError`, `fromHttpStatus`, `useErrorMessage`, `errorMessageKeys`, `fetchWithAuthJson`, `redirectToLogin` (exported for the spy test), components from `@/components/ui/errors`.
- Task 05 test note about duplicate `Object.defineProperty` blocks is called out inline (keep one per test; preferred: spy on exported `redirectToLogin`).
- Catalog key collisions: `errors.*` namespace is new (verified absent pre-task); `common.retry` exists (verified); `ask.error`/`ask.telegram_error` exist (login test fixtures match existing keys).