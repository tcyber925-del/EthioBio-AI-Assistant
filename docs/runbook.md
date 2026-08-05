# EthioBio AI Assistant — Operations Runbook

## Deployment Checklist

Before deploying to production:

- [ ] CI passes (ruff lint + mypy typecheck + pytest)
- [ ] `DATABASE_URL` points to the Render Postgres (`ethiobio-pg`)
- [ ] `REDIS_URL` points to Render Redis (`ethiobio-kv`)
- [ ] `OLLAMA_API_KEY` is valid and not rate-limited
- [ ] `SENTRY_DSN` is set and Sentry dashboards show green
- [ ] `BACKBLAZE_B2_KEY_ID` + `BACKBLAZE_B2_APP_KEY` are set
- [ ] Telegram bot token is valid — `/start` responds
- [ ] Vercel dashboard builds without errors
- [ ] Render service is **live** — `render services instances -o json` is non-empty
- [ ] CORS `DASHBOARD_URL` includes the Vercel domain

## Deploy

### Backend (Render)

Push to `main` runs `.github/workflows/render-image.yml`: builds the GHCR image
(`ghcr.io/tcyber925-del/ethiobio-ai-assistant:latest`) and calls the Render deploy hook.
Manual:

```bash
# Trigger a redeploy of the current image
curl -sSf -X POST "https://api.render.com/deploy/srv-d9obfaou01pc73akt160?key=1UBHLVgO49I"
# Check status
~/.local/bin/render deploys list srv-d9obfaou01pc73akt160
~/.local/bin/render services instances srv-d9obfaou01pc73akt160
```

### Frontend (Vercel)

```bash
vercel --prod                    # deploy from repo root (project rootDirectory=dashboard)
vercel env add NEXT_PUBLIC_API_URL   # set https://ethiobio-api.onrender.com
```

## Rollback

### Render (API)

```bash
~/.local/bin/render deploys list srv-d9obfaou01pc73akt160   # find previous SUCCESS deploy
# The CLI cannot promote an old deploy; instead trigger a redeploy of the last good
# image via the deploy hook, or roll back in the Render dashboard (Deploys → ⋮ → Rollback)
curl -sSf -X POST "https://api.render.com/deploy/srv-d9obfaou01pc73akt160?key=1UBHLVgO49I"
```

Vercel:

- Go to Vercel Dashboard → Deployments → find the previous working deploy → ⋮ → Promote to Production

## Rollback (Render → Railway)

Only relevant if Railway is ever re-activated as a fallback platform. Steps:

1. Vercel: set `NEXT_PUBLIC_API_URL` back to https://ethiobio-api-production.up.railway.app and redeploy.
2. Point the Telegram webhook back at Railway:

   ```bash
   curl "https://api.telegram.org/bot$TOKEN/setWebhook?url=https://ethiobio-api-production.up.railway.app/webhook&secret_token=$TELEGRAM_WEBHOOK_SECRET"
   ```

3. Pause the Render web service (Render → service → Pause) — keep the Render DB running
   so you can diff/recover any writes that landed on Render during the pilot.
4. If the Render DB received writes you need: dump via the API admin endpoint → restore into Railway's DB
   (see [Database Restore](#database-restore)) → `alembic upgrade head` → redeploy Railway.
5. Restore the keep-alive monitor URL to `https://ethiobio-api.onrender.com/liveness` and re-enable it.

## Database Restore

### Prerequisites

- Backblaze B2 credentials in env (see `.env.example`)
- `b2` CLI: `pip install b2` or `npx b2` or Docker
- PostgreSQL `pg_dump` / `pg_restore` (≥16)

### How backups work (Render migration)

External PostgreSQL access is blocked on the Render free tier, so `pg_dump` cannot
reach the DB from CI or any outside network. Instead the GitHub Actions workflow
(`.github/workflows/backup.yml`, daily 02:00 UTC + manual dispatch) drives the
deployed app itself:

1. `POST /auth/token` with `BACKUP_ADMIN_EMAIL` / `BACKUP_ADMIN_PASSWORD` secrets
   (admin account `backup@ethiobio.ai` on the production API).
2. `GET /admin/db-backup` — the app runs `pg_dump` **inside the container** using
   the internal DB host derived from `settings.database_url` (short name
   `dpg-...-a`; the full `*.render.com` hostname fails with `SSL connection has
   been closed` even from inside the container) and streams the SQL out.
3. The workflow gzips, aborts if the dump is empty, and uploads
   `ethiobio_prod_<date>.sql.gz` + `ethiobio_prod_latest.sql.gz` to the B2 bucket.

Manual trigger: `gh workflow run backup.yml` and watch with `gh run watch`.

### Restore from latest backup

```bash
# 1. Download latest backup
b2 download-file-by-name ethiobio-db-backups ethiobio_prod_latest.sql.gz /tmp/

# 2. Decompress
gunzip /tmp/ethiobio_prod_latest.sql.gz

# 3. Restore to a fresh DB (WARNING: overwrites target)
pg_restore -d "$DATABASE_URL" --clean --if-exists /tmp/ethiobio_prod_latest.sql
```

### Point-in-time recovery

```bash
# List available backups
b2 ls --recursive ethiobio-db-backups

# Download a specific backup
b2 download-file-by-name ethiobio-db-backups ethiobio_prod_2026-07-12.sql.gz /tmp/

# Restore
gunzip /tmp/ethiobio_prod_2026-07-12.sql.gz
pg_restore -d "$DATABASE_URL" --clean /tmp/ethiobio_prod_2026-07-12.sql
```

### Post-restore checks

```bash
curl https://ethiobio-api.onrender.com/health     # expect 200
curl https://ethiobio-api.onrender.com/models     # expect model list
# Telegram: send /start to bot — expect reply
# Dashboard: login at https://ethio-bio-ai-assistant.vercel.app
```

## Common Incidents

### Bot is down / API unreachable

**Symptoms:** Telegram messages get no response; `curl https://ethiobio-api.onrender.com/liveness` times out or returns HTTP 000.

**Triage:**
```bash
render logs -r srv-d9obfaou01pc73akt160 --limit 50
curl -m 15 https://ethiobio-api.onrender.com/liveness
```

**Resolution:**
1. If the service is sleeping: wait 10-15s for cold start, UptimeRobot pings every 5 min
2. If crash-looping / no instance: check `render services instances srv-d9obfaou01pc73akt160 -o json` for `[]` and look for `oomKilled` in service events (see [API OOM crash loop](#api-oom-crash-loop))
3. If crashed: trigger a redeploy via the deploy hook:
   `curl -sSf -X POST "https://api.render.com/deploy/srv-d9obfaou01pc73akt160?key=1UBHLVgO49I"` (or `render services update srv-d9obfaou01pc73akt160 --plan free`)
4. If the token is revoked: update `TELEGRAM_BOT_TOKEN` in Render env vars

### API OOM crash loop

**Symptoms:** `curl https://ethiobio-api.onrender.com/health` times out; service web UI shows repeated "OOM" restarts; `render services instances -o json` returns `[]` while the deploy shows `live`.

**Triage:**
```bash
# Instance kill reason (oomKilled = memory limit hit)
curl -sS -H "Authorization: Bearer rnd_NBhFYIhsnL9p9tqpDaggAytb38UN" \
  "https://api.render.com/v1/services/srv-d9obfaou01pc73akt160/events?limit=20"
render logs -r srv-d9obfaou01pc73akt160 --limit 80
```

**Root cause (fixed 2026-08-04/05):** the free tier caps memory at 512Mi. Two separate memory
 hogs have been removed from the request path:
 - **2026-08-04 — torch:** the app preloaded `sentence-transformers`+torch at startup (via
   `_preload_models` → embedder fallback), blowing past 512Mi → OOM → crash loop. Fix: dropped
   torch from both images and requirements; the embedder now only uses fastembed (ONNX),
   falling back to Ollama if fastembed fails.
 - **2026-08-05 — spaCy:** `RetrievalOrchestrator.search()` → `EntityExtractor._get_nlp()`
   lazily loaded `en_core_web_sm` on the **first memory-retrieval request**, spiking ~200Mi and
   OOM-killing a long-stable instance (events `server_failed oomKilled` ~5s after a
   `vector_search_unavailable` log). Fix: spaCy made optional — `_get_nlp()` returns `None`
   when not installed and entity extraction falls back to the pure-Python biology-term/difficulty
   regex matcher (which is what the tests assert). spaCy + the model wheel were removed from
   `requirements.txt`/`pyproject.toml`. Chromadb stays absent (not in requirements); the memory
   `MemoryVectorStore` caches the unavailable state so it stops re-importing per request, and
   recall works via Postgres BM25 (`search_vector`) + entity matching.

**Resolution:**
1. Confirm the running image has no torch: `docker run --rm <image> python -c "import torch"` should raise ModuleNotFoundError
2. Assess a fresh OOM: does any log line precede the kill? A `vector_search_unavailable` line then ~5s later `server_failed oomKilled` points at the retrieval path; a boot-time kill for this build points at startup preloads. See the triage command above for kill reason.
3. Ensure the embedder log line reads `local_embedder_loaded backend=fastembed` — no sentence-transformers path exists anymore
4. If the image still OOMs at ~512Mi, the next lever is upgrading the Render plan or migrating providers (as planned) — avoid re-adding torch or spaCy

### Database unreachable

**Symptoms:** `/health` returns `{"database": false}`; Tutor returns 500 errors.

**Triage:**
```bash
render logs -r srv-d9obfaou01pc73akt160 --limit 30
# or search deploy logs
render logs -r srv-d9obfaou01pc73akt160 --limit 100 | grep -iE "database|psycopg|connection"
```

**Resolution:**
1. Check the Render Postgres is Online: Render Dashboard → ethiobio-pg
2. If Postgres is up but connection fails: verify `DATABASE_URL` has correct host/port/password
3. If Postgres is down: Render restarts it automatically within a few minutes
4. If data is lost: follow [Database Restore](#database-restore)

### Ollama Cloud rate-limited

**Symptoms:** Chat responses are empty or contain LLM errors; Sentry shows `429` or `rate_limit` errors.

**Triage:**
```bash
render logs -r srv-d9obfaou01pc73akt160 --limit 100 | grep -iE "ollama|rate|429"
```

**Resolution:**
1. The codebase has a fallback chain — requests automatically retry with a different model
2. Monitor the rate limit reset header: `x-ratelimit-reset`
3. If persistent: switch the default model via the `/models` endpoint, or add an OpenAI/Anthropic key to `FALLBACK_PROVIDER_*` env vars

### Dashboard blank / 500

**Symptoms:** https://ethio-bio-ai-assistant.vercel.app shows blank page or server error.

**Triage:**
```bash
# Check Vercel deploy logs
vercel logs --deploy=<deployment-id>
# Check browser console for JS errors (F12 → Console)
# Check if API proxy works:
curl https://ethio-bio-ai-assistant.vercel.app/api/health
```

**Resolution:**
1. If API proxy returns `ROUTER_EXTERNAL_TARGET_ERROR` / 502: backend is down — see [Bot is down / API unreachable](#bot-is-down--api-unreachable)
2. If static assets 404: `vercel deploy --prod` to rebuild
3. If JS runtime error: check Vercel Build logs for TypeScript/Next.js errors
4. If CORS error in browser: verify `DASHBOARD_URL` env on Render includes the Vercel domain

### Sentry alert triggered

**Symptoms:** Email/Slack notification from Sentry (error spike > 10/min, new error, LLM failure > 50%).

**Triage:**
1. Open Sentry → Issues → find the new error group
2. Check the stack trace and event context (request body, headers, user)
3. Correlate with Render logs:
   ```bash
   render logs -r srv-d9obfaou01pc73akt160 --limit 100 | grep -iE "<error-fingerprint>"
   ```

**Resolution:**
1. New error: create a GitHub issue with Sentry permalink
2. Error spike: roll back to the last working deploy
3. LLM failure spike: check Ollama Cloud status at [status.ollama.ai](https://status.ollama.ai)
4. After fix: mark the Sentry issue as Resolved and deploy

## UptimeRobot Monitoring (keep-alive)

The Render free tier sleeps after ~15 min idle; the first request then triggers a cold start
(~1-2 min) and, historically, exposed OOM crash loops. UptimeRobot keeps the service warm and
alerts when it is genuinely down.

**Monitors (free tier: 50 monitors, 5-min interval):**

| Monitor | Type | URL | Keyword | Purpose |
|---------|------|-----|---------|---------|
| EthioBio API (Keep-Alive) | HTTP(S) | `https://ethiobio-api.onrender.com/liveness` | — | Wake + uptime |
| EthioBio API (Health) | HTTP(S) | `https://ethiobio-api.onrender.com/health` | `"ok"` | Deep check (DB + LLM) |

**Setup (one-time, manual in https://uptimerobot.com → Add New Monitor):**
1. Monitor Type: HTTP(S)
2. Friendly Name: `EthioBio API (Keep-Alive)`
3. URL: `https://ethiobio-api.onrender.com/liveness`
4. Interval: 5 minutes (free tier minimum)
5. Timeout: 30 seconds
6. Alert contacts: your email/Telegram
7. Repeat for the Health monitor with keyword `"ok"` (response body must contain it)

**Notes:**
- 5-min interval beats Render's ~15-min idle timeout, so the service stays warm.
- The GitHub Actions workflow `.github/workflows/keep-alive.yml` is kept as a backup but
  GitHub cron is unreliable (±30 min jitter) — UptimeRobot is the primary keep-alive.
- If you ever add a Telegram bot ping, keep it ≤ 4096 chars (see AGENTS.md gotchas).

## Backup Configuration

Automatic daily backups are handled by `.github/workflows/backup.yml`:

- **Schedule:** Daily at 02:00 UTC
- **Destination:** Backblaze B2 bucket `ethiobio-db-backups`
- **Retention:** 30 days (capped by B2 lifecycle rules)
- **Format:** compressed SQL dump with timestamp
- **Alert:** Workflow failure sends email to the GitHub owner

To run a manual backup (Render blocks external DB connections, so the dump runs server-side):

```bash
# 1. Get a short-lived admin token (credentials in Render env: BACKUP_ADMIN_EMAIL/PASSWORD)
TOKEN=$(curl -s -X POST https://ethiobio-api.onrender.com/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$BACKUP_ADMIN_EMAIL&password=$BACKUP_ADMIN_PASSWORD" | jq -r .access_token)

# 2. Stream the dump through the admin endpoint
curl -sS -H "Authorization: Bearer $TOKEN" \
  https://ethiobio-api.onrender.com/admin/db-backup \
  | gzip | b2 upload-file ethiobio-db-backups - "manual_$(date +%F).sql.gz"
```

## Architecture References

| Component | Location                          | URL                                                            |
|-----------|-----------------------------------|----------------------------------------------------------------|
| API       | Render — `ethiobio-api` service (srv-d9obfaou01pc73akt160) | https://ethiobio-api.onrender.com |
| Dashboard | Vercel — `ethiobio-ai-assistant`  | https://ethio-bio-ai-assistant.vercel.app                       |
| Bot       | Render — runs in `ethiobio-api`   | Telegram: @EthioBioBot                                         |
| DB        | Render — `ethiobio-pg` PostgreSQL + pgvector | `DATABASE_URL` env var                          |
| Cache     | Render — `ethiobio-kv` Redis      | `REDIS_URL` env var                                             |
| Monitor   | Sentry + UptimeRobot              | https://sentry.io/organizations/ethiobio/                       |
| Backups   | Backblaze B2 — `ethiobio-db-backups` | https://backblaze.com/cloud_storage                           |
