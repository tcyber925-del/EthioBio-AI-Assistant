# Migrate Backend to Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the EthioBio AI Assistant backend (FastAPI API + Telegram bot + Postgres/pgvector + Redis + scheduled reminders) from Railway to Render, with zero data loss and a clean rollback path.

**Architecture:** Replace Railway's services with a Render workspace containing: one **Web Service** (`ethiobio-api`, Docker runtime, holds the API + Telegram bot in webhook mode) — the largest single change is that the bot stops polling and uses a webhook on the API. **Managed Postgres** (pgvector-compatible) replaces the Railway Postgres; **managed Redis (Key Value)** replaces Railway Redis. The always-on reminder loop and proactive reminders move to **Render cron jobs**. The Vercel dashboard stays put and just gets a new `NEXT_PUBLIC_API_URL`. A small `scripts/render-entrypoint.sh` wrapper rewrites Render's `postgresql://` connection strings into the `postgresql+asyncpg://` form the app requires, so no app code changes are needed for the DB.

**Tech Stack:** Render (Docker web service, managed Postgres, Key Value/Redis, cron jobs), PostgreSQL 18 + pgvector extension (prod runs 18.4 — do NOT downgrade), Redis, FastAPI/uvicorn, python-telegram-bot webhook mode, Alembic, GitHub Actions (keep-alive + backups stay), Backblaze B2 (backups).

**Out of scope:** the Vercel dashboard code (only its env var changes), Ollama hosting (stays as Ollama Cloud/API — Render is not used for LLM inference).

---

## Render free-tier contract (why the plan looks the way it does) — read first

| Constraint | Value | Plan impact |
|---|---|---|
| Free web service | 512 MB RAM / 0.1 CPU, 750 free instance-hours/ws/mo | Single web service. Disable reranker (`ENABLE_RERANKER=false`). |
| Free sleep behavior | Sleeps after 15 min idle; ~1 min cold wake | Keep-alive job stays (ping every 5 min). Bot runs in webhook mode; Telegram retries for 24 h so a cold catch-up is safe. |
| Free Postgres (`Free` plan) | 1 GB storage, **expires 30 days after creation** | **Not durable.** For a real backend, provision `basic-256mb` or above. Free DB is acceptable only for staging. |
| Free Key Value (Redis) | 25 MB, in-memory, **wiped on restart** | OK for rate-limiter state; choose paid (`starter`) if you want persistence. |
| Free bandwidth | **5 GB/mo** (2026 Hobby change) | LLM/DB traffic is small; fine. |
| Free builds | Docker build on Render; torch image first build is slow | Optionally pre-build to GHCR (Task 4B) — see below. |
| Free disk | No persistent disk on free; **container FS is wiped on every deploy** | `data/diagrams`, `data/audio_recordings`, `./data` are ephemeral unless a paid plan + disk (`/app/data`) is attached. Make this a conscious decision in Task 1. |

**Dynamically enforced recommendation:** if this backend must run continuously and keep data, the honest minimal paid stack is **Web `starter` ($7) + Postgres `basic-256mb` ($7) + disk 1 GB (~$0.30) = ~$15/mo**, with optional Redis `starter` ($10) if you want persistent rate counters. The free tier works for eval/staging/demo. The plan keeps the DB plan and reranker/disks as variables you set once.

---

## File map (what this plan creates/modifies)

| File | Action | Responsibility |
|---|---|---|
| `render.yaml` | **Create (repo root)** | Declarative Render blueprint: web service, Postgres, Redis, cron jobs, env groups, disk. |
| `scripts/render-entrypoint.sh` | **Create** | Rewrites `DATABASE_URL` to `postgresql+asyncpg://`, derives `DATABASE_SYNC_URL`, then `exec`s the real command. |
| `Dockerfile` | **Modify** | Invoke entrypoint shell before the alembic/uvicorn command. |
| `.github/workflows/keep-alive.yml` | **Modify** | Point the 5-min ping at the Render URL so the free web service stays awake. |
| `.github/workflows/render-image.yml` | **Create (optional)** | Pre-build the torch image to GHCR so Render deploys an image instead of building (fast deploys). |
| `docs/runbook.md` | **Modify** | Replace Railway commands/URLs with the Render equivalents; add rollback section. |
| `docs/prd/deployment-spec.md` | **Modify** | Update platform references to Render. |
| `.env.production` | **Modify** | Update `API_BASE_URL`, `TELEGRAM_WEBHOOK_URL`, `DASHBOARD_URL` to the Render domain. |
| `dashboard` env (Vercel) | **Modify (dashboard env only)** | `NEXT_PUBLIC_API_URL` → Render URL. |
| GitHub secrets | **Modify (no file)** | `DATABASE_SYNC_URL` secret → Render DSN (used by `backup.yml`). |

You do **not** modify `src/main.py`, `src/config.py`, `src/telegram/bot.py`, or any app code: the app already supports webhook mode (`TELEGRAM_WEBHOOK_URL` env → webhook branch in `src/main.py:224`), reads all config from env (`src/config.py`), and the Dockerfile already runs `alembic upgrade head` before uvicorn. This is what makes the migration low-risk.

---

### Task 1: Decide the target plan and verify prerequisites

**Files:** none (decision + checklist)

- [ ] **Step 1: Decide service tier**

    Confirm with the product owner: free (staging/demo) vs. paid minimal (persistent). This sets the variables used throughout the rest of the plan:

    - **Free tier**: `plan: free` on web + `free` Postgres (accept 30-day expiry; set a calendar reminder to upgrade before it expires) + free Key Value. `data/` is ephemeral.
    - **Paid (recommended for a live API)**: web `starter`, Postgres `basic-256mb`, Redis `starter`, disk `1 GB` at `/app/data`.

- [ ] **Step 2: Verify the image builds locally** (catches torch/download issues before any provisioning):

```
docker build -t ethiobio-api:local-check .
```
Expected: build succeeds (≈10–20 min first time). If it fails, stop — do not start migration with a broken image.

- [ ] **Step 3: Verify prerequisites**
    - [ ] Render account + a workspace (https://render.com)
    - [ ] The GitHub repo connected to Render (`Settings → GitHub`) for blueprint deploys
    - [ ] A restorable Postgres backup: confirm a recent object exists in Backblaze B2 `ethiobio-db-backups` (from prior `backup.yml` runs), **and** that the current Railway `DATABASE_SYNC_URL` is reachable (`psql "$DATABASE_SYNC_URL" -c "SELECT 1"`).
        - **2026-08-03 incident:** backups were silently empty for 23 days — `backup.yml` installed apt `postgresql-client` (pg_dump 16) which refuses to dump the prod PostgreSQL **18.4** server, and the `pg_dump | gzip | b2 upload` pipe had no `pipefail` so a 20-byte empty gzip was uploaded. Fixed in PR #85 (docker `postgres:18-alpine` + temp file + exit-code gate). A fresh full dump was uploaded to B2 the same day. **Also note:** prod is PG 18.4 — keep `postgresMajorVersion: 18` in the blueprint (never 16).
    - [ ] Access to the Railway Dashboard to read the current env block (you copy values, not live traffic)

- [ ] **Step 4: Capture the current Railway env values to a local mirror file (never commit)**

```bash
# Copy values from Railway Dashboard → Service → Variables into this file.
# Required keys: SECRET_KEY, JWT_SECRET, INTERNAL_API_KEY, TELEGRAM_BOT_TOKEN,
# TELEGRAM_WEBHOOK_SECRET, OLLAMA_BASE_URL, OLLAMA_API_KEY, OLLAMA_CHAT_MODEL,
# OLLAMA_EMBED_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
# OPENROUTER_DEFAULT_MODEL, FALLBACK_PROVIDER, FALLBACK_API_KEY, FALLBACK_MODEL,
# PROVIDER_OPENAI_COMPATIBLE_*, SENTRY_DSN, GEMINI_API_KEY, GROQ_API_KEY,
# AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN,
# EMAIL_* (if notifications used), BACKBLAZE_B2_KEY_ID, BACKBLAZE_B2_APP_KEY (if app uploads).
cat > /tmp/render-mirror.env <<'EOF'
SECRET_KEY=<from-railway>
JWT_SECRET=<from-railway>
# ... one KEY=VALUE line per env var, real values from the Railway dashboard ...
EOF
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "docs: plan Render migration" || true
```

---

### Task 2: Create `render.yaml` (blueprint)

**Files:**
- Create: `render.yaml` (repo root)

- [ ] **Step 1: Write the blueprint**

```yaml
databases:
  - name: ethiobio-pg
    databaseName: ethiobio
    user: ethiobio
    plan: basic-256mb        # switch to "free" for staging (30-day expiry)
    postgresMajorVersion: 18   # prod is PG 18.4 — never dump 18→16

redis:
  - name: ethiobio-kv
    plan: free               # "starter" if you need persisted rate counters

services:
  - type: web
    name: ethiobio-api
    runtime: docker
    plan: starter            # switch to "free" for staging
    region: frankfurt        # nearest region; pick your region
    dockerfilePath: ./Dockerfile
    dockerContext: .
    healthCheckPath: /liveness
    envVarGroups:
      - ethiobio-app
    disk:
      name: ethiobio-data
      mountPath: /app/data
      sizeGB: 1

  - type: cron
    name: ethiobio-reminders
    runtime: docker
    schedule: "0 2 * * *"
    dockerfilePath: ./Dockerfile
    dockerContext: .
    plan: starter
    envVarGroups:
      - ethiobio-app
    startCommand: python -m scripts.send_proactive_reminders

  - type: cron
    name: ethiobio-digests
    runtime: docker
    schedule: "30 2 * * *"
    dockerfilePath: ./Dockerfile
    dockerContext: .
    plan: starter
    envVarGroups:
      - ethiobio-app
    startCommand: python -m scripts.send_digests

envVarGroups:
  - name: ethiobio-app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ethiobio-pg
          property: connectionString
      - key: REDIS_URL
        fromRedis:
          name: ethiobio-kv
          property: connectionString
      - key: OLLAMA_BASE_URL
        value: https://ollama.com           # or the endpoint you used on Railway
      - key: OLLAMA_API_KEY
        sync: false                          # set via dashboard secret
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: TELEGRAM_WEBHOOK_URL
        value: https://ethiobio-api.onrender.com/webhook
      - key: TELEGRAM_WEBHOOK_SECRET
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: JWT_SECRET
        sync: false
      - key: INTERNAL_API_KEY
        sync: false
      - key: ENABLE_RERANKER
        value: "false"
      - key: STORE_BACKEND
        value: pgvector
      - key: COLLECTION_NAME
        value: ethiobio_curriculum
      - key: VECTOR_STORE_PATH
        value: /app/data/vectors_new
      - key: DASHBOARD_URL
        value: https://ethio-bio-ai-assistant.vercel.app
      - key: API_BASE_URL
        value: https://ethiobio-api.onrender.com
      - key: SENTRY_DSN
        sync: false
```

Note: the entrypoint in `scripts/render-entrypoint.sh` (Task 3) will, at container start, rewrite the `connectionString` (`postgresql://`) into `postgresql+asyncpg://` for `DATABASE_URL` and emit `DATABASE_SYNC_URL` (so the backup + cron scripts work unchanged).

- [ ] **Step 2: Validate the blueprint** `npx render blueprint:validate render.yaml` (Render CLI: `npm i -g @render/cli`). Expected: “Blueprint is valid” or a clear error you must fix.
- [ ] **Step 3: Deploy the blueprint** `npx render blueprint:deploy render.yaml --environment production` and watch the dashboard for Postgres/Redis/web/cron resources to come up.
- [ ] **Step 4: Commit**

```bash
git add render.yaml
git commit -m "build(render): add Render blueprint for ethiobio-api"
```

---

### Task 3: Container runtime tweaks — entrypoint + Dockerfile

**Files:**
- Create: `scripts/render-entrypoint.sh`
- Modify: `Dockerfile`

- [ ] **Step 1: Write the entrypoint**

```bash
#!/usr/bin/env sh
set -e

# Rewrite Render's provided DATABASE_URL (postgresql://) into the asyncpg dialect
# the app expects (postgresql+asyncpg://). Derive DATABASE_SYNC_URL from it.
if [ -n "${DATABASE_URL:-}" ] && ! printf '%s' "$DATABASE_URL" | grep -q '+asyncpg'; then
  DATABASE_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql://#postgresql+asyncpg://#; s#^postgres://#postgresql+asyncpg://#')
  export DATABASE_URL
fi
if [ -z "${DATABASE_SYNC_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  DATABASE_SYNC_URL=$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql+asyncpg://#postgresql://#')
  export DATABASE_SYNC_URL
fi

exec "$@"
```

- [ ] **Step 2: Wire it into the Dockerfile** — replace only the last line (`CMD ...`):

```dockerfile
CMD ["sh", "/app/scripts/render-entrypoint.sh", "bash", "-c", "alembic upgrade head && python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Notes for the executor:
- Keep the rest of `Dockerfile` exactly as-is.
- Invoking via `sh` avoids needing `chmod +x` in the image.

- [ ] **Step 3: Verify the entrypoint rewrites the DSN**

```bash
docker build -t ethiobio-render-check .
docker run --rm -e DATABASE_URL=postgresql://u:p@localhost:5432/db ethiobio-render-check \
  sh /app/scripts/render-entrypoint.sh bash -c 'echo "$DATABASE_URL"; echo "$DATABASE_SYNC_URL"'
```
Expected output (two lines):
```
postgresql+asyncpg://u:p@localhost:5432/db
postgresql://u:p@localhost:5432/db
```

- [ ] **Step 4: Commit**

```bash
git add scripts/render-entrypoint.sh Dockerfile
git commit -m "build(render): entrypoint rewrites DSN to asyncpg for Render"
```

---

### Task 4: Keep the web service awake (keep-alive) and optionally pre-build the image

**Files:**
- Modify: `.github/workflows/keep-alive.yml`
- Create (optional): `.github/workflows/render-image.yml`

- [ ] **Step 1: Point keep-alive at the Render URL**

Change the `run:` line in `.github/workflows/keep-alive.yml`:

```yaml
      - run: curl -sSf -o /dev/null "https://ethiobio-api.onrender.com/liveness"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/keep-alive.yml
git commit -m "ops: point keep-alive at Render"
```

- [ ] **Step 3 (optional, recommended): pre-build the torch image to GHCR** so Render *deploys an image* instead of rebuilding the ~2 GB torch image on every push.

Create `.github/workflows/render-image.yml`:

```yaml
name: Build & push Render image
on:
  push:
    branches: [ main ]
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:latest,ghcr.io/${{ github.repository }}:${{ github.sha }}
```

Then in `render.yaml` change the web service to deploy from the image (remove `dockerfilePath`/`dockerContext`):

```yaml
  - type: web
    name: ethiobio-api
    runtime: docker
    plan: starter
    region: frankfurt
    image: ghcr.io/<owner>/<repo>:latest
    healthCheckPath: /liveness
    envVarGroups:
      - ethiobio-app
    disk:
      name: ethiobio-data
      mountPath: /app/data
      sizeGB: 1
```

Rebuild + push once, then each deploy downloads only new layers. **Keep Step 1 (keep-alive) regardless.** If you skip this task, Render builds from the Dockerfile directly — slower first deploy, still works.

---

### Task 5: Configure the web service env vars (mirror + Render-specific)

**Files:** none (Render dashboard / blueprint)

Once the web service exists, open Service → Environment and set:

- [ ] **Step 1: DB + Redis** (from the blueprint `envVarGroups`): `DATABASE_URL`, `DATABASE_SYNC_URL`, `REDIS_URL` — confirm they appear; `DATABASE_URL` should be the `postgresql+asyncpg://` form after the entrypoint rewrites it at boot.
- [ ] **Step 2: Bot + webhook**
    - `TELEGRAM_BOT_TOKEN` = the live bot token (same as Railway)
    - `TELEGRAM_WEBHOOK_URL` = `https://ethiobio-api.onrender.com/webhook`
    - `TELEGRAM_WEBHOOK_SECRET` = same value as Railway
- [ ] **Step 3: Mirror the remaining secrets** from `/tmp/render-mirror.env` (Task 1 Step 4): `SECRET_KEY`, `JWT_SECRET`, `INTERNAL_API_KEY`, `OLLAMA_*`, `OPENROUTER_*`, `FALLBACK_*`, `PROVIDER_OPENAI_COMPATIBLE_*`, `SENTRY_DSN`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `AZURE_SPEECH_*`, `CLOUDFLARE_*`, `EMAIL_*`, `BACKBLAZE_B2_*`.
- [ ] **Step 4: Render-specific toggles**
    - `ENABLE_RERANKER=false` (512 MB free/starter instances are memory-limited)
    - `DEBUG=false`, `LOG_LEVEL=INFO`
    - `STORE_BACKEND=pgvector`, `COLLECTION_NAME=ethiobio_curriculum`
    - `DASHBOARD_URL` = the Vercel URL (CORS must allow the dashboard origin)
- [ ] **Step 5: Health check** — Service → Settings → Health Check Path = `/liveness` (dependency-free endpoint already in the app; `/health` also calls the LLM router and can be slow). Keep Grace Period ≥ 10 s.
- [ ] **Step 6: Deploy** and watch the logs. Expected: image builds (or pulls GHCR), container starts, `alembic upgrade head` runs, then uvicorn logs `app_starting…` and `embedding_models_preloaded` (the on-boot SentenceTransformer preload).

---

### Task 6: Migrate the data (Postgres + vectors) from Railway to Render

**Files:** none (shell only) — reuses runbook steps; vector data lives in Postgres, so a plain dump/restore carries it.

- [ ] **Step 1: Create a full dump of the Railway database** (production DSN from Railway):

```bash
docker run --rm postgres:18-alpine pg_dump "$RAILWAY_PG_URL" --no-owner --no-acls \
  --format=custom -f /tmp/ethiobio_site.dump
ls -lh /tmp/ethiobio_site.dump   # e.g. 1.4 GB
```
Note: use a pg_dump that **matches the server major (18)** — apt `pg_dump` 16 (and anything <18) refuses to dump PG 18.4. The `postgres:18-alpine` docker image is the safe way (same image the fixed `backup.yml` uses).

- [ ] **Step 2: Restore into the fresh Render DB** (use the Render *internal* connection string — public DSN also works but costs egress):

```bash
pg_restore -d "postgresql://ethiobio:<render-pw>@dpg-xxx.render.com:5432/ethiobio" \
  --verbose --no-owner --no-acls /tmp/ethiobio_site.dump
```
Expected: success; no `ERROR ... extension "vector"` — you created the extension in Task 2 Step 2 of provisioning, and alembic re-runs it at boot.

- [ ] **Step 3: Verify the migration**
    - Table count matches: `psql ... -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"`
    - Key rows survived: compare counts of `users`, `chats`, `knowledge_items`, `questions` between dumps.
    - Vector data works: pick one row from a pgvector-backed table and run a `<->` distance query — returns a candidate.

- [ ] **Step 4: Note the verification numbers in the runbook** (no code commit; `/tmp` dumps stay local).

---

### Task 7: Cut over dependencies (webhook, dashboard, cron, keep-alive, backups)

**Files:** modify `docs/runbook.md`, `docs/prd/deployment-spec.md`, `.env.production`, Vercel env (dashboard)

- [ ] **Step 1: Point the Telegram webhook definitively at Render.** The app calls `set_webhook` at startup when `TELEGRAM_WEBHOOK_URL` is set (`src/main.py:224`). Confirm after deploy:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```
Expected: `"url": "https://ethiobio-api.onrender.com/webhook"` and no `last_error_message` 4xx.

- [ ] **Step 2: Update the dashboard env.** Vercel → Dashboard project → Environment Variables: set **Production** and **Preview** `NEXT_PUBLIC_API_URL` = `https://ethiobio-api.onrender.com`. Redeploy the Vercel project if not automatic. Ensure `DASHBOARD_URL` in the API env matches the Vercel URL (CORS).
- [ ] **Step 3: Update `docs/runbook.md`** — replace every `.up.railway.app` and `railway` command with Render equivalents:
    - Deployment checklist: `railway up` → git push (or `npx render blueprint:deploy`)
    - Deploy: `railway redeploy` → Render dashboard → Deploy button
    - Rollback: `railway redeploy --deployment=<id>` → Render → Deploys → previous deploy → “Redeploy”
    - Incidents/DB-loss triage: `railway logs` → Render logs tab; same curl commands with the new domain
- [ ] **Step 4: Update `docs/prd/deployment-spec.md` and `.env.production`** — replace the Railway domain with `ethiobio-api.onrender.com` in `.env.production` (`API_BASE_URL`, `TELEGRAM_WEBHOOK_URL`, `DASHBOARD_URL`) and the spec's domain column.

```bash
git add docs/runbook.md docs/prd/deployment-spec.md .env.production
git commit -m "docs(render): cut over runbook, spec, and env to Render"
```

- [ ] **Step 5: Point `backup.yml` at the Render DSN.** Set the GitHub secret `DATABASE_SYNC_URL` to the Render **sync** DSN (`postgresql://…`, from the entrypoint output or the service env). Test:

```bash
gh workflow run backup.yml
# wait for completion
b2 ls --recursive ethiobio-db-backups | tail -5
```
Expected: a new `ethiobio_prod_<date>.sql.gz`.

- [ ] **Step 6: Verify cron jobs.** At 02:00 UTC, `ethiobio-reminders` and `ethiobio-digests` should fire. To test immediately, trigger from the dashboard and check logs:

```bash
render logs --service ethiobio-reminders --limit 20
```

---

### Task 8: Integration smoke test

**Files:** none

- [ ] **Step 1: Health + readiness**

```bash
curl -sS https://ethiobio-api.onrender.com/liveness | jq .     # {"status":"alive"}
curl -sS https://ethiobio-api.onrender.com/readiness | jq .    # ready: true, all checks ok
curl -sS https://ethiobio-api.onrender.com/models | jq .       # model list
```

- [ ] **Step 2: DB + RAG path.** Log in as a test user (OTP or test account), then hit an endpoint that touches DB + pgvector:

```bash
TOKEN=$(curl -s -X POST https://ethiobio-api.onrender.com/auth/login -d '{"phone": "<test-phone>"}' | jq -r .access_token)
curl -s -H "Authorization: Bearer $TOKEN" "https://ethiobio-api.onrender.com/knowledge/chunks?limit=2" | jq .
```
Expected: rows returned (proves asyncpg + pgvector are working).

- [ ] **Step 3: Bot.** Send `/start` in the Telegram chat; expect a reply < ~15 s. Then ask a biology question to force a full chat + DB + RAG request.
- [ ] **Step 4: Dashboard.** Open the Vercel URL, log in, create an assignment — traffic flows against Render.
- [ ] **Step 5: Failure-mode check (free tier only).** Pause the keep-alive workflow for one hour, wait 17 min, then `curl /liveness` — expect a response within ~90 s (cold start), proving the wake path works.

---

### Task 9: Rollback plan (Render → Railway)

**Files:** modify `docs/runbook.md` (add section)

- [ ] **Step 1: Record the rollback procedure in `docs/runbook.md`:**

```markdown
## Rollback (Render → Railway)

1. Vercel: set NEXT_PUBLIC_API_URL back to https://<old>.up.railway.app and redeploy.
2. Point the Telegram webhook back at Railway:
   curl "https://api.telegram.org/bot$TOKEN/setWebhook?url=https://<old>.up.railway.app/webhook&secret_token=$TELEGRAM_WEBHOOK_SECRET"
3. Pause the Render web service (Render → service → Pause) — keep the Render DB running
   so you can diff/recover any writes that landed on Render during the pilot.
4. If the Render DB received writes you need: pg_dump Render → restore into Railway's DB
   (runbook "Database Restore" section) → alembic upgrade head → redeploy Railway.
5. Restore the keep-alive URL to the Railway /health and re-enable it.
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbook.md
git commit -m "docs(render): add Render→Railway rollback procedure"
```

---

### Task 10: Cleanup Railway (only after 7 days of green on Render)

**Files:** none

- [ ] **Step 1: Confirm no traffic still hits Railway.** Check Render logs show the bot/dashboard requests flowing; check Railway service logs stop showing request activity for 48 h.
- [ ] **Step 2: Re-verify the daily backup still lands in B2** (backup.yml now dumps the Render DB).
- [ ] **Step 3: Deprovision Railway resources** per the old runbook; keep `railway.toml` in the repo (harmless). Update the `AGENTS.md` “Deployment” section and runbook “Architecture References” table to Render.

---

## Post-migration notes

- **Persistent vs staging**: fully free works for staging/demo (web + DB 30-day + Key Value). For the 30-day DB timer, set a calendar reminder to upgrade the DB plan before expiry, or accept a fresh staging DB.
- **The `render.yaml` blueprint codifies env and DB** — re-provision or clone environments with `npx render blueprint:deploy`.
- **Disk**: `/app/data` (uploaded audio, diagrams, vector caches) persists on the paid plan. Free plan wipes it on every redeploy — a documented trade-off; a future hardening step is backing `LocalFileStorage`/uploads up to B2.

---

## Self-review (done against the plan)

- [x] Backend API on Render (web service) → Tasks 2, 5
- [x] Postgres with pgvector migrated with zero data loss → Tasks 2, 6
- [x] Redis / rate limiter → Task 2 + env in Task 5
- [x] Bot (webhook mode, no polling) → Tasks 5, 8 (Step 3)
- [x] Cron (reminders, digests) → Task 2 (cron) + Task 7 (Step 6)
- [x] Keep-alive to survive free-tier sleep → Task 4
- [x] Backups + rollback + docs → Tasks 7–9
- [x] No app source changes required — verified against `src/main.py`, `src/config.py`, `Dockerfile`
- [x] Placeholder scan: no TBDs; all file contents and commands are complete
