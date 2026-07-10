#!/usr/bin/env bash
# ci_push_agent.sh
# Usage: scripts/ci_push_agent.sh /full/path/to/worktree "Commit message" pr/branch-name
# Requires: gh CLI installed and authenticated.

set -euo pipefail

WT="${1:?worktree required}"
MSG="${2:-AI: suggested changes}"
PRBRANCH="${3:-ai/auto-changes-$(date +%s)}"

cd "$WT"

# safety: ensure not detached HEAD
CUR=$(git rev-parse --abbrev-ref HEAD)
if [ "$CUR" = "HEAD" ]; then
  echo "Refusing to operate on detached HEAD in $WT"
  exit 1
fi

# stage only tracked changes + created files, but be conservative
git add -A

if git diff --cached --quiet; then
  echo "No staged changes; nothing to push"
  exit 0
fi

git commit -m "$MSG"

# push to new branch and open PR
git push origin HEAD:refs/heads/$PRBRANCH

# create PR (target base is the original branch we were on)
gh pr create --title "$MSG" --body "Auto-generated changes from agent on branch $CUR" --base "$CUR" --head "$PRBRANCH"
