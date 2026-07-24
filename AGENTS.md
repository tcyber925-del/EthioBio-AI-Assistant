# EthioBio AI Assistant — Agent Instructions

Obsidian PARA vault. Codebase at `1-Projects/p000-Active/EthioBio AI Assistant/`. `.env`, `.venv`, and all source files live there — NOT at root.

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
| CLI | `ethiobio` / `ethiobio-bot` | pyproject.toml `[project.scripts]` |

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
```

## Deployment

```bash
railway up                                       # deploy API+bot to Railway
vercel deploy --prod                              # deploy dashboard to Vercel
```

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
