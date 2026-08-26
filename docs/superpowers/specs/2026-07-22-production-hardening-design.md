# Production Hardening — Four-Track Design

Date: 2026-07-22
Status: Draft

## Overview

Systematic production hardening of the EthioSci AI Assistant across security, testing/CI, performance/infrastructure, and frontend. No new features — only hardening existing surfaces.

## Track 1 — Auth, Rate Limiting, Error Handling

### 1A: Cookie-based JWT Auth

**Replace localStorage JWT with HTTP-only cookies.**

- `access_token`: 15 min TTL, `HttpOnly; Secure; SameSite=Strict; Path=/`
- `refresh_token`: 7 day TTL, stored in Redis (hashed), one-time use with rotation
- `POST /auth/refresh`: invalidate old refresh in Redis, issue new pair
- If a consumed refresh is reused → revoke ALL tokens for that user (breach detection)
- Startup guard: `SystemExit` if `JWT_SECRET` is still default
- `decode_access_token()` returns structured errors: `ExpiredSignatureError` vs `InvalidTokenError` vs `MalformedTokenError`
- PII output guardrail: replace matched text with `[REDACTED <type>]` instead of just logging

**Internal API key auth**

- New env `INTERNAL_API_KEY`, passed via `X-API-Key` header
- Bot and cron routes move to `/internal/bot/*` and `/internal/cron/*`
- `APIKeyMiddleware` checks on `/internal/*` prefix

**Files:** `src/api/auth.py`, `src/api/deps.py` (new), `src/guardrails/output/pii_scanner.py`, `src/guardrails/startup.py`, `src/config.py`, `src/main.py`, `src/telegram/bot.py`, `dashboard/src/lib/auth.ts`, `dashboard/src/lib/fetchWithAuth.ts`, `dashboard/src/middleware.ts`

### 1B: Global Rate Limiting

**Replace per-route (`/chat` only) with middleware-based tiered rate limiting on all endpoints.**

| Tier | Prefix | Window | Max |
|------|--------|--------|-----|
| `auth` | `/auth/*` | 60s | 5 |
| `otp` | `/auth/request-otp`, `/auth/verify-otp` | 300s | 3 |
| `chat` | `/chat/*` | 60s | 20 |
| `write` | POST/PUT/DELETE elsewhere | 60s | 30 |
| `read` | GET elsewhere | 60s | 100 |
| `internal` | `/internal/*` | 60s | 500 |

- Key: `{tier}:{ip}:{user_id}` (user_id if authenticated, IP otherwise)
- Backend: Redis sorted set (sliding window, existing mechanism)
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 response: `{"detail": "rate_limit_exceeded", "tier": "<tier>", "retry_after": <seconds>}`

**Files:** `src/guardrails/input/rate_limiter.py`, `src/guardrails/input/middleware.py`, `src/main.py`

### 1C: Error Handling Cleanup

**Phase 1** — Eliminate all `except: pass` (8+ locations):
- `send_telegram_otp()`: log + return 502 instead of swallowing
- `handle_children_back()`: log + return error to Telegram
- Bot fallbacks: wrap in `logger.exception()` with `chat_id`, `handler_name`, `query_preview`
- Lifespan errors: distinguish expected shutdown vs unexpected crash

**Phase 2** — Structured error format:
- New `src/core/errors.py`: `AppError(code, detail, status, context)` base class
- FastAPI exception handlers for `AppError` (structured) and `Exception` (500 generic + log)
- Every response includes `request_id`

**Phase 3** — Replace broad `except Exception` with specific types:
- `except JWTError` → `except ExpiredSignatureError | InvalidTokenError`
- `except Exception` in DB → `except SQLAlchemyError | IntegrityError`
- `except Exception` in LLM → `except httpx.TimeoutException | ProviderUnavailableError`

**Files:** `src/core/errors.py` (new), `src/telegram/bot.py`, `src/main.py`, `src/api/auth.py`, various graph/guardrail files

## Track 2 — CI & Testing Infrastructure

### 2A: Fix Broken Tests First

- `status_code in (200, 500)` → assert specific expected codes across all API tests
- Remove empty `test_forecasting.py`
- Implement 2 `pass` stubs in `test_auth.py`

### 2B: Restore CI

```yaml
jobs:
  lint:    ruff --select E,F,I,N,W,B,C4,PT,S + mypy src/ --strict
  test:    pytest -m "not slow" --cov=src --cov-fail-under=50
  security: pip-audit + bandit -r src/
```

- Tiered markers: `smoke` (always), `integration` (always), `slow` (nightly, Ollama-dependent)
- `pytest-cov` with 50% floor, ratchet up

### 2C: Enable Stricter Linting

- Ruff: add `B` (bugbear), `C4` (comprehensions), `PT` (pytest-style), `S` (security)
- Mypy: remove `call-arg`, `arg-type`, `return-value` from `disable_error_code`
- New `.pre-commit-config.yaml`: ruff + mypy + trailing-whitespace

**Files:** `.github/workflows/ci.yml`, `pyproject.toml`, `tests/test_auth.py`, `tests/test_api_endpoints*.py`, `tests/test_forecasting.py`, `.pre-commit-config.yaml` (new)

## Track 3 — Performance & Infrastructure

### 3A: ChromaDB → pgvector Only

- Remove ChromaDB as a backend option; pgvector is the sole vector store
- `store_backend` config becomes a no-op
- Eliminate dual-backend conditionals in `VectorStore`
- Removes sync I/O that blocks the async event loop

### 3B: LLM Circuit Breaker

- New `src/llm/circuit_breaker.py`: CLOSED → OPEN (5 failures) → HALF_OPEN (30s) → CLOSED (3 successes)
- One breaker per provider (ollama, openrouter, openai, anthropic)
- `ProviderManager.route()` checks before calling; skips OPEN providers
- State exposed in `/health/modules`

### 3C: Fix Eval Task Leak

- `Semaphore(5)` around `_evaluate_trace()` — max 5 concurrent eval tasks
- `pipeline_monitor` trace store: `max_traces=1000` with LRU eviction
- Periodic cleanup in cron container

### 3D: Docker Security

- Move `POSTGRES_PASSWORD`, `GF_SECURITY_ADMIN_PASSWORD` to `${PG_PASSWORD}`, `${GRAFANA_PASSWORD}`
- Pin Ollama to a specific stable version (e.g., `ollama/ollama:0.5.12` — check [Ollama releases](https://github.com/ollama/ollama/releases) for latest stable at deploy time)

**Files:** `src/rag/vector_store.py`, `src/rag/pgvector_store.py`, `src/llm/circuit_breaker.py` (new), `src/llm/manager.py`, `src/core/monitoring.py`, `src/main.py`, `docker-compose.yml`, `Dockerfile`

## Track 4 — Frontend Hardening

### 4A: Client Auth → HTTP-Only Cookies

- Remove `localStorage` reads in `dashboard/src/lib/auth.ts`
- `fetchWithAuth()` drops `Authorization: Bearer` — uses `credentials: 'include'`
- SSR middleware reads cookie server-side
- No cookie → redirect to `/login`

### 4B: Theme Cleanup

- Remove legacy `--background: #0a0e1a`, `--foreground` etc. from `globals.css`
- Remove `StatCard.tsx` if `InsightCard` covers all use cases
- All routes default to v2 theme

### 4C: Unit Test Scaffolding

- Add `vitest` + `@testing-library/react`
- Test 5 critical components: `SidebarV2`, `InsightCard`, `MarkdownRenderer`, `ActivityTimeline`, `LoginPage`
- Pattern: render → assert render → assert interaction → assert error state

**Files:** `dashboard/src/lib/auth.ts`, `dashboard/src/lib/fetchWithAuth.ts`, `dashboard/src/middleware.ts`, `dashboard/src/app/globals.css`, `dashboard/src/components/ui/StatCard.tsx`, `dashboard/package.json`, `dashboard/vitest.config.ts` (new)

## Delivery Order

Tracks are independent — each can be PR'd separately:

1. **Track 1** (highest risk reduction — security + error handling)
2. **Track 2** (must happen before any other refactoring to prevent regressions)
3. **Track 3** (performance + infra — parallel with Track 4)
4. **Track 4** (frontend — parallel with Track 3)
