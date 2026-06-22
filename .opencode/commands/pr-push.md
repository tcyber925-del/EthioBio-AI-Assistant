---
description: Commit changes, push, and resolve review threads
---
Commit uncommitted changes and push to the PR branch, auto-resolve threads on touched files, then verify.

`!bash scripts/pr-auto-loop/pr-review-loop.sh push "$ARGUMENTS" 2>&1 || echo "Script failed"`

Summarize what was pushed and the current terminal state.
