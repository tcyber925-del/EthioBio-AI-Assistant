#!/usr/bin/env bash
# run_gemini_agent.sh
set -Eeuo pipefail


BRANCH="${1:?branch required}"
WORKTREE="${2:?worktree required}"
LOGFILE="${3:?logfile required}"


# small debug header
printf "\n[run_gemini_agent] branch=%s worktree=%s logfile=%s\n" "$BRANCH" "$WORKTREE" "$LOGFILE"


if [ ! -d "$WORKTREE/.git" ]; then
echo "❌ ERROR: Not a git worktree: $WORKTREE"
exec bash
fi


cd "$WORKTREE"


echo "✅ PWD=$(pwd)"
echo "✅ git branch=$(git branch --show-current)"
echo "-------------------------------------------------"


# Keep interactive gemini; also record start time
printf "[agent start][%s] %s\n" "$BRANCH" "$(date -Iseconds)" >> "$LOGFILE"


# Run gemini, append to log and keep interactive
exec gemini 2>&1 | tee -a "$LOGFILE"