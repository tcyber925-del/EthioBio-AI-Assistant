---
description: Check PR approval and merge status
---
Check whether the current PR is approved, has unresolved threads, or can be merged.

`!bash scripts/pr-auto-loop/pr-review-loop.sh verify 2>&1 || echo "Script failed"`

Report the terminal state and suggest next action.
