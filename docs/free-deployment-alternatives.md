# Free Deployment Alternatives to Railway (Aug 2026)

Research into free-tier platforms for hosting a containerized backend (Python/FastAPI) with PostgreSQL.
Facts are sourced from the platforms' own pricing pages and docs (links inline). Anything unverifiable from
an official source is marked **UNVERIFIED**.

## Quick verdict

| Need | Pick |
|---|---|
| Best overall (proven, generous forever-free, easiest DX) | **Render** |
| Best for a persistent REST API + free *managed* Postgres on one platform | **Northflank** (Sandbox: 1 free service + 1 free DB, always-on) |
| Best scale-to-zero / pay-as-you-grow serverless | **Koyeb** |
| Dumpy demo only (no custom domain, sleeps, no DB) | **Hugging Face Spaces** |
| Pay-after-trial "real" platform, closest to Railway’s model | **Fly.io** (no free tier since 2024) |

---

## Comparison matrix

| | Render | Koyeb | Northflank | Hugging Face Spaces | Google Cloud Run | Fly.io | Oracle Always Free |
|---|---|---|---|---|---|---|---|
| **Free compute** | Forever: 750 free-hrs/mo, 512MB/0.1CPU web service | Forever: free web service 512MB/0.1vCPU | Sandbox: 2 services, always-on | CPU Basic 2vCPU/16GB (per Space, sleeps) | None (free tier is usage allowance on paid account) | None — trial only | Always Free ARM VM 4 OCPU/24GB |
| **Free managed Postgres** | Yes — **30-day expiry**, 1GB | Yes — **5 hrs active/mo**, 1GB | Yes — free DB addon (size UNVERIFIED) | No | No (Cloud SQL paid) | No (managed PG from $38/mo) | No managed PG (run your own) |
| **Custom domain** | 2 free, TLS | 10 free (Pro), free tier limited | Free, TLS | **Pro only** | Yes (free mapping via GCP) | Yes | Yes (bring your own) |
| **Docker/Dockerfile** | Yes | Yes | Yes | Yes (Docker Spaces) | Yes (container-native) | Yes (CLI) | Only via VM |
| **Deploy method** | Git push | Git push / API / CLI | Git push / CLI | Git push | `gcloud` / Docker | `flyctl` CLI | VM + config |
| **Sleep/cold-start** | Sleeps 15min idle, ~1min wake | Scale-to-zero | none — always on | Sleeps after 48h idle; 30–90s cold start | Scales to zero; cold start | Autostop opt-in | N/A (VM) |
| **Post-free pricing (cheapest)** | Starter $7/mo; Postgres $6/mo | Pay-as-you-go from ~$1.61/mo (Eco) | PAYG from ~$2.70/mo (0.1CPU/256MB) | PRO $9/mo (mostly ML features) | pay-as-you-go per sec | ~$2.02/mo machine | PAYG per-OCPU/hr |
| **Card required for free** | No | No | No | No | Yes (billing-enabled account) | Yes | Yes (holds) |
| **Good fit** | REST API + DB (short-lived) | Serverless REST, scale-to-zero | Small always-on REST + PG | Demo/ML only | Serious containerized API | prod-grade always-on | compute-heavy (run own Docker) |

### Notes on the matrix

- **Render**: 2026 plan change (Apr 23) cut legacy Hobby bandwidth from 100GB→**5GB/mo** and capped services at 25.
  Free Postgres now expires after **30 days** (was 90). Free KV (Redis-lite) is 25MB/50 conns/in-memory.
  — https://render.com/docs/free, https://render.com/pricing, https://www.render.com/docs/new-workspace-plans
- **Koyeb**: acquired by **Mistral AI** (Feb 2026) — future free tier stability is an open question (their own
  FAQ promises a "forever free" and is still live). Free Postgres is capped at **5 h of active time/month** —
  effectively unusable for a real API; pair the free web service with Neon/Supabase free PG instead.
  — https://www.koyeb.com/docs/faqs/pricing, https://www.koyeb.com/pricing
- **Northflank**: Sandbox tier explicitly advertises "always-on compute – no sleeping" with 2 free services,
  1 free database, 2 free cron jobs. All plans include free SSL/custom domains and Postgres/MySQL/Redis addons.
  — https://northflank.com/pricing
- **Hugging Face Spaces**: not a general host. Ephemeral disk wiped on restart, sleep after 48h, no
  custom domain for free, loads on port 7860. Docker Spaces can serve an arbitrary FastAPI but it is not a
  production backend. — https://huggingface.co/pricing, https://huggingface.co/docs/hub/spaces-gpus
- **Cloud Run**: "always free" only applies to a billing-enabled GCP account (card needed). Free tier on request
  billing: 2M requests/mo, CPU 180k vCPU-sec, RAM 360k GiB-sec. No free managed Postgres — pair with Neon
  (1 pool ~512MB, sleep) or Supabase free tier. Scales to zero (cold starts on traffic). Paired with a free
  Postgres and occasional traffic it can be $0/mo forever. — https://cloud.google.com/run/pricing, https://cloud.google.com/free
- **Fly.io**: no free tier for new customers (removed ~Oct 2024). Trial only; smallest machine ≈ **$2.02/mo**+egress;
  managed Postgres from $38/mo. Egress e.g. NA $0.02/GB, Africa $0.12/GB. Not a "free alternative" — include
  for the Railway-style dev-experience, pay-as-you-go model. — https://fly.io/docs/about/pricing
- **Oracle Always Free**: strongest pure compute (4 OCPU / 24GB ARM Ampere VM), but it's a VM you fully manage
  (no app platform), no managed PG, card required, and idle accounts (30 days) get suspended. Best solo when
  you want a private self-hosted PG + app. — https://www.oracle.com/cloud/free/

---

## Verdict

### Best overall: Render
- The most proven "Heroku-like" PaaS with a genuinely **forever-free, unlimited-hours web service** (750h/mo ≈ light
  wink; only one free web service consumes all the hours). Great DX (git push), both native Python and Docker,
  free custom domains/TLS, no credit card.
- Caveats: free Postgres **expires after 30 days** (1GB) and free web services **sleep on 15min idle** (~1min wake).
  **If you need a persistent free Postgres on Render, pair the free web service with a free Neon/Supabase PG**
  or budget $12/mo for committed Postgres (Basic-256mb).

### Best for a REST API + PostgreSQL (fully self-contained, free forever)
**Northflank Sandbox**:
- free 1 service + 1 database, always-on (no sleeping → good for a Telegram/API bot), managed PG/MySQL/Redis,
  free DNS/TLS, no card.
- Caveat: compute is "Limited" (Sandbox is intended for testing), DB size per-account limits **UNVERIFIED**, and
  a sustained real traffic user will upgrade to PAYG (~$2–5/mo).
- If 1 free service + 1 free DB + no sleeps is the fit, this is the closest thing to a self-contained free
  Railway.

**Close second (better DX, hit the DB-upgrade): Render** — free web service forever + Neon/Supabase free PG
(Supabase 500MB, Neon 512MB) keeps the whole API stack at $0. Render remains the sane default if you want
a platform that will grow with you.

---

## Sources (primary)

- Render pricing/docs: https://render.com/pricing · https://docs.render.com/free · https://www.render.com/docs/new-workspace-plans
- Koyeb pricing/FAQ: https://www.koyeb.com/pricing · https://www.koyeb.com/docs/faqs/pricing
- Northflank: https://northflank.com/pricing https://northflank.com/docs
- Hugging Face: https://huggingface.co/pricing · https://huggingface.co/docs/hub/spaces-gpus
- Cloud Run: https://cloud.google.com/run/pricing · https://cloud.google.com/run/docs
- Fly.io: https://fly.io/docs/about/pricing · https://fly.io/docs/about/billing
- Oracle: https://www.oracle.com/cloud/free/