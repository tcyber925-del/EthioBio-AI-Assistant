#!/usr/bin/env bash
# pr-review-loop — Automated PR review fix loop
#
# Usage:
#   pr-review-loop                       Read feedback and show next step
#   pr-review-loop read                  Show all unresolved review feedback
#   pr-review-loop auto [-n N] [message] Auto-apply suggested fixes (max N iterations, default 3)
#   pr-review-loop push [message]        Commit changes, push, resolve threads, verify
#   pr-review-loop verify                Check approval/merge status
#   pr-review-loop watch                 Continuously poll for new reviews
#   pr-review-loop goal [--every N] [--stagnation N]
#                                        Run until PR merged or blocked (polls on interval)
#
# Terminal states (Loop Library):
#   0 — success:       PR merged or approved, loop complete
#   1 — pending:       Changes pushed, not yet approved (continue loop)
#   2 — blocked:       No progress or needs human intervention
#   3 — no-pr:         No open PR on current branch

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}==>${NC} $*" >&2; }
err()   { echo -e "${RED}==>${NC} $*" >&2; }
header(){ echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

detect_pr() {
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "")
  if [[ -z "$PR_NUMBER" ]]; then
    err "No open PR for branch '$branch'"
    err "Create one with: gh pr create --fill"
    terminal_state 3 "no-pr" "No open PR on this branch."
  fi
  REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
  OWNER="${REPO%/*}"
  REPO_NAME="${REPO#*/}"
  PR_URL="https://github.com/$REPO/pull/$PR_NUMBER"
  BASE_BRANCH=$(gh pr view "$PR_NUMBER" --json baseRefName -q .baseRefName 2>/dev/null || echo "main")
}

graphql() {
  gh api graphql -f query="$1" -F o="$OWNER" -F r="$REPO_NAME" -F p="$PR_NUMBER" --jq "$2" 2>/dev/null || echo ""
}

resolve_thread() {
  local tid="$1"
  gh api graphql -f query="mutation { r: resolveReviewThread(input: { threadId: \"$tid\" }) { thread { isResolved } } }" --jq '.data.r.thread.isResolved' 2>/dev/null
}

check_branch_protection() {
  local protection
  protection=$(gh api "/repos/$REPO/branches/$BASE_BRANCH/protection" 2>/dev/null || echo "")
  if [[ -n "$protection" ]]; then
    local req_count
    req_count=$(echo "$protection" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('required_pull_request_reviews',{}).get('required_approving_review_count',0))" 2>/dev/null || echo "0")
    [[ "$req_count" -gt 0 ]] && echo "true|$req_count" || echo "false|0"
  else
    echo "false|0"
  fi
}

try_merge() {
  info "No branch protection — attempting to merge PR #$PR_NUMBER"
  if gh pr merge "$PR_NUMBER" --squash --subject "Merge PR #$PR_NUMBER: $(gh pr view "$PR_NUMBER" --json title -q .title 2>/dev/null)" 2>&1; then
    info "PR #$PR_NUMBER merged!"
    return 0
  fi
  warn "Auto-merge failed"
  return 1
}

get_unresolved_threads() {
  graphql '
    query($o:String!,$r:String!,$p:Int!) {
      repository(owner:$o,name:$r) {
        pullRequest(number:$p) {
          reviewThreads(first:100) {
            nodes { id isResolved comments(first:5) { nodes { path body author { login } } } }
          }
        }
      }
    }' '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | {id, path: .comments.nodes[0].path, body: .comments.nodes[0].body, author: .comments.nodes[0].author.login}]'
}

cmd_read() {
  detect_pr

  local state
  state=$(gh pr view "$PR_NUMBER" --json state -q .state 2>/dev/null || echo "")
  if [[ "$state" == "MERGED" ]]; then
    header "STATUS"
    echo -e "  ${GREEN}${BOLD}✓ PR #$PR_NUMBER has been MERGED.${NC}"
    echo -e "  $PR_URL"
    terminal_state 0 "success" "PR already merged."
  fi

  discover_pr_state

  header "REVIEW DECISION"
  local decision
  decision=$(gh pr view "$PR_NUMBER" --json reviewDecision -q .reviewDecision 2>/dev/null || echo "unknown")
  case "$decision" in
    APPROVED)          echo -e "  ${GREEN}$decision${NC}" ;;
    CHANGES_REQUESTED) echo -e "  ${RED}$decision${NC}" ;;
    "")                echo -e "  ${YELLOW}No review yet${NC}" ;;
    *)                 echo -e "  ${YELLOW}$decision${NC}" ;;
  esac

  local protection
  protection=$(check_branch_protection)
  local req_approval="${protection%%|*}"
  if [[ "$req_approval" == "true" ]]; then
    echo -e "  Branch protection: ${YELLOW}Approval required${NC}"
  else
    echo -e "  Branch protection: ${GREEN}None — can merge without approval${NC}"
  fi

  header "REVIEWS"
  gh pr view "$PR_NUMBER" --json reviews -q '.reviews[] | select(.state != "APPROVED") | "  [\(.state)] by @\(.author.login): \(.body[:200])"' 2>/dev/null || echo "  No pending review feedback."

  local threads_json
  threads_json=$(get_unresolved_threads)

  header "UNRESOLVED THREADS"
  if [[ -z "$threads_json" || "$threads_json" == "[]" ]]; then
    echo "  All threads resolved. ✓"
  else
    echo "$threads_json" | python3 "$SCRIPT_DIR/read_threads.py" 2>/dev/null
  fi

  header "PR COMMENTS"
  gh api "/repos/$REPO/issues/$PR_NUMBER/comments" --paginate 2>/dev/null | python3 "
import json,sys
try:
    data = json.load(sys.stdin)
except:
    data = []
for c in data:
    print(f'  @{c[\"user\"][\"login\"]}  |  {c[\"body\"][:120]}...')
" 2>/dev/null || echo "  No PR-level comments."

  header "NEXT STEP"
  echo -e "  ${BOLD}pr-review-loop auto${NC}  — auto-apply suggested fixes"
  echo -e "  ${BOLD}pr-review-loop push \"msg\"${NC} — manual commit + push"
}

apply_suggested_fixes() {
  local threads_json="$1"
  echo "$threads_json" | python3 "$SCRIPT_DIR/apply_fixes.py" 2>/dev/null
}

cmd_auto() {
  detect_pr
  local max_iter="${MAX_AUTO_ITERATIONS}"
  local message="fix: apply suggested review changes"

  # Parse optional -n flag for iteration limit
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      -n) max_iter="$2"; shift 2 ;;
      *)  message="$1"; shift ;;
    esac
  done

  local state
  state=$(gh pr view "$PR_NUMBER" --json state -q .state 2>/dev/null || echo "")
  if [[ "$state" == "MERGED" ]]; then
    header "STATUS"
    echo -e "  ${GREEN}${BOLD}✓ PR #$PR_NUMBER already MERGED.${NC}"
    terminal_state 0 "success" "Already merged."
  fi

  # Track iteration count
  local iter
  iter=$(iteration_track "$PR_NUMBER" "bump")
  echo -e "  Iteration: ${BOLD}$iter${NC} / $max_iter"

  header "AUTO-FIX MODE"
  echo -e "  Reading unresolved threads and applying suggested diffs..."

  local threads_json
  threads_json=$(get_unresolved_threads)

  if [[ -z "$threads_json" || "$threads_json" == "[]" ]]; then
    echo -e "  ${GREEN}✓ No unresolved threads.${NC}"
    iteration_cleanup "$PR_NUMBER"
    cmd_verify
    return
  fi

  local result
  result=$(apply_suggested_fixes "$threads_json")

  local applied_count=0 skip_count=0 changed_files=""
  while IFS='|' read -r action tid path_or_msg; do
    case "$action" in
      APPLIED)
        applied_count=$((applied_count + 1))
        echo -e "  ${GREEN}✓${NC} Applied fix → ${CYAN}$path_or_msg${NC}"
        resolve_thread "$tid" >/dev/null 2>&1 && echo -e "    ${GREEN}→ Thread resolved${NC}"
        ;;
      SKIP)
        skip_count=$((skip_count + 1))
        echo -e "  ${YELLOW}⚠${NC} Skipped: $path_or_msg"
        ;;
      CHANGED)
        changed_files="$path_or_msg"
        ;;
    esac
  done <<< "$result"

  echo ""

  # Stagnation detection: all threads skipped, nothing applied
  if [[ "$applied_count" -eq 0 && "$skip_count" -gt 0 ]]; then
    echo -e "  ${YELLOW}All $skip_count thread(s) skipped — no diffs could be auto-applied.${NC}"
    iteration_cleanup "$PR_NUMBER"
    terminal_state 2 "blocked" "No progress. Fix remaining threads manually or push with pr-review-loop push."
  fi

  if [[ "$applied_count" -eq 0 && "$skip_count" -eq 0 ]]; then
    echo -e "  ${YELLOW}No auto-fixable threads found. Fix manually and run 'pr-review-loop push'.${NC}"
    cmd_read
    return
  fi

  echo -e "  ${GREEN}$applied_count fix(es) applied${NC}, ${YELLOW}$skip_count skipped${NC}"

  if git diff --quiet && git diff --cached --quiet; then
    warn "No changes resulted from the suggested diffs."
    iteration_cleanup "$PR_NUMBER"
    cmd_verify
    return
  fi

  # Iteration limit check
  if [[ "$iter" -ge "$max_iter" ]]; then
    echo -e "  ${YELLOW}Hit iteration limit ($max_iter).${NC}"
    iteration_cleanup "$PR_NUMBER"
    terminal_state 2 "blocked" "Exhausted $max_iter auto iterations. Handing off to human."
  fi

  info "Running verification gates..."
  if ! run_verification_gates; then
    state_update "{\"applied_count\": $applied_count, \"skip_count\": $skip_count, \"gates_failed\": true, \"last_run\": \"$(date -Iseconds)\"}"
    terminal_state 2 "blocked" "Verification gates failed (ruff/mypy). Fix issues and run pr-review-loop push."
  fi
  state_update "{\"applied_count\": $applied_count, \"skip_count\": $skip_count, \"gates_failed\": false, \"last_run\": \"$(date -Iseconds)\"}"

  git add -A
  git commit -m "$message"
  info "Pushing..."
  git push origin "$(git rev-parse --abbrev-ref HEAD)"

  info "Triggering re-review..."
  gh pr comment "$PR_NUMBER" --body "@coderabbitai review" 2>/dev/null || true

  info "Verifying..."
  cmd_verify pushed
}

cmd_push() {
  detect_pr
  local message="${1:-fix: address PR review feedback}"

  if git diff --quiet && git diff --cached --quiet; then
    warn "No changes to commit."
    cmd_verify
    return
  fi

  local changed_files
  changed_files=$(git diff --name-only HEAD 2>/dev/null || true)
  local staged_files
  staged_files=$(git diff --cached --name-only 2>/dev/null || true)
  local all_changed
  all_changed=$(echo -e "$changed_files\n$staged_files" | sort -u | grep -v '^$' || true)

  git add -A
  git commit -m "$message"
  info "Pushing..."
  git push origin "$(git rev-parse --abbrev-ref HEAD)"

  if [[ -n "$all_changed" ]]; then
    header "AUTO-RESOLVING THREADS"
    local threads_json
    threads_json=$(get_unresolved_threads)
    if [[ -n "$threads_json" && "$threads_json" != "[]" ]]; then
      echo "$threads_json" | python3 "$SCRIPT_DIR/resolve_touched.py" "$all_changed" 2>/dev/null | while IFS='|' read -r action tid path; do
        if resolve_thread "$tid"; then
          echo -e "  ${GREEN}✓${NC} Resolved thread on ${CYAN}${path}${NC}"
        fi
      done
    fi
  fi

  info "Checking status..."
  cmd_verify pushed
}

cmd_verify() {
  detect_pr
  local just_pushed="${1:-}"

  local state decision
  state=$(gh pr view "$PR_NUMBER" --json state -q .state 2>/dev/null || echo "")
  decision=$(gh pr view "$PR_NUMBER" --json reviewDecision -q .reviewDecision 2>/dev/null || echo "")

  if [[ "$state" == "MERGED" ]]; then
    header "VERIFICATION"
    echo -e "  ${GREEN}${BOLD}✓ PR #$PR_NUMBER has been MERGED.${NC}"
    echo -e "  $PR_URL"
    terminal_state 0 "success" "PR merged."
  fi

  local unresolved_count
  unresolved_count=$(graphql '
    query($o:String!,$r:String!,$p:Int!) {
      repository(owner:$o,name:$r) { pullRequest(number:$p) { reviewThreads(first:100) { nodes { isResolved comments(first:2) { nodes { body } } } } } }
    }' '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | select(.comments.nodes[0].body | test("🏁 Script executed|Analysis chain") | not)] | length')

  local protection
  protection=$(check_branch_protection)
  local req_approval="${protection%%|*}"

  header "VERIFICATION"
  echo -e "  PR:           $PR_URL"
  echo -e "  State:        $(case "$state" in MERGED) echo -e "${GREEN}MERGED${NC}" ;; *) echo -e "${YELLOW}OPEN${NC}" ;; esac)"
  echo -e "  Review:       $(case "$decision" in
    APPROVED)          echo -e "${GREEN}$decision${NC}" ;;
    CHANGES_REQUESTED) echo -e "${RED}$decision${NC}" ;;
    *)                 echo -e "${YELLOW}Pending${NC}" ;;
  esac)"
  echo -e "  Unresolved:   $([[ "$unresolved_count" -eq 0 ]] && echo -e "${GREEN}0${NC}" || echo -e "${YELLOW}$unresolved_count${NC}")"
  echo -e "  Protection:   $([[ "$req_approval" == "true" ]] && echo -e "${YELLOW}Approval required${NC}" || echo -e "${GREEN}None${NC}")"

  if [[ "$unresolved_count" -eq 0 ]]; then
    iteration_cleanup "$PR_NUMBER"
    if [[ "$req_approval" != "true" ]]; then
      local review_count
      review_count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")
      if [[ "$review_count" -eq 0 ]]; then
        echo -e "\n  ${YELLOW}0 threads, but no reviews yet — waiting for first review cycle.${NC}"
        terminal_state 1 "pending" "No reviews submitted yet."
      fi
      echo -e "\n  ${GREEN}${BOLD}✓ Clean — no approvals required. Merging...${NC}"
      try_merge && terminal_state 0 "success" "Merged."
      echo -e "\n  ${YELLOW}Auto-merge failed.${NC}"
      terminal_state 1 "pending" "Merge failed — push or merge manually."
    elif [[ "$decision" == "APPROVED" ]]; then
      terminal_state 0 "success" "APPROVED — all threads resolved."
    else
      echo -e "\n  ${YELLOW}All threads resolved but $BASE_BRANCH requires approval.${NC}"
      echo -e "  Ask a collaborator to approve (self-approval is blocked)."
      terminal_state 2 "blocked" "Needs external approval."
    fi
  fi

  if [[ -n "$just_pushed" ]]; then
    echo -e "\n  ${YELLOW}Changes pushed. $unresolved_count thread(s) remain.${NC}"
    echo -e "  Run again after next review: ${BOLD}pr-review-loop auto${NC}"
    terminal_state 1 "pending" "Changes pushed, waiting for review."
  elif git diff --quiet HEAD 2>/dev/null; then
    echo -e "\n  ${RED}$unresolved_count unresolved thread(s), no pending changes.${NC}"
    echo -e "  Run: ${BOLD}pr-review-loop auto${NC} or ${BOLD}pr-review-loop read${NC}"
    terminal_state 2 "blocked" "Unresolved threads with no local changes."
  else
    echo -e "\n  ${YELLOW}Uncommitted changes detected. Push with:${NC}"
    echo -e "    ${BOLD}pr-review-loop push \"fix: ...\"${NC}"
    terminal_state 1 "pending" "Uncommitted changes ready to push."
  fi
}

cmd_watch() {
  detect_pr
  info "Watching PR #$PR_NUMBER for new reviews (poll every 30s)..."
  info "Press Ctrl+C to stop"
  local last_count
  last_count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")
  while true; do
    sleep 30
    local count
    count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")
    if [[ "$count" -gt "$last_count" ]]; then
      info "New review detected! ($count total)"
      cmd_read
      last_count="$count"
    fi
  done
}

terminal_state() {
  local code="$1"
  local name="$2"
  local msg="$3"
  case "$code" in
    0) echo -e "\n  ${GREEN}${BOLD}[${name}]${NC} ${msg}" ;;
    1) echo -e "\n  ${YELLOW}${BOLD}[${name}]${NC} ${msg}" ;;
    2) echo -e "\n  ${RED}${BOLD}[${name}]${NC} ${msg}" ;;
    3) echo -e "\n  ${RED}${BOLD}[${name}]${NC} ${msg}" ;;
  esac
  exit "$code"
}

ITER_FILE="/tmp/pr-review-loop-iter"
MAX_AUTO_ITERATIONS=3

iteration_track() {
  local pr="$1"
  local action="$2"  # bump or reset
  local file="${ITER_FILE}-${pr}"
  if [[ "$action" == "reset" ]]; then
    rm -f "$file"
    return
  fi
  local count=0
  [[ -f "$file" ]] && count=$(cat "$file")
  count=$((count + 1))
  echo "$count" > "$file"
  echo "$count"
}

iteration_cleanup() {
  local pr="$1"
  rm -f "${ITER_FILE}-${pr}"
}

STATE_FILE="$PWD/.pr-loop-state.json"

state_update() {
  local json="$1"
  python3 -c "
import json, os
path = '$STATE_FILE'
data = {}
if os.path.exists(path):
    with open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
data.update($json)
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null
}

state_read_key() {
  local key="$1"
  if [[ ! -f "$STATE_FILE" ]]; then
    echo ""
    return
  fi
  python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    try:
        d = json.load(f)
        print(d.get('$key', ''))
    except:
        print('')
" 2>/dev/null
}

state_cleanup() {
  rm -f "$STATE_FILE"
}

discover_pr_state() {
  local json
  json=$(gh pr view "$PR_NUMBER" --json isDraft,mergeable,state 2>/dev/null || echo '{}')
  local is_draft mergeable pr_state
  is_draft=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('isDraft','?'))" 2>/dev/null || echo "?")
  mergeable=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('mergeable','?'))" 2>/dev/null || echo "?")
  pr_state=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('state','?'))" 2>/dev/null || echo "?")

  local ci_json ci_status ci_conclusion
  ci_json=$(gh run list --branch "$(git rev-parse --abbrev-ref HEAD)" --limit 1 --json status,conclusion 2>/dev/null || echo '[]')
  ci_status=$(echo "$ci_json" | python3 -c "
import json,sys
try:
    runs = json.load(sys.stdin)
    if runs:
        s = runs[0].get('status','?')
        c = runs[0].get('conclusion','?')
        print(f'{s}/{c}' if s != 'completed' else c)
    else:
        print('no-runs')
except:
    print('?')
" 2>/dev/null || echo "?")

  local draft_label merge_label
  [[ "$is_draft" == "true" ]] && draft_label="${YELLOW}draft${NC}" || draft_label="${GREEN}no${NC}"
  case "$mergeable" in
    MERGEABLE)   merge_label="${GREEN}clean${NC}" ;;
    CONFLICTING) merge_label="${RED}conflict${NC}" ;;
    UNKNOWN)     merge_label="${YELLOW}checking${NC}" ;;
    *)           merge_label="${YELLOW}$mergeable${NC}" ;;
  esac
  local ci_label
  case "$ci_conclusion" in
    success) ci_label="${GREEN}success${NC}" ;;
    failure|startup_failure) ci_label="${RED}fail${NC}" ;;
    cancelled) ci_label="${YELLOW}cancelled${NC}" ;;
    in_progress|queued|waiting) ci_label="${YELLOW}running${NC}" ;;
    no-runs) ci_label="${YELLOW}no runs${NC}" ;;
    *) ci_label="${YELLOW}$ci_conclusion${NC}" ;;
  esac

  DISCOVER_DRAFT="$is_draft"
  DISCOVER_CI="$ci_conclusion"
  DISCOVER_MERGEABLE="$mergeable"

  echo -e "  Status: ${GREEN}$pr_state${NC} | Draft: $draft_label | CI: $ci_label | Mergeable: $merge_label"
}

run_verification_gates() {
  local failed=0
  local results="[]"

  if command -v ruff &>/dev/null && [[ -f "pyproject.toml" || -f ".ruff.toml" || -f "ruff.toml" ]]; then
    info "Gate: ruff check ."
    local ruff_out
    ruff_out=$(ruff check . 2>&1) || {
      warn "ruff check FAILED"
      echo "$ruff_out" | sed 's/^/    /'
      failed=1
    }
  fi

  if command -v mypy &>/dev/null && [[ -d "src" ]]; then
    info "Gate: mypy src/"
    local mypy_out
    mypy_out=$(mypy src/ 2>&1) || {
      warn "mypy FAILED"
      echo "$mypy_out" | sed 's/^/    /'
      failed=1
    }
  fi

  if [[ "$failed" -eq 1 ]]; then
    warn "Verification gates failed — skipping commit."
    state_update '{"verification_failed": true, "last_verification": "fail"}'
    return 1
  fi

  state_update '{"verification_failed": false, "last_verification": "pass"}'
  return 0
}

parse_duration() {
  local input="$1"
  local num="${input%[smh]}"
  local unit="${input: -1}"
  case "$unit" in
    s) echo "$num" ;;
    m) echo "$((num * 60))" ;;
    h) echo "$((num * 3600))" ;;
    *) echo "$((input * 60))" ;;
  esac
}

cmd_goal() {
  detect_pr 2>/dev/null || true
  if [[ -z "${PR_NUMBER:-}" ]]; then
    info "No open PR — creating one..."
    if ! gh pr create --fill 2>&1; then
      terminal_state 3 "no-pr" "Failed to create PR. Push commits first."
    fi
    detect_pr
  fi
  local interval_secs=300
  local stagnation_max=5

  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --every|-e) interval_secs=$(parse_duration "$2"); shift 2 ;;
      --stagnation|-s) stagnation_max="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  info "Goal: Get PR #$PR_NUMBER merged"
  info "Poll: every ${interval_secs}s | Stagnation limit: $stagnation_max cycles"
  echo -e "  PR: $PR_URL"
  echo ""

  local cycle=0 stagnant=0 last_thread_count=-1

  while true; do
    cycle=$((cycle + 1))
    local timestamp
    timestamp=$(date '+%H:%M:%S')
    echo -e "\n${CYAN}━━━ Cycle $cycle at $timestamp ━━━${NC}"

    local state
    state=$(gh pr view "$PR_NUMBER" --json state -q .state 2>/dev/null || echo "")
    if [[ "$state" == "MERGED" ]]; then
      state_update "{\"cycle\": $cycle, \"last_exit_code\": 0, \"last_run\": \"$(date -Iseconds)\", \"terminal\": \"success\"}"
      terminal_state 0 "success" "Goal achieved — PR #$PR_NUMBER merged!"
    fi

    discover_pr_state

    if [[ "$DISCOVER_DRAFT" == "true" ]]; then
      echo -e "  ${YELLOW}PR is in draft — not ready for review.${NC}"
      echo -e "\n  ${YELLOW}⌛ Sleeping ${interval_secs}s...${NC}"
      state_update "{\"cycle\": $cycle, \"last_exit_code\": 1, \"last_run\": \"$(date -Iseconds)\", \"terminal\": \"draft\"}"
      sleep "$interval_secs"
      continue
    fi

    if [[ "$DISCOVER_CI" == "failure" || "$DISCOVER_CI" == "startup_failure" ]]; then
      echo -e "  ${YELLOW}CI is failing — fixing before continuing...${NC}"
    fi

    if [[ "$DISCOVER_MERGEABLE" == "CONFLICTING" ]]; then
      echo -e "  ${RED}Merge conflict detected — needs human resolution.${NC}"
      state_update "{\"cycle\": $cycle, \"last_exit_code\": 2, \"last_run\": \"$(date -Iseconds)\", \"terminal\": \"conflict\"}"
      terminal_state 2 "blocked" "PR has merge conflicts. Resolve manually."
    fi

    local output exit_code=0
    output=$(bash "$SCRIPT_DIR/pr-review-loop.sh" auto -n 999 2>&1) || exit_code=$?

    if [[ -n "$output" ]]; then
      echo "$output"
    fi

    case "$exit_code" in
      0)
        state_update "{\"cycle\": $cycle, \"last_exit_code\": 0, \"last_run\": \"$(date -Iseconds)\", \"terminal\": \"success\"}"
        terminal_state 0 "success" "Goal achieved — PR #$PR_NUMBER merged/approved."
        ;;
      2)
        state_update "{\"cycle\": $cycle, \"last_exit_code\": 2, \"last_run\": \"$(date -Iseconds)\", \"terminal\": \"blocked\"}"
        terminal_state 2 "blocked" "Goal blocked — auto-fix hit a terminal stop."
        ;;
      1|*)
        local threads_json
        threads_json=$(get_unresolved_threads)
        local thread_count=0
        if [[ -n "$threads_json" && "$threads_json" != "[]" ]]; then
          thread_count=$(echo "$threads_json" | python3 -c "
import json,sys
try:
    t = json.load(sys.stdin)
    print(len([x for x in t if '🏁 Script executed' not in x.get('body','') and 'Analysis chain' not in x.get('body','')]))
except:
    print(0)
" 2>/dev/null || echo "0")
        fi

        state_update "{\"cycle\": $cycle, \"last_exit_code\": 1, \"last_run\": \"$(date -Iseconds)\", \"last_thread_count\": $thread_count, \"terminal\": \"pending\"}"

        local review_count
        review_count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")

        # Don't count "waiting for first review" as stagnation
        if [[ "$review_count" -eq 0 ]]; then
          stagnant=0
          last_thread_count="$thread_count"
          echo -e "\n  ${YELLOW}⌛ Waiting for first review (${review_count} reviews, ${thread_count} threads)...${NC}"
        elif [[ "$thread_count" -eq "$last_thread_count" && "$thread_count" -ge 0 ]]; then
          stagnant=$((stagnant + 1))
          echo -e "\n  ${YELLOW}⚠ Stagnant cycle ${stagnant}/${stagnation_max} (${thread_count} threads, unchanged)${NC}"
          if [[ "$stagnant" -ge "$stagnation_max" ]]; then
            state_update '{"terminal": "stagnated"}'
            terminal_state 2 "blocked" "Stagnated after $stagnant cycles with $thread_count unresolved threads."
          fi
        else
          stagnant=0
          last_thread_count="$thread_count"
        fi

        echo -e "\n  ${YELLOW}⌛ Sleeping ${interval_secs}s — next cycle in ${interval_secs}s...${NC}"
        sleep "$interval_secs"
        ;;
    esac
  done
}

main() {
  local cmd="${1:-}"
  shift 2>/dev/null || true

  case "$cmd" in
    read)   cmd_read ;;
    auto)   cmd_auto "$@" ;;
    push)   cmd_push "$@" ;;
    verify) cmd_verify ;;
    watch)  cmd_watch ;;
    goal)   cmd_goal "$@" ;;
    "")
      cmd_read
      echo ""
      info "Auto-fix: ${BOLD}pr-review-loop auto${NC}"
      info "Goal:     ${BOLD}pr-review-loop goal${NC}"
      info "Manual:   ${BOLD}pr-review-loop push \"fix: ...\"${NC}"
      ;;
    *)
      echo "Usage: pr-review-loop [read|auto|push|verify|watch|goal]"
      echo "  goal --every 5m --stagnation 5    Run until PR merged or blocked"
      exit 1
      ;;
  esac
}

main "$@"
