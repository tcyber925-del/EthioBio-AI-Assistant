# EthioSci — Agent Instructions

Obsidian PARA vault. Codebase at `1-Projects/p000-Active/EthioBio AI Assistant/`. `.env`, `.venv`, and all source files live there — NOT at root.

## Naming & Brand

The product is **EthioSci** — a multi-subject
science learning and teaching assistant covering **biology, chemistry, physics, and
mathematics** for Ethiopian Grades 7–12. It was renamed from "EthioBio" (biology-only)
to "EthioSci" (multi-subject); the rename kept several infrastructure identifiers as
`ethiobio_*` for backward compatibility.

- **Product / brand name:** `EthioSci` (use "science learning assistant" only in
  descriptive copy, not in the name). Use "science" as the
  generic subject term ("science Q&A", "science tutor"). Subjects are biology, chemistry,
  physics, mathematics.
- **Retained `ethiobio_*` infrastructure identifiers (do NOT rename):** Render service &
  domain `ethiobio-api.onrender.com`; GHCR image `ghcr.io/tcyber925-del/ethiobio-ai-assistant`;
  Postgres service/db `ethiobio-pg` with `COLLECTION_NAME=ethiobio_curriculum`; Redis
  `ethiobio-kv`; LangSmith project `ethiobio` and datasets `ethiobio-curriculum` /
  `ethiobio-adversarial` / `ethiobio-gold`; `email_from=noreply@ethiobio.com`; Telegram
  bot `t.me/ethiobio_bot`; localStorage `ethiobio_active_workspace_id`; Grafana default
  `admin/ethiobio`; historical/archive docs.
- **Bio textbooks:** the `data/textbooks/Biology/` corpus and any "Biology" domain-specific
  references (legacy biology corpus, biology-only features) stay as-is — they are
  subject-specific, not the product name.

## Pipeline

```
orchestrator → _route_after_orchestrator
    ├── "planner" → plan_executor → evidence_graph → sufficient_context
    │     └── route_after_sufficiency: "synthesis" / "rewrite" / "replan"
    ├── "retrieve" → tutor
    └── "skip_retrieval" → tutor

tutor → hallucination → claim_verifier → route_after_verification
    ├── "finalize" → safety → END
    ├── "revise" → tutor (max 2) ───┐
    └── "reject" → safety → END     │
         safety ←───────────────────┘
```

## Entrypoints

| What | How | Process |
|------|-----|---------|
| API server | `python -m src.main` (FastAPI :8000) | uvicorn, includes bot webhook |
| Telegram bot | `python -m src.telegram.bot` | PTB polling (or webhook via API) |
| Full stack | `docker compose up --build` | app + bot + postgres + redis + ollama + cron + jaeger + prometheus + grafana + dashboard |
| CLI | `ethiosci` / `ethiosci-bot` / `ethiosci-langsmith` | pyproject.toml `[project.scripts]` |

## Commands

```bash
python -m src.main                               # API :8000 (+ bot webhook)
python -m src.telegram.bot                       # bot (separate terminal, polling)
pytest tests/ -v -k "not slow"                   # unit tests (skip slow endpoint tests)
ruff check . && mypy src/                         # lint + typecheck
pre-commit run --all-files                       # pre-commit hooks
docker compose up -d postgres redis               # infra
curl http://localhost:8000/models                  # list models
curl -X POST http://localhost:8000/models/refresh  # refresh Ollama cache
curl http://localhost:8000/health                  # health check
curl http://localhost:8000/readiness               # readiness check
LANGSMITH_API_KEY=... scripts/langsmith/verify_tracing.sh   # verify LangSmith traces (needs langsmith CLI)
```

## Deployment

```bash
git push origin main                     # build GHCR image + deploy API+bot to Render (deploy hook)
npx render blueprint:deploy render.yaml  # (re)provision Postgres/Redis/web/cron resources
npx render services list                 # check status
vercel deploy --prod                     # deploy dashboard to Vercel
```

Scheduled jobs (reminders, digests) run as Render cron jobs in
`render.yaml`; the LangSmith eval runs as the weekly GitHub Actions
workflow `.github/workflows/evaluate.yml` (Render cron needs a paid plan,
and GitHub runners can't reach the allowlisted Postgres — the workflow
triggers `/admin/langsmith-eval`, which runs in-process).

## Tooling

| Tool | Config |
|------|--------|
| Ruff | `line-length=100`, `select=E,F,I,N,W,B,C4,PT,S` |
| Mypy | `strict=false`, `ignore_missing_imports=true` |
| Python | 3.12+, async everywhere (asyncpg, httpx) |
| Providers | Ollama (primary), OpenRouter, OpenAI, Anthropic, OpenAI-compatible (LM Studio, vLLM) |
| Testing | pytest, pytest-asyncio (module-scoped), pytest-cov (50% floor) |
| CI/CD | GitHub Actions: lint+typecheck, tests (-m "not slow"), security (pip-audit+bandit) |
| Pre-commit | ruff lint+format, trailing-whitespace, EOF fixer, check-yaml, check-added-large-files |

## Module Index

Read the relevant file before working in that area:

| File | Read when |
|------|-----------|
| `.opencode/rules/architecture.md` | Pipeline, graph nodes, evidence/planning, key abstractions |
| `.opencode/rules/modules.md` | Gamification, export, notifications, recovery, Ralph PRD |
| `.opencode/rules/adaptive-intel.md` | Adaptive quiz, question attempts, student ability, recommendations |
| `.opencode/rules/gotchas.md` | Debugging, unfamiliar modules, unexpected behavior |
| `.opencode/rules/ingestion.md` | PDF ingestion, OCR, vector store |
| `.opencode/rules/testing.md` | Test commands, mocking patterns, test architecture |
| `src/evaluation/langsmith/` | LangSmith datasets, offline eval CLI (`ethiosci-langsmith`), online feedback posting |
| `src/observability/langsmith.py` | LangSmith client setup, sampling, run-id capture, feedback |

## Cross-Cutting Gotchas

1. **`topic` filter returns empty** — PDF chunks lack `topic` metadata. Use `grade_level` only.
2. **Telegram 4096-char limit** — use `_reply_long()` at `bot.py:1416` to split.
3. **`send_email()` silently returns False** — check return value when `email_host` is unset.
4. **`requires_planning` from subtasks, NOT intent** — OrchestratorNode derives from `subtasks` count.
5. **Weak topic detection order** — wire AFTER gamification, BEFORE `session.commit()`.
6. **SECRET_KEY / JWT_SECRET defaults are fatal** — `guardrails/startup.py` calls `SystemExit` if defaults are unchanged.
7. **Rate limiting disabled in tests** — conftest sets `rate_limit_enabled=False` via Settings override.
8. **Chat/lesson-plan 500 without LLM** — these require running Ollama; marked `@pytest.mark.slow` and excluded from CI.
9. **Redis lazy connection** — `redis_client.py` creates connection on first use; tests use `rate_limit_enabled=False` so Redis is optional.
10. **Graph nodes use structlog, not stdlib logging** — switching `import logging` to `import structlog` in graph node files fixed 7 previously-failing agentic e2e tests.
11. **Depends captures function objects at import time** — `patch.object` on a function used with `Depends()` is a no-op; use `app.dependency_overrides` instead.
12. **Telegram mock must signal `TokenChunk(done=True)`** — test mocks for `run_graph` must put `TokenChunk(delta="", node="tutor", done=True)` into `token_queue` to break the `_stream_and_edit` loop.
13. **Never default STT language to `"am"`** — force Amharic even for English speakers. Default to `None`/`""` (auto-detect), then `result.language or "en"`. Whisper reports full names (`"english"`, `"amharic"`); use `normalize_language_code()` (`src/voice/providers/types.py`) before comparing to `LanguageEnum`. **Addis carve-out:** addis-whisper has no auto-detect (400 without `language_code`), so `AddisProvider.transcribe` sends the universal `"am"` hint when language is unknown — verified live that Amharic returns Ethiopic script and English returns correct English, and the result is tagged via `detect_transcript_language()` script sniffing. The `"en"` hint romanizes Amharic and must never be the default. <!-- retire_when: observable -->
14. **Never pass `None`/`"both"`/arbitrary codes as TTS language** — Gemini auto-detects the text's language and will speak any language; edge-tts/Azure silently fall back to English voices. `SpeechProviderRegistry.synthesize()` clamps every call to `"am"`/`"en"` via `resolve_tts_language()` (`src/voice/providers/types.py`, Ethiopic-script sniff for `both`). Don't call providers directly with a raw language; don't bypass the registry. <!-- retire_when: observable -->

## Maintenance

This file is kept under ~120 lines. When adding a module, create a file in `.opencode/rules/` and add one row to the Module Index. When fixing a recurring mistake, add a gotcha with `<!-- retire_when: observable -->`. Every quarter, ask an agent to audit: remove stale rules, verify commands run, confirm linked files exist.

## References

- `README.md` — API endpoints, full setup guide
- `.env.example` — all env vars (80+)
- `docker-compose.yml` — service topology (postgres+pgvector, redis, ollama, jaeger, prometheus, grafana)
- `docs/runbook.md` — Deployment, rollback, backup, incident response
- `scripts/Git-Worktree/README.md` — `gt` worktree orchestrator docs
- `~/.opencode/skills/gt/SKILL.md` — `gt` agent skill (auto-loaded for worktree tasks)

## Agent skills

### Issue tracker

Issues are tracked on GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Issues use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.
