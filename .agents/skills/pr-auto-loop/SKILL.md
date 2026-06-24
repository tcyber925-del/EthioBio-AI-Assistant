---
name: pr-auto-loop
description: >
  Automated PR review iteration loop using gh CLI. Reads CodeRabbit reviews,
  applies suggested diffs, pushes fixes, resolves threads, and merges.
  Use when working on PRs, responding to CodeRabbit reviews, automating
  review-to-merge workflow, or when user asks about PR status/fixes/merging.
---

# PR Auto Loop

## Quick start

```
pr-review-loop goal --every 10m
```

Creates PR if missing, then polls and auto-fixes until merge or blocked.

## Command dispatch

| When user says... | Run this first |
|-------------------|----------------|
| "check PR", "what's the status", "review this PR" | `pr-review-loop read` |
| "apply fixes", "fix the PR", "address CodeRabbit" | `pr-review-loop auto` |
| "push changes", "commit and push" | `pr-review-loop push "msg..."` |
| "can we merge?", "ready to merge?" | `pr-review-loop verify` |
| "watch this PR", "keep fixing", "merge when ready" | `pr-review-loop goal --every 10m` |

Always start with `read` unless user explicitly asks for auto/goal.

## Terminal state dispatch

After any command, inspect exit code and output:

| Exit | State | Next action |
|------|-------|-------------|
| 0 | `[success]` | Tell user. PR merged or fully approved. |
| 1 | `[pending]` | Tell user. Run `goal --every 10m` if they want auto-wait. |
| 2 | `[blocked]` | Inspect output for cause. Report to user. |
| 3 | `[no-pr]` | Create PR with `gh pr create --fill`, then re-run. |

## Diagnostics

Check `.pr-loop-state.json` (created at project root by `auto`/`goal`):

```json
{
  "cycle": 5,
  "last_exit_code": 1,
  "last_run": "2026-06-22T14:07:35+00:00",
  "last_thread_count": 3,
  "terminal": "pending"
}
```

Look for these keywords in script output:
- `VERIFICATION_FAILED` — ruff or mypy rejected auto-fix. Manual fix needed.
- `STAGNATION` — threads not decreasing. Unactionable or bad suggestions.
- `MERGE_CONFLICT` — manual conflict resolution needed.
- `DRAFT` — PR not ready for review yet.

## Gotchas

- GitHub blocks self-approval — `gh pr review --approve` fails on own PR
- CodeRabbit posts `COMMENTED` reviews, never `APPROVED` — `reviewDecision` stays empty when only CR has reviewed
- CodeRabbit analysis-chain threads (`🏁 Script executed`) are unactionable but counted as unresolved — script filters them
- Review threads do NOT auto-resolve on push — script uses GraphQL `resolveReviewThread`
- 0 threads + 0 reviews = "waiting for first review" (pending), not "ready to merge"
