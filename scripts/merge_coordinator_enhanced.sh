#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# merge_coordinator_enhanced.sh
#
# READ-ONLY Merge Coordinator
# -----------------------------------------------------------------------------

set -euo pipefail

# -----------------------------------------------------------------------------
# Paths & configuration
# -----------------------------------------------------------------------------

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREES_DIR="${WORKTREES_DIR:-$REPO/../worktrees}"
LOG_DIR="${LOG_DIR:-$WORKTREES_DIR/logs}"
PR_DRAFT_DIR="${OUT_DIR_PR_DRAFTS:-$WORKTREES_DIR/pr-drafts}"

GEMINI_CMD="${GEMINI_CMD:-gemini}"

MAX_TOTAL_BYTES="${MAX_TOTAL_BYTES:-15000}"
MAX_BYTES_PER_FILE="${MAX_BYTES_PER_FILE:-2000}"
MAX_FILES_PER_BRANCH="${MAX_FILES_PER_BRANCH:-8}"
DIFF_CONTEXT_LINES="${DIFF_CONTEXT_LINES:-120}"

mkdir -p "$LOG_DIR" "$PR_DRAFT_DIR"

timestamp() { date +"%Y%m%d-%H%M%S"; }
TS="$(timestamp)"

LOG_FILE="$LOG_DIR/merge-coordinator-$TS.log"
REPORT_FILE="$LOG_DIR/merge-coordinator-report-$TS.md"

log() {
  echo "[merge-coordinator] $*" | tee -a "$LOG_FILE"
}

# -----------------------------------------------------------------------------
# Base branch selection
# -----------------------------------------------------------------------------

pick_base_branch() {
  if git -C "$REPO" rev-parse --verify --quiet main >/dev/null; then
    echo "main"
  elif git -C "$REPO" rev-parse --verify --quiet master >/dev/null; then
    echo "master"
  else
    git -C "$REPO" branch --show-current
  fi
}

# -----------------------------------------------------------------------------
# Discover worktrees
# -----------------------------------------------------------------------------

declare -a WORKTREES=()

if [ -d "$WORKTREES_DIR" ]; then
  for wt in "$WORKTREES_DIR"/*; do
    [ -d "$wt" ] || continue
    if git -C "$wt" rev-parse --git-dir >/dev/null 2>&1; then
      WORKTREES+=("$wt")
    fi
  done
fi

if [ "${#WORKTREES[@]}" -eq 0 ]; then
  log "No active worktrees found."
  exit 0
fi

BASE_BRANCH="$(pick_base_branch)"
git -C "$REPO" fetch --quiet || true

log "Run at: $(date -Iseconds)"
log "Base branch: $BASE_BRANCH"
log "Worktrees detected: ${#WORKTREES[@]}"

# -----------------------------------------------------------------------------
# Collect changes
# -----------------------------------------------------------------------------

declare -A FILE_TO_BRANCHES
declare -A BRANCH_FILES
declare -A BRANCH_SHORTSTAT

for wt in "${WORKTREES[@]}"; do
  BRANCH="$(git -C "$wt" branch --show-current || basename "$wt")"

  SHORTSTAT="$(git -C "$wt" diff --shortstat "$BASE_BRANCH...HEAD" || true)"
  FILES="$(git -C "$wt" diff --name-only "$BASE_BRANCH...HEAD" || true)"

  BRANCH_SHORTSTAT["$BRANCH"]="$SHORTSTAT"
  BRANCH_FILES["$BRANCH"]="$FILES"

  while read -r f; do
    [ -n "$f" ] && FILE_TO_BRANCHES["$f"]+="$BRANCH "
  done <<< "$FILES"

  log "Collected: $BRANCH (${SHORTSTAT:-no changes})"
done

# -----------------------------------------------------------------------------
# Detect overlaps
# -----------------------------------------------------------------------------

OVERLAPS=""
for f in "${!FILE_TO_BRANCHES[@]}"; do
  if [ "$(wc -w <<< "${FILE_TO_BRANCHES[$f]}")" -gt 1 ]; then
    OVERLAPS+="- $f → ${FILE_TO_BRANCHES[$f]}\n"
  fi
done

# -----------------------------------------------------------------------------
# Build prompt
# -----------------------------------------------------------------------------

PROMPT="Merge Coordinator Report
Base branch: $BASE_BRANCH
Run at: $(date -Iseconds)

## Branch summaries
"

for BRANCH in "${!BRANCH_FILES[@]}"; do
  PROMPT+="
### $BRANCH
Shortstat: ${BRANCH_SHORTSTAT[$BRANCH]:-(none)}
Files:
"
  PROMPT+="$(echo "${BRANCH_FILES[$BRANCH]}" | head -n "$MAX_FILES_PER_BRANCH" | sed 's/^/- /')"
  PROMPT+="
"
done

[ -n "$OVERLAPS" ] && PROMPT+="
## Overlapping file edits
$OVERLAPS
"

PROMPT+="
Please produce for each branch:
1. One-sentence summary
2. Risk (low/med/high) with reason
3. PR title
4. 3–5 line PR description
5. Suggested reviewers and test steps
"

PROMPT_FILE="/tmp/merge_coordinator_prompt_$TS.txt"
echo "$PROMPT" > "$PROMPT_FILE"

# -----------------------------------------------------------------------------
# Run Gemini (best-effort, non-fatal)
# -----------------------------------------------------------------------------

ASSISTANT_REPLY=""

if command -v "$GEMINI_CMD" >/dev/null 2>&1; then
  log "Running Gemini (best-effort)…"
  ASSISTANT_REPLY="$(
    GEMINI_DISABLE_MCP=1 \
    "$GEMINI_CMD" -p "$PROMPT" 2>/dev/null || true
  )"
else
  log "Gemini CLI not found. Skipping AI summary."
fi

# -----------------------------------------------------------------------------
# Write report
# -----------------------------------------------------------------------------

{
  echo "# Merge Coordinator Report"
  echo
  echo "**Base branch:** $BASE_BRANCH"
  echo "**Run:** $(date -Iseconds)"
  echo
  if [ -n "$ASSISTANT_REPLY" ]; then
    echo "## Assistant Summary"
    echo "$ASSISTANT_REPLY"
  else
    echo "_No assistant output available_"
  fi
  echo
  echo "## Prompt (truncated)"
  head -n 300 "$PROMPT_FILE"
} > "$REPORT_FILE"

log "Report written: $REPORT_FILE"

# -----------------------------------------------------------------------------
# Write PR drafts
# -----------------------------------------------------------------------------

for wt in "${WORKTREES[@]}"; do
  BRANCH="$(git -C "$wt" branch --show-current)"
  # sanitize branch name (replace slashes to avoid creating nested dirs)
  SAFE_BRANCH="${BRANCH//\//-}"
  DRAFT="$PR_DRAFT_DIR/${SAFE_BRANCH}-draft-$TS.md"
  mkdir -p "$(dirname "$DRAFT")"

  {
    echo "# PR draft for branch: $BRANCH"
    echo
    [ -n "$ASSISTANT_REPLY" ] && echo "$ASSISTANT_REPLY"
    echo
    echo "## Files changed"
    git -C "$wt" diff --name-only "$BASE_BRANCH...HEAD" | sed -n '1,200p'
  } > "$DRAFT"

  log "PR draft written: $DRAFT"
done

log "Merge coordinator complete."
