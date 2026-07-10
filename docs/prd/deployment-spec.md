---
title: EthioBio AI Assistant — Production Deployment Spec
status: accepted
date: 2026-07-10
authors: [tcyber]
grilled: yes
platforms: [railway-free, vercel-hobby, upstash-free, ollama-cloud-free, Sentry-free, UptimeRobot-free]
---

# EthioBio AI Assistant — Production Deployment Spec

## Status

Accepted — result of a grilling session on 2026-07-10 that revised the original 18-phase plan to fit a `$0/month` free-tier budget.

## Platform Stack

| Service           | Platform             | Cost | Notes                                              |
|-------------------|----------------------|------|----------------------------------------------------|
| FastAPI + Bot     | Railway Free         | $0   | Single service, Fibonacci backoff, ~$1 free credit |
| PostgreSQL        | Railway Free plugin  | $0   | 0.5 GB, pgvector extension available               |
| Redis             | Upstash Free         | $0   | 10K commands/day, off-Railway                       |
| LLM inference     | Ollama Cloud Free    | $0   | 1 concurrent model, 5h/7d usage windows              |
| Dashboard         | Vercel Hobby         | $0   | 12 functions / 10s timeout — may need rework        |
| Keep-alive        | UptimeRobot Free     | $0   | 5-min pings to `/health`                            |
| Backups           | GitHub Actions + B2  | $0   | Daily `pgdump` → Backblaze B2 free 10 GB            |
| Monitoring        | Sentry Free          | $0   | 5K errors/mo, 50 replays/mo, 1K perf transactions   |
| CI / CD           | GitHub Actions free  | $0   | Public repos include 2K min/mo                      |
| Domains           | Platform subdomains  | $0   | `xxx.up.railway.app` + `xxx.vercel.app`             |

**Total ongoing cost: $0/month** until usage outgrows free limits, at which point the natural upgrade is Hobby for Railway ($5/mo, 5 GB volume, no sleeping) or Pro ($20/mo).

> Budget for an upgrade path: switch Railway Free → Hobby as soon as any of these fire:
> - Bot cold-starts exceed two per day despite keep-alive
> - DB hits 0.4 GB (80 % of 0.5 GB)
> - Ollama free 1-concurrent limit causes visible LLM latency
> - You start adding a real prod domain

## Architecture

```
                GitHub (Actions + Dependabot)
                          |
                +---------+---------+
                |                   |
            lint/test           push to main
                |                   |
                v                   v
          +-----------------------+     +-------------------+
          | Railway Free          |     | Vercel Hobby      |
          |  ┌─────────────────┐ |     |  dashboard/        |
          |  │ uvicorn          | |     |  (CSR + caching)  |
          |  │ + src.main:app   | |     +-------------------+
          |  │                  | |
          |  │ + asyncio task   | |
          |  │   telegram.bot   | |
          |  └─────────────────┘ |
          +----------+------------+
                     |
       +-------------+-------------+
       |                           |
  PostgreSQL (pgvector)      Redis (Upstash)
  Railway free plugin         Free tier
  0.5 GB                     10K cmds/day
  512 MB RAM                 256 MB cap
  pg_dump daily → B2         session + rate-limit + queue
       |
       v
  embeddings (pgvector)
  knowledge_objects
  bookmarks
  user accounts
  quiz attempts
  mastery / recovery / memory
       |
       v
  Ollama Cloud (https://ollama.com)
  API key: OLLAMA_API_KEY
  Free: 1 concurrent model; 5h session + 7d weekly window
  Models: gpt-oss:120b, glm-5.2, deepseek-v4-flash,
          qwen3.5, kimi-k2.6
       |
       v
  Optional fallback: OpenAI / Anthropic
  (already supported via existing providers)
       |
       v
  Sentry (Free) — error + perf
  UptimeRobot — 5-min ping → /health
```

## Key Decisions Resolved (from the grilling session)

1. **Service count = 2.** API + Bot bundled in one Railway container (bot runs as background `asyncio` task). No separate worker service. OCR / embedding pipelines run as in-process async tasks; nothing in Railway Free can run sidecars independently.

2. **Vector store = pgvector.** Replaces ChromaDB. Reuses the existing Railway PostgreSQL instead of needing a separate persistent volume (Free tier = 0.5 GB total). Also fixes the `'topic' returns empty` gotcha in `AGENTS.md` (PDF chunks lacked `topic` metadata; pgvector tracks metadata natively).

3. **Ollama = Ollama Cloud Free.** No self-hosted Ollama. Railway Free has no GPU. Ollama Cloud supports a direct API at `https://ollama.com/api/chat` with `Authorization: Bearer $OLLAMA_API_KEY`. Free tier: 1 concurrent model, 5-hour session window, 7-day weekly window.

4. **Redis = Upstash Free.** Moved off Railway (saves compute on the Free plan). Free tier: 10K commands/day, max 256 MB. Provides session cache + rate-limit backend + simple background queue.

5. **Dashboard = Vercel Hobby.** Keep Vercel for the `dashboard/` (Next.js App Router). Convert heavy pages to `"use client"` + fetch where 10-second limit is at risk. Verify with a preview deploy before declaring prod.

6. **Sleep = UptimeRobot 5-min ping.** Railway Free services sleep after 10 minutes idle. UptimeRobot hits `/health` every 5 minutes for free — keeps the service awake. Caveat: first request may return 502 during cold boot.

7. **AI providers = use existing `LLMProvider` ABC.** No redesign. The codebase already has `base.py`, `ollama.py`, `openai_provider.py`, `anthropic_provider.py`, `openrouter.py`. Add Ollama Cloud as a config variant of `OllamaProvider` (different host + auth header).

8. **Migrations = adopt Alembic.** Current code uses `Base.metadata.create_all()` which is unsafe for prod (no column renames / drops). Initial migration generated from current schema. `alembic upgrade head` runs on every deploy via Railway start command.

9. **Auth = existing JWT system.** Codebase already has `src/api/auth.py`. Ship as-is. Fix weak `JWT_SECRET=dev-jwt-secret` in `.env` with a 32+ byte value. Telegram bot auth = `update.effective_user.id` (no email/password). Dashboard users = existing JWT flow.

10. **Monitoring = Sentry Free only.** Drop Jaeger / Prometheus / Grafana sidecars (Railway Free can't host them). SDK + Sentry DSN env var. OTel SDKs stay in code but emit to Sentry via the Sentry OTel bridge (or no-op until needed).

11. **CI/CD = GitHub Actions lint + typecheck + smoke test on PR.** Railway auto-deploys from `main` via its GitHub integration. `railway up` only as a manual fallback.

12. **Rollback = Railway redeploy previous deployment.** One click. No auto-rollback on health-check failure (out of scope for Free tier).

13. **Domains = platform subdomains.** `xxx.up.railway.app` for API + Bot. `xxx.vercel.app` for dashboard. Custom `ethiobio.ai` deferred until traffic justifies the ~$10-20/year cost.

14. **Ship pace = MVP now, harden later.** Stage 1 ships the current codebase to Railway as-is (auto-create tables). Stages 2-4 incrementally add Alembic, pgvector migration, backups, Sentry, CI/CD, and dashboard work.

## Implementation Stages

### Stage 1 — MVP Deploy (this week)

Goal: something live that answers Telegram messages.

| Step | Owner       | Action                                                                                                              |
|------|-------------|---------------------------------------------------------------------------------------------------------------------|
| 1.1  | agent       | Commit current uncommitted work (ruff formatting fixes, `Bookmark` model + `bookmark.py` router, `bot.py:64 fix`)  |
| 1.2  | agent       | Audit `.env` for weak secrets. Set `SECRET_KEY`, `JWT_SECRET`, `OLLAMA_API_KEY` to real values. Add `OLLAMA_BASE_URL=https://ollama.com`. |
| 1.3  | agent       | Create `railway.toml` with start command `uvicorn src.main:app --host 0.0.0.0 --port $PORT` (Railway injects `PORT`). |
| 1.4  | agent       | Create `Dockerfile.railway` that uses the existing Dockerfile but without the `RUN python -c "..."` model preload (slower cold start, less RAM during build). |
| 1.5  | agent       | Create Railway account + project, link GitHub repo, provision free PostgreSQL.                                      |
| 1.6  | user        | Sign up at ollama.com, generate API key, set `OLLAMA_API_KEY` in Railway env vars.                                  |
| 1.7  | user        | Create Upstash free Redis, set `REDIS_URL` in Railway env vars.                                                     |
| 1.8  | agent       | Deploy to Railway. Verify `/health` returns `{"status": "ok", "ollama": true, "database": true}`.                  |
| 1.9  | agent       | Add Sentry SDK to `src/main.py` with `SENTRY_DSN` env var.                                                          |
| 1.10 | agent       | Create UptimeRobot account, set 5-min HTTP monitor on `https://<railway-subdomain>/health`.                         |
| 1.11 | agent       | Test bot: `/start`, `/quiz`, `/help` from a real Telegram account.                                                 |

**Acceptance criteria for Stage 1:**
- `curl https://<api>.up.railway.app/health` returns `ollama: true`
- Telegram bot responds to `/start` within 30 seconds (cold start acceptable)
- Sentry dashboard receives a test event
- UptimeRobot shows the endpoint as up

### Stage 2 — Hardening (week 2)

Goal: production-safe schema + storage + AI provider.

| Step | Action                                                                                                          |
|------|------------------------------------------------------------------------------------------------------------------|
| 2.1  | `alembic init alembic/` + configure `alembic.ini` with `DATABASE_URL`                                            |
| 2.2  | `alembic revision --autogenerate -m "baseline"` from current `Base.metadata` snapshot                            |
| 2.3  | Update Railway start command: `alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port $PORT`         |
| 2.4  | Remove `Base.metadata.create_all()` from `src/database/session.py` (relying on Alembic now)                     |
| 2.5  | Port `src/rag/vector_store.py` from ChromaDB → pgvector adapter. Use `pgvector/pgvector:pg16` Docker image (already in `docker-compose.yml`). |
| 2.6  | Add `embedding` + `metadata` JSONB columns to the `knowledge_objects` table (Alembic migration)                  |
| 2.7  | Update `src/retrieval/adapter.py` / `bm25.py` / `reranker.py` to read from pgvector instead of Chroma.           |
| 2.8  | Fix `'topic' returns empty` gotcha: write metadata with `topic`, `grade_level`, `unit`, `page` on every chunk.   |
| 2.9  | Pre-process textbooks locally via `scripts/ingest_curriculum.py` → dump SQL fixture → import into Railway PG.    |
| 2.10 | Update `OllamaProvider` to honour `OLLAMA_API_KEY` + optional `OLLAMA_BASE_URL=https://ollama.com` (Cloud).       |
| 2.11 | Add `/readiness` and `/liveness` endpoints in `src/main.py` (different from `/health`):                          |
|      |   `/liveness` = 200 OK if process alive                                                                          |
|      |   `/readiness` = checks DB + Redis + Ollama Cloud reachability                                                   |
| 2.12 | Add security headers middleware + trusted hosts filter in `src/main.py`.                                        |

**Acceptance criteria for Stage 2:**
- `alembic upgrade head` runs clean on a fresh DB
- Vector search returns `topic`-filtered results (gotcha fixed)
- Talk to bot with `/quiz` — questions come back curriculum-grounded (not hallucinated)
- `/readiness` returns `{"database": "ok", "redis": "ok", "ollama": "ok"}`
- Bot still responds on Telegram

### Stage 3 — Dashboard + CI/CD (week 3)

Goal: dashboard live on Vercel + lint/test gate on PRs.

| Step | Action                                                                                                          |
|------|------------------------------------------------------------------------------------------------------------------|
| 3.1  | `vercel link` on `dashboard/` → first preview deploy. Verify build passes.                                      |
| 3.2  | Inspect any SSR pages that exceed 10s on Vercel preview. Convert to `"use client"` + `fetch()` from the API.     |
| 3.3  | Configure Vercel env vars: `NEXT_PUBLIC_API_URL` (Railway subdomain), `NEXT_PUBLIC_ENVIRONMENT`.                |
| 3.4  | Add `vercel.json` to pin the dashboard to only deploy from `dashboard/` folder + set caching rules.              |
| 3.5  | Create `.github/workflows/ci.yml`: `ruff check . && mypy src/ && pytest tests/ -m smoke` (~3 min).              |
| 3.6  | Enable Railway GitHub integration — `main` push triggers redeploy.                                              |
| 3.7  | Add branch protection: PR checks required before merge.                                                         |

**Acceptance criteria for Stage 3:**
- `https://<dashboard>.vercel.app` loads without errors
- Teacher flow works: login → admin → review pending content
- PR with a bad change is blocked by CI
- Push to main triggers Railway deploy + Vercel deploy automatically

### Stage 4 — Reliability (week 4+)

Goal: stress-tested backups + observability + operational maturity.

| Step | Action                                                                                                          |
|------|------------------------------------------------------------------------------------------------------------------|
| 4.1  | Set up Backblaze B2 free tier (10 GB storage, free egress with Cloudflare).                                      |
| 4.2  | Add `.github/workflows/backup.yml` cron @daily: `pg_dump $DATABASE_URL | gzip | b2 upload`.                      |
| 4.3  | Document restore runbook in `docs/runbook.md` (test restore on a local Postgres instance first).                |
| 4.4  | Add request validation middleware (Pydantic v2 already in codebase — apply `model_config = ConfigDict(extra="forbid")`). |
| 4.5  | Set up Sentry alert rules: error spike > 10/min, new error in last 24h, LLM call failure > 50%.                  |
| 4.6  | Document `docs/runbook.md` with: deployment checklist, rollback steps, DB restore steps, common incidents.     |
| 4.7  | Consider buying `ethiobio.ai` domain + Cloudflare DNS (cost: ~$10-20/year).                                     |
| 4.8  | Add `api.ethiobio.ai` → Railway + `app.ethiobio.ai` → Vercel + `docs.ethiobio.ai` → Vercel static.               |

**Acceptance criteria for Stage 4:**
- Cron ran daily for 7 days without failures
- Restore runbook tested end-to-end on a fresh DB
- Incident runbook covers: bot down, DB unreachable, Ollama Cloud rate-limited, dashboard blank, Sentry alert triggered

## Open Questions (Resolved or Deferred)

### Resolved during grilling
- Service split: 2 services (consolidated)
- Ollama: Ollama Cloud Free (verified it exists)
- Storage for embeddings: pgvector (replaces Chroma)
- Bot cold starts: UptimeRobot keep-alive
- CI/CD: GitHub Actions + Railway CLI
- Migrations: adopt Alembic
- Auth: existing JWT (fix weak secrets)
- Monitoring: Sentry Free (drop Jaeger/Prometheus sidecars)
- Rollback: Railway built-in redeploy
- Domains: platform subdomains for now
- Implementation order: revised above

### Deferred until after MVP
- Custom domain `ethiobio.ai`
- Horizontal scaling (replicas) — needs Railway Pro
- Auto-rollback on health-check failure
- BetterStack + OpenTelemetry SaaS export
- Qdrant / Weaviate / Milvus migration
- Azure OpenAI / Gemini providers
- Rate-limit tuning (existing defaults work for MVP)

## Plan Phases vs. Current Codebase

Cross-reference between the original 18-phase plan and the actual codebase state:

| Original Phase         | Status        | Notes                                                                                             |
|------------------------|---------------|---------------------------------------------------------------------------------------------------|
| 1 Repository prep       | Partial       | `.env.example` exists; `railway.toml`, `vercel.json`, `.github/workflows/ci.yml` still need work  |
| 2 Config management    | **Done**      | `src/config.py` uses Pydantic Settings, env-based, no hardcoded secrets                           |
| 3 Service separation   | **Revised**   | Consolidated from 4 → 2 services (API+Bot together) for Free tier                                 |
| 4 Railway infra        | Partial       | Need to provision + env vars; `railway.toml` to be created                                       |
| 5 AI provider layer    | **Done**      | `LLMProvider` ABC already in `src/llm/providers/base.py`; only need Ollama Cloud config variant   |
| 6 Storage layer        | **Revised**   | Replaced with pgvector — eliminates Railway volume dependency                                    |
| 7 Vector store         | **Revised**   | ChromaDB → pgvector. TODO adapter port in `src/rag/vector_store.py` + `src/retrieval/adapter.py`  |
| 8 Database             | **Partially done** | Existing PostgreSQL + asyncpg + `pgvector/pgvector:pg16` in docker-compose. Needs Alembic init. |
| 9 Redis                | **Done**      | Existing rate-limit middleware + session cache + queue patterns in code                          |
| 10 Security            | Partial       | Existing `add_rate_limit_middleware` + `src/api/auth.py` need hardened secrets + headers         |
| 11 Observability       | Partial       | `/health`, `/health/modules`, `/metrics` exist. Need `/readiness` + `/liveness` distinction      |
| 12 Monitoring          | **Revised**   | Sentry Free replaces Jaeger/Prometheus/Grafana stack (can't host sidecars on Free tier)          |
| 13 CI/CD               | TODO          | GitHub Actions file to create; Railway GitHub integration to enable                              |
| 14 Vercel deploy       | TODO          | `vercel.json` to create; dashboard preview deploy to test                                        |
| 15 Custom domains      | **Deferred**  | Use platform subdomains for now                                                                  |
| 16 Deploy automation   | Partial       | Railway GitHub integration handles this once enabled; needs PR gate in Actions                    |
| 17 Rollback strategy   | **Done**      | Railway built-in redeploy previous deployment                                                     |
| 18 Production checklist| TODO          | To be run manually before declaring "prod"                                                       |

## Risk Register

| Risk                                    | Likelihood | Impact | Mitigation                                                                                  |
|-----------------------------------------|------------|--------|---------------------------------------------------------------------------------------------|
| Railway Free DB has no SLA              | High       | High   | Daily Backblaze B2 backups; documented restore runbook; monitor disk usage                  |
| Service sleeps despite UptimeRobot     | Low        | Med    | Keep-alive runs every 5 minutes; first request after sleep may need to retry                |
| Ollama Cloud free 1-concurrent limit   | Med        | Med    | Queue requests; fall back to OpenAI / Anthropic during bursts (already supported in code)   |
| Vercel 10s timeout on dashboard        | Med        | Low    | Convert heavy pages to CSR + fetch; verify with preview deploy first                        |
| Upstash 10K cmds/day exceeded           | Low        | Low    | Add Redis command counter; alert at 8K; degrade to in-memory cache past 10K                 |
| Pre-processed pgvector import too big  | Low        | Med    | Use small embedding model (all-MiniLM-L6-v2 = 384 dim); monitor 0.5 GB limit                |
| LLM hallucination on curriculum answers | Med        | High   | Existing `claim_verifier` + `hallucination_detector` nodes in LangGraph pipeline;            |
|                                        |            |        |   alert on sharp citation-rate drop in Sentry                                               |
| Chroma → pgvector port introduces bugs  | Med        | Med    | Keep Chroma code path intact for 1 release; gate pgvector behind a feature flag              |
| Single-service failure cascades         | High       | Med    | Bundled API + Bot means bot dies when API dies; accept for MVP, separate later at Pro tier  |

## Production Readiness Checklist (Stage 4 final gate)

Run this checklist before declaring "production":

- [ ] Database reachable from Railway service
- [ ] Redis reachable (Upstash)
- [ ] pgvector extension enabled + embeddings imported
- [ ] All env vars present (audit script in `scripts/check_env.py`)
- [ ] Ollama Cloud API key valid + non-rate-limited
- [ ] Telegram bot connected (polling working)
- [ ] Dashboard reachable from Vercel subdomain
- [ ] Dashboard can call Railway API (CORS configured)
- [ ] `/health` returns 200 from UptimeRobot region
- [ ] `/readiness` returns all green
- [ ] `/liveness` returns 200
- [ ] OCR pipeline tested on a sample student upload
- [ ] Vector search returns `topic`-filtered results
- [ ] Authentication works: dashboard login + JWT issued
- [ ] File uploads land in persistent storage + retrievable
- [ ] Sentry receiving errors + performance traces
- [ ] Daily backup cron has run at least once
- [ ] Restore runbook executed end-to-end on a fresh DB
- [ ] Rollback tested: redeployed prior Railway deployment
- [ ] Smoke tests passing in CI on main
- [ ] Branch protection on `main` (PR required)

## References

- `docs/adr/` — Architecture Decision Records (existing)
- `AGENTS.md` — module index, commands, gotchas
- `README.md` — full setup guide, API endpoints
- `.env.example` — all env vars
- `docker-compose.yml` — service topology reference
- Railway docs: https://docs.railway.com (pricing, serverless mode, volumes)
- Vercel docs: https://vercel.com/docs (limits, fair-use, Next.js deploy)
- Ollama Cloud docs: https://docs.ollama.com/cloud (API, models, pricing)
- Upstash docs: https://docs.upstash.com/redis (free tier limits)
- Sentry Python SDK: https://docs.sentry.io/platforms/python/
- Backblaze B2 CLI: https://docs.backblaze.com/b2/docs/b2_command_line_tool.html
