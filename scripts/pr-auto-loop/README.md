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
goal ──→ poll ──→ auto ──→ apply diffs ──→ commit ──→ push ──→ resolve ──→ re-review
  │                                                                              │
  └────────────────────────── sleep & repeat ←── pending ─── verify ←────────────┘
                                  │
                             [success] or [blocked] ──→ exit
```

## Files

| File | Role |
|------|------|
| `pr-review-loop.sh` | Main script |
| `apply_fixes.py` | Extracts CodeRabbit ` ```diff ` blocks and applies them |
| `read_threads.py` | Formats unresolved threads for display |
| `resolve_touched.py` | Finds threads to auto-resolve by changed files |

## How auto-fix works

1. Fetch unresolved review threads via GraphQL
2. Skip analysis-chain threads (`🏁 Script executed`, `Analysis chain`)
3. Extract ` ```diff ` blocks from remaining threads
4. Parse `-`/`+` lines, find-and-replace in source files
5. If multiple diffs reference the same file, apply all before writing
6. Resolve the thread via GraphQL `resolveReviewThread` mutation
7. Commit, push, comment `@coderabbitai review` to trigger re-review

## Stagnation detection

`goal` tracks unresolved thread count across cycles. If the count stays the same for `--stagnation N` consecutive cycles (no diffs applied, no threads resolved), it exits `[blocked]`. Prevents infinite loops on unactionable feedback.

## Requirements

- `gh` CLI authenticated
- `python3`
- Git branch with unpushed commits (or `goal` creates the PR)

## Installation

```bash
ln -sf "$PWD/scripts/pr-auto-loop/pr-review-loop.sh" ~/.local/bin/pr-review-loop
```
