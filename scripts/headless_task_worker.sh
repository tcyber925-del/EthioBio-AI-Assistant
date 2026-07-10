#!/usr/bin/env bash
# headless_task_worker.sh
# Usage: ./headless_task_worker.sh /full/path/to/worktree [task_dir]
# Picks one task file from the queue (file-per-task), runs it headlessly, appends to a headless log, and deletes the task.

set -euo pipefail

WORKTREE="${1:?worktree required (full path)}"
TASK_DIR="${2:-$(dirname "$WORKTREE")/../tasks/queue}"
LOCKFILE="/tmp/headless-task-lock"

mkdir -p "$TASK_DIR"
mkdir -p "$(dirname "$WORKTREE")/../" 2>/dev/null || true

(
  # acquire exclusive lock so multiple workers don't pick same file
  flock -n 9 || { echo "Another worker is running; exiting"; exit 0; }

  task=$(ls -1 "$TASK_DIR" 2>/dev/null | head -n1 || true)
  if [ -z "$task" ]; then
    echo "No tasks in $TASK_DIR"
    exit 0
  fi

  taskpath="$TASK_DIR/$task"
  echo "Picked task: $taskpath"

  # read prompt and run gemini headless
  prompt="$(cat "$taskpath")"

  # safe headless invocation; adapt flags for your gemini-cli version
  printf "%s\n" "$prompt" | gemini --headless 2>&1 | tee -a "$WORKTREE/../worktrees_headless.log"

  # remove task after success
  rm -f "$taskpath"
  echo "Completed and removed task: $task"
) 9>"$LOCKFILE"
