---
description: Show PR review status and unresolved threads
---
Show the current PR review status for this branch.

`!bash scripts/pr-auto-loop/pr-review-loop.sh read 2>&1 || echo "No PR or script failed"`

Then summarize the current state and suggest the next action.
