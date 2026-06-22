---
description: Auto-apply review suggested diffs, push, and verify
---
Run the PR review auto-fix loop: apply CodeRabbit suggested diffs, resolve threads, commit, push, trigger re-review, and verify.

`!bash scripts/pr-auto-loop/pr-review-loop.sh auto $ARGUMENTS 2>&1 || echo "Script failed"`

Summarize what was applied, skipped, and the current terminal state.
