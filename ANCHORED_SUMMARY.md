# Anchored Summary — PR #59 Bug Fixes & Docker Rebuild

PR #59 fixes complete. Telegram-bot rebuild pending (see Remaining section).

## Completed

### 1. PR #59 Code Review — 20+ Bugs Fixed (9 Rounds)
OpenCode review agent found bugs on GitHub PR #59; fixed iteratively push → review → fix → push → review until clean.

| Round | Commit | Fixes |
|-------|--------|-------|
| 1 | `68581f4` | Route shadowing, SQL boolean op, filter mutual exclusion, deprecated `utcnow()`, type annotation, blank-line style |
| 2 | `a3cc2e6` | Published-status guard, 404 on missing assignment, `is_active == True` consistency (3 locations), `data.status is not None` guard |
| 3 | `c62c861` | Trailing slash on route, `@model_validator` on `NewSubmission`, full UUID display, hide raw errors |
| 4 | `4aeb8c2` | `UniqueConstraint` + `index=True`, soft-delete guard, `str()` safety in consumer, `AsyncClient` timeout=30.0 |
| 5 | `825bc2e` | Due-date enforcement, `is_active == True` at 2 more locations, UUID validation in `submit_command` |
| 6 | `efb44e2` | Agent test names, FK indexes, soft-delete filter, trailing slash in bot URL, missing assertion |
| 7 | `b85f9a5` | `structlog>=24.4.0` dep, `import json` top-level (2 files), `Assignment.status` / `Submission.status` Literal types, `AssignmentStatus` param validation, soft-delete filter |
| 8 | `da31f5f` | `my_assignments` status type consistency |
| 9 | `c02b1a9` | Explicit `.join()`, response model `Literal` types |

Review confirmed "No remaining issues with clear, unambiguous diffs" (run 28811536183).

### 2. PR Merged + Docker Rebuild (Round 10 Bugfix)
- Squash-merged PR #59 into `main` (`dcc84e2`)
- App image rebuilt, container recreated with all fixes
- **Round 10**: Fixed pre-existing `redis.asyncio.Redis.xreadgroup` API mismatch (`group=` → `groupname=`, `consumer=` → `consumername=`) that surfaced after fresh build with redis-py 5.1.1

### 3. Verification
- Health endpoint responds: `{"status":"ok","ollama":true,"database":true}`
- App container healthy
- Bot container running (old image, not rebuilt due to Docker Hub/PyPI network timeouts)

## Remaining
- **Telegram-bot rebuild**: Blocked by Docker Hub/PyPI network timeouts. Old container runs 6+ hours with old bot code (is_active fixes, UUID validation missing).
- **Telegram-bot Dockerfile**: `pip install uv` step times out at ~11KB/s download speed. Needs local PyPI mirror or pre-cached wheel.
