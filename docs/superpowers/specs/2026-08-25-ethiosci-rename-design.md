# EthioBio → EthioSci Rename + Multi-Subject Expansion — Design

**Date:** 2026-08-25
**Status:** Approved

## Problem

The project is named "EthioBio AI Assistant" and is hard-scoped to biology: prompts,
guardrail keyword lists, i18n strings, and ingestion layout all assume biology. We are
expanding to other Ethiopian secondary science subjects (Physics, Chemistry, Mathematics;
Biology stays) and renaming to **EthioSci**.

## Decisions

| Decision | Choice |
|----------|--------|
| New name | EthioSci (`ethiosci`) |
| Rename depth | Code + docker-compose + local defaults; **prod names kept** (Render services/domain, GHCR image, prod DB user/db, `COLLECTION_NAME=ethiobio_curriculum`, LangSmith project `ethiobio` + dataset `ethiobio-curriculum`, backup filenames, Railway service in ci.yml, `email_from=noreply@ethiobio.com`) |
| Subject scope | Multi-subject ready + ingest Physics/Chemistry/Math when PDFs arrive |
| Subjects | Physics, Chemistry, Math (+ existing Biology) |
| Approach | Combined core phase (rename + de-biology + subject feature together in `src/`), then mechanical infra/docs sweep, then data ingestion |

## Architecture

### Subject as metadata (no Alembic migration)

Chunk metadata is stored as JSONB; we add a `"subject"` key with read-time default
`"biology"` for legacy chunks.

- Ingestion canonical layout: `data/textbooks/<Subject>/Grade{N}/*.pdf`
  (e.g. `data/textbooks/Chemistry/Grade10/`). Legacy `Grade{N}/` dirs auto-tag
  `"subject": "biology"`. Existing PDFs move under `data/textbooks/Biology/`.
- `RetrievalFilter` gains optional `subject`; BM25 + pgvector paths filter on it.
- No orchestrator change required initially: subject is optional; `None` searches all.

### Prompt generalization

All agent/system prompts drop the "biology" scope restriction ("AI science tutor …
physics, chemistry, biology, mathematics"), identity lines become "EthioSci …".
Affected: tutor (graph + agent), safety, orchestrator intent classifier, claim verifier,
quiz, lesson planner, diagnostic assessment, recovery, unit planner, translator,
diagram-tutor integration.

### Guardrails

- `ETHIOBIO_TOPICS` → `SCIENCE_TOPICS`, expanded with physics/chemistry/math keywords.
- Tool name `search_biology_topic` → `search_science_topic`.

### Kept deliberately as `ethiobio`

Render resource names + `ethiobio-api.onrender.com`, GHCR image
(`ghcr.io/tcyber925-del/ethiobio-ai-assistant`, derives from repo name — repo rename out
of scope), prod DB user/db via render.yaml, pgvector collection name default in prod env,
LangSmith project/dataset, backup filenames in `.github/workflows/backup.yml`,
Railway service name in ci.yml, `email_from` domain (we do not own ethiosci.com),
historical docs (PRDs, plans, specs, ADRs, wiki).

## Phases

1. **Core** (`src/` + tests): subject metadata feature + prompt de-biology + rename +
   guardrails, one logical change.
2. **Mechanical sweep**: compose containers/PG defaults, `.env.example`, pyproject package
   + CLI scripts (`ethiosci`, `ethiosci-bot`, `ethiosci-langsmith`), grafana/prometheus,
   Telegram i18n, dashboard copy, notification templates, forward-looking docs
   (AGENTS.md, README, runbook, `.opencode/rules/*`).
3. **Data**: ingest Physics/Chemistry/Math PDFs into `<Subject>/Grade{N}/` when provided;
   per-subject retrieval sanity queries.

## Verification

- Per phase: `ruff check . && mypy src/ && pytest tests/ -v -k "not slow"`
- Grep audit gate: only deliberate matches for `ethiobio|biology` remain in
  `src/ tests/ dashboard/src` (e.g. subject value `"biology"`, kept prod identifiers).
- After Phase 2: `pre-commit run --all-files`.
- Local compose smoke test (one-time local PG volume recreate due to renamed defaults).
- Nothing deploys to prod as part of this work.

## Non-goals

GitHub repo rename, Render resource/domain renames, GHCR image rename, LangSmith project
rename, email domain change, per-subject Amharic terminology review (future), new-subject
LangSmith eval datasets (future).
