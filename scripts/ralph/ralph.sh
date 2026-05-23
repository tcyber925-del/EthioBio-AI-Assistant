#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop for OpenCode
# Usage: ./ralph.sh [max_iterations]

set -euo pipefail

MAX_ITERATIONS=10

if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  MAX_ITERATIONS="$1"
  shift
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"
TASK_PRD_FILE="$SCRIPT_DIR/tasks/PRD-socratic-tutor-mode.md"
REQUIRED_STORY_IDS=()

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: Required command '$command_name' is not installed or not on PATH." >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"

  if [ ! -f "$file_path" ]; then
    echo "Error: Required file not found: $file_path" >&2
    exit 1
  fi
}

load_required_story_ids() {
  if [ -f "$TASK_PRD_FILE" ]; then
    mapfile -t REQUIRED_STORY_IDS < <(grep -oE 'ST-[0-9]+' "$TASK_PRD_FILE" | awk '!seen[$0]++')
  fi
}

validate_prd() {
  local parsed_ids
  local expected_id

  if ! jq empty "$PRD_FILE" >/dev/null 2>&1; then
    echo "Error: $PRD_FILE is not valid JSON." >&2
    exit 1
  fi

  if ! jq -e '.title | strings | length > 0' "$PRD_FILE" >/dev/null 2>&1; then
    echo "Error: $PRD_FILE is missing a non-empty title." >&2
    exit 1
  fi

  if ! jq -e '.branchName | strings | length > 0' "$PRD_FILE" >/dev/null 2>&1; then
    echo "Error: $PRD_FILE is missing a non-empty branchName." >&2
    exit 1
  fi

  if ! jq -e '.userStories | arrays | length > 0' "$PRD_FILE" >/dev/null 2>&1; then
    echo "Error: $PRD_FILE must contain at least one user story." >&2
    exit 1
  fi

  if ! jq -e 'all(.userStories[]; (.id | type == "string" and length > 0) and (.title | type == "string" and length > 0) and (.passes | type == "boolean"))' "$PRD_FILE" >/dev/null 2>&1; then
    echo "Error: Every user story in $PRD_FILE must have non-empty id/title fields and a boolean passes field." >&2
    exit 1
  fi

  if [ "$(jq -r '.userStories | map(.id) | length' "$PRD_FILE")" != "$(jq -r '.userStories | map(.id) | unique | length' "$PRD_FILE")" ]; then
    echo "Error: $PRD_FILE contains duplicate story IDs." >&2
    exit 1
  fi

  if [ "${#REQUIRED_STORY_IDS[@]}" -gt 0 ]; then
    mapfile -t parsed_ids < <(jq -r '.userStories[].id' "$PRD_FILE")

    for expected_id in "${REQUIRED_STORY_IDS[@]}"; do
      if ! printf '%s\n' "${parsed_ids[@]}" | grep -Fxq "$expected_id"; then
        echo "Error: $PRD_FILE is missing expected story ID '$expected_id' from $TASK_PRD_FILE." >&2
        exit 1
      fi
    done
  fi
}

initialize_progress_file() {
  if [ ! -f "$PROGRESS_FILE" ]; then
    {
      echo "# Ralph Progress Log"
      echo "Started: $(date)"
      echo "---"
    } > "$PROGRESS_FILE"
  fi
}

require_command jq
require_command opencode
require_file "$PRD_FILE"
require_file "$SCRIPT_DIR/RALPH.md"
load_required_story_ids
validate_prd

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")

  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    DATE=$(date +%Y-%m-%d)
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"

    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"

    {
      echo "# Ralph Progress Log"
      echo "Started: $(date)"
      echo "---"
    } > "$PROGRESS_FILE"
  fi
fi

if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

initialize_progress_file

echo "Starting Ralph - Tool: opencode - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  validate_prd

  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS (opencode)"
  echo "==============================================================="

  OUTPUT_FILE="$(mktemp)"
  OUTPUT=""

  if opencode run --dangerously-skip-permissions "$(cat "$SCRIPT_DIR/RALPH.md")" 2>&1 | tee "$OUTPUT_FILE"; then
    :
  else
    STATUS=${PIPESTATUS[0]}
    OUTPUT="$(cat "$OUTPUT_FILE")"
    rm -f "$OUTPUT_FILE"
    echo "Error: opencode run failed during iteration $i with exit code $STATUS." >&2
    exit "$STATUS"
  fi

  OUTPUT="$(cat "$OUTPUT_FILE")"
  rm -f "$OUTPUT_FILE"

  if echo "$OUTPUT" | grep -Eq '<promise>COMPLETE</promise>|(^|[^[:alpha:]])COMPLETE([^[:alpha:]]|$)'; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $i of $MAX_ITERATIONS"
    exit 0
  fi

  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
