# EthioBio AI Assistant — Operations Runbook

## Deployment Checklist

Before deploying to production:

- [ ] CI passes (ruff lint + mypy typecheck + pytest)
- [ ] `DATABASE_URL` points to the Railway Postgres (not local)
- [ ] `REDIS_URL` points to Railway Redis (not local)
- [ ] `OLLAMA_API_KEY` is valid and not rate-limited
- [ ] `SENTRY_DSN` is set and Sentry dashboards show green
- [ ] `BACKBLAZE_B2_KEY_ID` + `BACKBLAZE_B2_APP_KEY` are set
- [ ] Telegram bot token is valid — `/start` responds
- [ ] Vercel dashboard builds without errors
- [ ] Railway service is **Online** — `railway status`
- [ ] CORS `ALLOWED_ORIGINS` includes the Vercel domain

## Deploy

### Backend (Railway)

Push to `main` triggers auto-deploy. Manual:

```bash
cd /app
railway up --detach           # deploy from local
railway redeploy --yes        # redeploy last image
railway deployment list       # check status
```

### Frontend (Vercel)

```bash
cd dashboard
vercel deploy --prod                   # from linked project
vercel logs --deploy=<deployment-id>   # check build logs
vercel env add NEXT_PUBLIC_API_URL     # set Railway URL
```

## Rollback

### Railway

```bash
railway deployment list                      # find previous SUCCESS deploy
railway redeploy --deployment=<deployment-id> # roll back to that deploy
```

Vercel:

- Go to Vercel Dashboard → Deployments → find the previous working deploy → ⋮ → Promote to Production

## Rollback (Render → Railway)

1. Vercel: set `NEXT_PUBLIC_API_URL` back to https://ethiobio-api-production.up.railway.app and redeploy.
2. Point the Telegram webhook back at Railway:

   ```bash
   curl "https://api.telegram.org/bot$TOKEN/setWebhook?url=https://ethiobio-api-production.up.railway.app/webhook&secret_token=$TELEGRAM_WEBHOOK_SECRET"
   ```

3. Pause the Render web service (Render → service → Pause) — keep the Render DB running
   so you can diff/recover any writes that landed on Render during the pilot.
4. If the Render DB received writes you need: pg_dump Render → restore into Railway's DB
   (see [Database Restore](#database-restore)) → `alembic upgrade head` → redeploy Railway.
5. Restore the keep-alive URL to the Railway `/health` and re-enable it.

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

### Bot is down

**Symptoms:** Telegram messages get no response; UptimeRobot reports bot endpoint down.

**Triage:**
```bash
railway logs --service ethiobio-api --limit 50    # check recent logs
curl https://ethiobio-api-production.up.railway.app/health
```

**Resolution:**
1. If the service is sleeping: wait 10-15s for cold start, UptimeRobot pings every 5 min
2. If crashed: `railway redeploy --yes`
3. If the token is revoked: update `TELEGRAM_BOT_TOKEN` in Railway env vars

### Database unreachable

**Symptoms:** `/health` returns `{"database": false}`; Tutor returns 500 errors.

**Triage:**
```bash
railway logs --service ethiobio-api --search "database|psycopg|connection" --limit 30
```

**Resolution:**
1. Check Railway Postgres status: `railway service postgres` → is it Online?
2. If Postgres is up but connection fails: verify `DATABASE_URL` has correct host/port/password
3. If Postgres is down: Railway restarts it automatically within a few minutes
4. Worst case: Railway Dashboard → Postgres → Restart
5. If data is lost: follow [Database Restore](#database-restore)

### Ollama Cloud rate-limited

**Symptoms:** Chat responses are empty or contain LLM errors; Sentry shows `429` or `rate_limit` errors.

**Triage:**
```bash
railway logs --service ethiobio-api --search "ollama|rate|429" --limit 20
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
1. If API proxy returns 502: backend is down — see [Bot is down](#bot-is-down)
2. If static assets 404: `vercel deploy --prod` to rebuild
3. If JS runtime error: check Vercel Build logs for TypeScript/Next.js errors
4. If CORS error in browser: verify `ALLOWED_ORIGINS` includes the Vercel domain

### Sentry alert triggered

**Symptoms:** Email/Slack notification from Sentry (error spike > 10/min, new error, LLM failure > 50%).

**Triage:**
1. Open Sentry → Issues → find the new error group
2. Check the stack trace and event context (request body, headers, user)
3. Correlate with Railway logs:
   ```bash
   railway logs --service ethiobio-api --search "<error-fingerprint>" --limit 20
   ```

**Resolution:**
1. New error: create a GitHub issue with Sentry permalink
2. Error spike: roll back to the last working deploy
3. LLM failure spike: check Ollama Cloud status at [status.ollama.ai](https://status.ollama.ai)
4. After fix: mark the Sentry issue as Resolved and deploy

## Backup Configuration

Automatic daily backups are handled by `.github/workflows/backup.yml`:

- **Schedule:** Daily at 02:00 UTC
- **Destination:** Backblaze B2 bucket `ethiobio-db-backups`
- **Retention:** 30 days (capped by B2 lifecycle rules)
- **Format:** compressed SQL dump with timestamp
- **Alert:** Workflow failure sends email to the GitHub owner

To run a manual backup:

```bash
pg_dump "$DATABASE_URL" | gzip | b2 upload-file ethiobio-db-backups - "manual_$(date +%F).sql.gz"
```

## Architecture References

| Component | Location                          | URL                                                            |
|-----------|-----------------------------------|----------------------------------------------------------------|
| API       | Railway — `ethiobio-api` service  | https://ethiobio-api-production.up.railway.app                 |
| Dashboard | Vercel — `ethiobio-ai-assistant`  | https://ethio-bio-ai-assistant.vercel.app                       |
| Bot       | Railway — runs in `ethiobio-api`  | Telegram: @EthioBioBot                                         |
| DB        | Railway — PostgreSQL + pgvector    | `DATABASE_URL` env var                                          |
| Cache     | Railway — Redis                    | `REDIS_URL` env var                                             |
| Monitor   | Sentry                             | https://sentry.io/organizations/ethiobio/                       |
| Backups   | Backblaze B2 — `ethiobio-db-backups` | https://backblaze.com/cloud_storage                           |
