#!/usr/bin/env bash
# pr-review-loop — One cycle: read feedback → push fixes → verify/merge
#
# Usage:
#   pr-review-loop                       Full cycle (read → fix → push → verify)
#   pr-review-loop read                  Show all unresolved review feedback
#   pr-review-loop push [message]        Commit changes, push, resolve threads, verify
#   pr-review-loop verify                Check approval status
#   pr-review-loop watch                 Continuously poll for new reviews
#
# Exit codes:
#   0 — PR merged or approved, loop complete
#   1 — Changes pushed, not yet approved (continue loop)
#   2 — No changes made, not approved, needs human help
#   3 — No open PR on current branch

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

detect_pr() {
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "")
  if [[ -z "$PR_NUMBER" ]]; then
    err "No open PR for branch '$branch'"
    err "Create one with: gh pr create --fill"
    exit 3
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

# Filter out CodeRabbit analysis-chain threads (no actionable content)
is_actionable_thread() {
  local body="$1"
  # Analysis chains start with analysis/shell execution logs, not suggestions
  echo "$body" | grep -q "Analysis chain" && echo "$body" | grep -qv "Suggested fix\|Quick win\|Potential issue" && return 1
  echo "$body" | grep -q "🏁 Script executed" && return 1
  return 0
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

resolve_thread() {
  local tid="$1"
  gh api graphql -f query="mutation { r: resolveReviewThread(input: { threadId: \"$tid\" }) { thread { isResolved } } }" --jq '.data.r.thread.isResolved' 2>/dev/null
}

check_branch_protection() {
  local requires_approval=false
  local req_count=0
  local protection
  protection=$(gh api "/repos/$REPO/branches/$BASE_BRANCH/protection" 2>/dev/null || echo "")
  if [[ -n "$protection" ]]; then
    req_count=$(echo "$protection" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('required_pull_request_reviews',{}).get('required_approving_review_count',0))" 2>/dev/null || echo "0")
    if [[ "$req_count" -gt 0 ]]; then requires_approval=true; fi
  fi
  echo "$requires_approval|$req_count"
}

try_merge() {
  local merge_method="${1:-squash}"
  info "No branch protection — attempting to merge PR #$PR_NUMBER"
  gh pr merge "$PR_NUMBER" --"$merge_method" --subject "Merge PR #$PR_NUMBER: $(gh pr view "$PR_NUMBER" --json title -q .title 2>/dev/null)" 2>&1 && return 0
  warn "Auto-merge failed — may need manual merge"
  return 1
}

cmd_read() {
  detect_pr

  local state
  state=$(gh pr view "$PR_NUMBER" --json state -q .state 2>/dev/null || echo "")
  if [[ "$state" == "MERGED" ]]; then
    header "STATUS"
    echo -e "  ${GREEN}${BOLD}✓ PR #$PR_NUMBER has been MERGED.${NC}"
    echo -e "  $PR_URL"
    exit 0
  fi

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
  local req_count="${protection##*|}"
  if [[ "$req_approval" == "true" ]]; then
    echo -e "  Branch protection: ${YELLOW}$req_count approval(s) required on $BASE_BRANCH${NC}"
  else
    echo -e "  Branch protection: ${GREEN}None — can merge without approval${NC}"
  fi

  header "REVIEWS"
  local reviews
  reviews=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews[] | select(.state != "APPROVED") | "  [\(.state)] by @\(.author.login): \(.body[:200])"' 2>/dev/null || echo "")
  if [[ -z "$reviews" ]]; then echo "  No pending review feedback."
  else echo "$reviews"
  fi

  header "UNRESOLVED THREADS"
  local threads_json
  threads_json=$(get_unresolved_threads)
  if [[ -z "$threads_json" || "$threads_json" == "[]" ]]; then
    echo "  All threads resolved. ✓"
    return
  fi

  echo "$threads_json" | python3 -c "
import json,sys
try:
    threads = json.load(sys.stdin)
except:
    threads = []
actionable = 0
for t in threads:
    body = t.get('body', '')
    path = t.get('path', '?')
    tid = t.get('id', '')
    # Skip analysis-chain threads
    if '🏁 Script executed' in body or 'Analysis chain' in body:
        print(f'  📋 {path}  (analysis chain, skipping)')
        continue
    actionable += 1
    sev = '🔴' if 'Critical' in body else '🟠' if 'Major' in body else '🟡'
    summary = body[:100].replace(chr(10), ' ')
    print(f'  {sev} {path}  |  {summary}')
print(f'\n  {actionable} actionable thread(s)')
" 2>/dev/null

  header "NEXT STEP"
  echo -e "  1. Fix the issues above"
  echo -e "  2. Run: ${BOLD}pr-review-loop push \"fix: address PR review feedback\"${NC}"
  echo -e "  3. Run: ${BOLD}pr-review-loop verify${NC}"
  if [[ "$req_approval" != "true" ]]; then
    echo -e "  (No branch protection — will auto-merge when clean)"
  fi
}

cmd_push() {
  detect_pr
  local message="${1:-fix: address PR review feedback}"

  if git diff --quiet && git diff --cached --quiet; then
    warn "No changes to commit."
    cmd_verify
    return
  fi

  # Get changed files before commit
  local changed_files
  changed_files=$(git diff --name-only HEAD 2>/dev/null || true)
  local staged_files
  staged_files=$(git diff --cached --name-only 2>/dev/null || true)
  local all_changed
  all_changed=$(echo -e "$changed_files\n$staged_files" | sort -u | grep -v '^$' || true)

  git add -A
  git commit -m "$message"
  info "Pushing to origin/$(git rev-parse --abbrev-ref HEAD)..."
  git push origin "$(git rev-parse --abbrev-ref HEAD)"

  # Auto-resolve threads for files we touched
  if [[ -n "$all_changed" ]]; then
    header "AUTO-RESOLVING THREADS"
    local threads_json
    threads_json=$(get_unresolved_threads)
    if [[ -n "$threads_json" && "$threads_json" != "[]" ]]; then
      echo "$threads_json" | python3 -c "
import json,sys
try:
    threads = json.load(sys.stdin)
except:
    threads = []
changed = set('${all_changed}'.split(chr(10)))
for t in threads:
    path = t.get('path', '')
    if path in changed:
        print(f'RESOLVE|{t[\"id\"]}|{path}')
" 2>/dev/null | while IFS='|' read -r action tid path; do
        if resolve_thread "$tid"; then
          echo -e "  ${GREEN}✓${NC} Resolved thread on ${CYAN}$path${NC}"
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
    echo -e "\n  ${GREEN}${BOLD}✓ Loop complete.${NC}"
    exit 0
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

  # All clear — merge
  if [[ "$unresolved_count" -eq 0 ]]; then
    if [[ "$req_approval" != "true" ]]; then
      echo -e "\n  ${GREEN}${BOLD}✓ Clean — no approvals required. Merging...${NC}"
      try_merge squash
      exit 0
    elif [[ "$decision" == "APPROVED" ]]; then
      echo -e "\n  ${GREEN}${BOLD}✓ APPROVED — All threads resolved. Loop complete.${NC}"
      exit 0
    else
      echo -e "\n  ${YELLOW}All threads resolved but approval required on $BASE_BRANCH.${NC}"
      echo -e "  Ask a collaborator to approve, or run: ${BOLD}gh pr review $PR_NUMBER --approve${NC}"
      echo -e "  (Note: GitHub blocks self-approval)"
      exit 2
    fi
  fi

  # Not clean
  if [[ -n "$just_pushed" ]]; then
    echo -e "\n  ${YELLOW}Changes pushed. $unresolved_count thread(s) remain. Run again after next review.${NC}"
    exit 1
  elif git diff --quiet HEAD 2>/dev/null; then
    echo -e "\n  ${RED}$unresolved_count unresolved thread(s), no pending changes.${NC}"
    echo -e "  ${YELLOW}Read the issues with 'pr-review-loop read' or wait for next review cycle.${NC}"
    exit 2
  else
    echo -e "\n  ${YELLOW}Uncommitted changes. Push with:${NC}"
    echo -e "    ${BOLD}pr-review-loop push \"fix: ...\"${NC}"
    exit 1
  fi
}

cmd_watch() {
  detect_pr
  info "Watching PR #$PR_NUMBER for new reviews (poll every 30s)..."
  info "Press Ctrl+C to stop"
  local last_review_count
  last_review_count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")
  while true; do
    sleep 30
    local count
    count=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews | length' 2>/dev/null || echo "0")
    if [[ "$count" -gt "$last_review_count" ]]; then
      info "New review detected! ($count total)"
      pr-review-loop read
      last_review_count="$count"
    fi
  done
}

main() {
  local cmd="${1:-}"
  shift 2>/dev/null || true

  case "$cmd" in
    read)   cmd_read ;;
    push)   cmd_push "$@" ;;
    verify) cmd_verify ;;
    watch)  cmd_watch ;;
    "")
      cmd_read
      echo ""
      info "Make your fixes, then run: pr-review-loop push \"fix: address PR review feedback\""
      ;;
    *)
      echo "Usage: pr-review-loop [read|push [message]|verify|watch]"
      exit 1
      ;;
  esac
}

main "$@"
