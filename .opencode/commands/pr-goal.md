---
description: Run PR review loop until merged or blocked
---
Run the PR review goal loop: polls on an interval, auto-applies CodeRabbit suggested diffs, pushes, triggers re-review, and continues until the PR is merged or stagnation is detected.

`!bash scripts/pr-auto-loop/pr-review-loop.sh goal $ARGUMENTS 2>&1 || echo "Script failed"`

Summarize current state, how many cycles ran, and the terminal state reached.
