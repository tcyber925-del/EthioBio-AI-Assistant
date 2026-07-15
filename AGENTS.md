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
| API server | `python -m src.main` (FastAPI :8000) | uvicorn |
| Telegram bot | `python -m src.telegram.bot` | PTB polling |
| Full stack | `docker compose up --build` | app + bot + postgres + redis + ollama + dashboard |
| CLI | `ethiobio` / `ethiobio-bot` | pyproject.toml `[project.scripts]` |

## Commands

```bash
python -m src.main                               # API :8000
python -m src.telegram.bot                       # bot (separate terminal)
pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"
ruff check . && mypy src/                         # lint + typecheck
docker compose up -d postgres redis               # infra
curl http://localhost:8000/models                  # list models
curl -X POST http://localhost:8000/models/refresh  # refresh Ollama cache
```

## Tooling

| Tool | Config |
|------|--------|
| Ruff | `line-length=100`, `select=E,F,I,N,W` |
| Mypy | `strict=false`, `ignore_missing_imports=true` |
| Python | 3.12+, async everywhere (asyncpg, httpx) |
| Providers | Ollama (primary), OpenAI, Anthropic, OpenAI-compatible (LM Studio, vLLM) |

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
2. **Telegram 4096-char limit** — use `_reply_long()` at `bot.py:313` to split.
3. **`send_email()` silently returns False** — check return value when `email_host` is unset.
4. **`requires_planning` from subtasks, NOT intent** — OrchestratorNode derives from `subtasks` count.
5. **Weak topic detection order** — wire AFTER gamification, BEFORE `session.commit()`.

## Maintenance

This file is kept under ~120 lines. When adding a module, create a file in `.opencode/rules/` and add one row to the Module Index. When fixing a recurring mistake, add a gotcha with `<!-- retire_when: observable -->`. Every quarter, ask an agent to audit: remove stale rules, verify commands run, confirm linked files exist.

## References

- `README.md` — API endpoints, full setup guide
- `.env.example` — all env vars
- `docker-compose.yml` — service topology (postgres+pgvector, redis, ollama with GPU)
- `scripts/Git-Worktree/README.md` — `gt` worktree orchestrator docs
- `~/.opencode/skills/gt/SKILL.md` — `gt` agent skill (auto-loaded for worktree tasks)

## Agent skills

### Issue tracker

Issues are tracked on GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Issues use the five canonical triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout. See `docs/agents/domain.md`.
