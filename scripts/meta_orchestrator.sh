#!/usr/bin/env bash
# meta_orchestrator.sh
# Interactive meta agent at repo root to inspect logs and run ad-hoc queries.

set -euo pipefail

# repo root inferred from script location
REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREES_DIR="$REPO/../worktrees"
LOG_DIR="$WORKTREES_DIR/logs"

echo "====== Meta Orchestrator ======"
echo "Repo: $REPO"
echo "Worktrees dir: $WORKTREES_DIR"
echo "Logs dir: $LOG_DIR"
echo

# show recent status of worktrees
printf "\nWorktree summary:\n"
for dir in "$WORKTREES_DIR"/*/ 2>/dev/null; do
  [ -d "$dir" ] || continue
  bname="$(basename "$dir")"
  printf " - %-30s " "$bname"
  if [ -d "$dir/.git" ]; then
    branch=$(git -C "$dir" branch --show-current 2>/dev/null || echo "(unknown)")
    printf "branch: %s\n" "$branch"
  else
    printf "NOT a worktree\n"
  fi
done

echo
echo "Recent agent logs (tail 3 lines each):"
for f in "$LOG_DIR"/*.log 2>/dev/null; do
  printf "\n---- %s ----\n" "$(basename "$f")"
  tail -n 3 "$f" || true
done

echo
echo "=== helper commands ==="
echo " - To inspect an agent worktree:  ls $WORKTREES_DIR/<branch>"
echo " - To tail a log:               tail -f $LOG_DIR/<branch>.log"
echo " - To run headless worker:      ./scripts/headless_task_worker.sh $WORKTREES_DIR/<branch>"
echo

echo "Dropping into interactive gemini at repo root. Use this interactive agent to coordinate/inspect."
exec gemini
