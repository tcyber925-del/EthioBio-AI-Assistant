# PR Review Loop

Automated PR review iteration loop. Reads CodeRabbit reviews, applies suggested diffs, pushes fixes, resolves threads, and merges — all from one command.

## Quick start

```bash
# On a branch ready for review:
pr-review-loop goal --every 10m
```

That's it. It creates the PR if missing, then loops until merged or blocked.

## Commands

| Command | Purpose |
|---------|---------|
| `goal --every N` | **Main command.** Polls every N min, auto-fixes, pushes, resolves, re-reviews. Stops when PR merges or stagnates. |
| `auto` | One-shot: apply CodeRabbit diffs, commit, push, trigger re-review, verify. |
| `push "message"` | Manual commit + push + auto-resolve threads on touched files. |
| `read` | Show PR status, review decision, unresolved threads. |
| `verify` | Check approval/merge status. |
| `watch` | Poll for new reviews every 30s (pre-goal). |

### Flags

| Flag | Applies to | Effect |
|------|-----------|--------|
| `-n N` | `auto` | Max iterations before giving up (default 3) |
| `--every N` | `goal` | Poll interval (`5m`, `30s`, `2h`). Default 5m |
| `--stagnation N` | `goal` | Max stagnant cycles before exiting. Default 5 |

## Slash commands (OpenCode TUI)

| Command | Equivalent |
|---------|-----------|
| `/pr-goal --every 10m` | `pr-review-loop goal --every 10m` |
| `/pr-auto` | `pr-review-loop auto` |
| `/pr-push "fix: ..."` | `pr-review-loop push "fix: ..."` |
| `/pr-read` | `pr-review-loop read` |
| `/pr-verify` | `pr-review-loop verify` |

## Terminal states

| Code | Name | Meaning |
|------|------|---------|
| 0 | `[success]` | PR merged or approved. All threads resolved. Done. |
| 1 | `[pending]` | Changes pushed, waiting for review. Continue the loop. |
| 2 | `[blocked]` | Stagnated or needs human intervention. Stop and check. |
| 3 | `[no-pr]` | No open PR on this branch. Create one first. |

## Architecture

```
goal ──→ discover ──→ auto ──→ gates ──→ commit ──→ push ──→ resolve ──→ re-review
  │        │         │        │                                        │
  │    [draft] [ci/fail] [gates fail]                                  │
  │        │         │        └──→ [blocked]                           │
  │        │         └──→ skip if CI failing                           │
  │        └──→ skip if draft                                          │
  │                                                                     │
  └───────────────────────── sleep & repeat ←── pending ─── verify ←───┘
                                  │
                             [success] or [blocked] ──→ exit
```

## Safety gates

| Gate | Phase | What it blocks |
|------|-------|---------------|
| **Review gate** | Pre-merge | Won't merge if 0 reviews exist (CodeRabbit or human hasn't looked yet) |
| **Draft gate** | Pre-`auto` | Skips `auto` entirely if PR is in draft mode |
| **Conflict gate** | Pre-`auto` | Exits `[blocked]` if PR has merge conflicts |
| **CI gate** | Pre-`auto` | Reports failing CI (continues, but warns) |
| **Verification gate** | Pre-commit | Runs `ruff check .` and `mypy src/` before allowing a commit. Skips commit if they fail and exits `[blocked]` |

## Persistent state

The loop writes `.pr-loop-state.json` in the project root after every cycle:

```json
{
  "cycle": 5,
  "last_exit_code": 1,
  "last_run": "2026-06-22T14:07:35+00:00",
  "last_thread_count": 3,
  "terminal": "pending"
}
```

This survives machine restarts and provides an audit trail. `goal` references it for progress tracking across sessions.

## Discover phase

At the start of each cycle, `goal` runs a discover check and reports:

```
Status: OPEN | Draft: no | CI: success | Mergeable: clean | Threads: 3
```

- **Draft**: skips the cycle if PR is still a draft
- **CI**: reports passing/failing/running status from latest workflow run
- **Mergeable**: detects merge conflicts before attempting auto-fix
- **Threads**: unresolved review thread count (existing)

## Verification gates (maker-checker split)

Before committing auto-fixes, the loop runs:

1. `ruff check .` — lint pass (if ruff and a config file exist)
2. `mypy src/` — type check pass (if mypy and `src/` exist)

If either fails, the commit is **skipped** and the loop exits `[blocked]` with the failure output. This is the deterministic "checker" gate — the same agent that wrote the fix cannot bypass it.

## Files

| File | Role |
|------|------|
| `pr-review-loop.sh` | Main script |
| `apply_fixes.py` | Extracts CodeRabbit ` ```diff ` blocks and applies them |
| `read_threads.py` | Formats unresolved threads for display |
| `resolve_touched.py` | Finds threads to auto-resolve by changed files |
| `.pr-loop-state.json` | Persistent state file (created at project root) |

## How auto-fix works

1. Fetch unresolved review threads via GraphQL
2. Skip analysis-chain threads (`🏁 Script executed`, `Analysis chain`)
3. Extract ` ```diff ` blocks from remaining threads
4. Parse `-`/`+` lines, find-and-replace in source files
5. If multiple diffs reference the same file, apply all before writing
6. Resolve the thread via GraphQL `resolveReviewThread` mutation
7. Run verification gates (ruff + mypy)
8. Commit, push, comment `@coderabbitai review` to trigger re-review

## Stagnation detection

`goal` tracks unresolved thread count across cycles. If the count stays the same for `--stagnation N` consecutive cycles (no diffs applied, no threads resolved), it exits `[blocked]`. Prevents infinite loops on unactionable feedback. Cycles where no reviews exist yet (first review pending) do not count toward stagnation.

## Requirements

- `gh` CLI authenticated
- `python3`
- Git branch with unpushed commits (or `goal` creates the PR)

## Installation

```bash
ln -sf "$PWD/scripts/pr-auto-loop/pr-review-loop.sh" ~/.local/bin/pr-review-loop
```
