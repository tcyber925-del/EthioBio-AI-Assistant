#!/usr/bin/env bash
# pr-review-loop — One cycle: read feedback → push fixes → verify approval
#
# Usage:
#   pr-review-loop                       Full cycle (read + push + verify)
#   pr-review-loop read                  Show all unresolved review feedback
#   pr-review-loop push [message]        Commit changes, push, check approval
#   pr-review-loop verify                Check approval status only
#
# Exit codes:
#   0 — PR approved, loop should stop
#   1 — Changes pushed, PR not yet approved (continue loop)
#   2 — No changes made but PR not approved (needs human help)
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
  info "PR #$PR_NUMBER — $branch → $REPO"
}

cmd_read() {
  detect_pr

  header "REVIEW DECISION"
  local decision
  decision=$(gh pr view "$PR_NUMBER" --json reviewDecision -q .reviewDecision 2>/dev/null || echo "unknown")
  case "$decision" in
    APPROVED)          echo -e "  ${GREEN}$decision${NC}" ;;
    CHANGES_REQUESTED) echo -e "  ${RED}$decision${NC}" ;;
    "")                echo -e "  ${YELLOW}No review yet${NC}" ;;
    *)                 echo -e "  ${YELLOW}$decision${NC}" ;;
  esac

  header "REVIEWS"
  local reviews
  reviews=$(gh pr view "$PR_NUMBER" --json reviews -q '.reviews[] | select(.state != "APPROVED") | "  [\(.state)] by @\(.author.login): \(.body[:300])"' 2>/dev/null || echo "")
  if [[ -z "$reviews" ]]; then
    echo "  No pending review feedback."
  else
    echo "$reviews"
  fi

  header "INLINE REVIEW COMMENTS"
  local owner="${REPO%/*}" repo="${REPO#*/}"
  local comments
  comments=$(gh api graphql -f query='
    query($o:String!,$r:String!,$p:Int!) {
      repository(owner:$o,name:$r) { pullRequest(number:$p) { reviewThreads(first:50) { nodes { isResolved comments(first:5) { nodes { path body } } } } } }
    }' -F o="$owner" -F r="$repo" -F p="$PR_NUMBER" --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | .comments.nodes[0] | "\(.path) | \(.body[:120])"] | .[]' 2>/dev/null)
  if [[ -z "$comments" ]]; then
    echo "  No unresolved inline review comments."
  else
    while IFS= read -r line; do
      sev="🟡"
      echo "$line" | grep -qi "critical" && sev="🔴"
      echo "$line" | grep -qi "major" && sev="🟠"
      echo "  $sev $line"
    done <<< "$comments"
  fi

  header "PR COMMENTS"
  local pr_comments
  pr_comments=$(gh api "/repos/$REPO/issues/$PR_NUMBER/comments" --paginate 2>/dev/null | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
except:
    data = []
for c in data:
    print(f'  @{c[\"user\"][\"login\"]}  |  {c[\"body\"][:120]}...')
" 2>/dev/null)
  if [[ -z "$pr_comments" ]]; then
    echo "  No PR-level comments."
  else
    echo "$pr_comments"
  fi

  header "NEXT STEP"
  echo -e "  Fix the issues above, then run:"
  echo -e "    ${BOLD}pr-review-loop push \"fix: address PR review feedback\"${NC}"
}

cmd_push() {
  detect_pr
  local message="${1:-fix: address PR review feedback}"

  if git diff --quiet && git diff --cached --quiet; then
    warn "No changes to commit."
    warn "Run 'pr-review-loop read' first to see what needs fixing."
    cmd_verify
    return
  fi

  git add -A
  git commit -m "$message"
  info "Pushing to origin/$(git rev-parse --abbrev-ref HEAD)..."
  git push origin "$(git rev-parse --abbrev-ref HEAD)"

  info "Checking approval status..."
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
    echo -e "  PR: https://github.com/$REPO/pull/$PR_NUMBER"
    echo -e "\n  ${GREEN}${BOLD}✓ Loop complete.${NC}"
    exit 0
  fi

  local owner="${REPO%/*}" repo="${REPO#*/}"
  local unresolved_threads
  unresolved_threads=$(gh api graphql -f query='
    query($o:String!,$r:String!,$p:Int!) {
      repository(owner:$o,name:$r) { pullRequest(number:$p) { reviewThreads(first:50) { nodes { isResolved } } } }
    }' -F o="$owner" -F r="$repo" -F p="$PR_NUMBER" --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length' 2>/dev/null || echo "0")

  header "VERIFICATION"
  echo -e "  Review decision:  $(case "$decision" in
    APPROVED)          echo -e "${GREEN}$decision${NC}" ;;
    CHANGES_REQUESTED) echo -e "${RED}$decision${NC}" ;;
    *)                 echo -e "${YELLOW}Pending${NC}" ;;
  esac)"
  echo -e "  Unresolved threads: $unresolved_threads"
  echo -e "  PR: https://github.com/$REPO/pull/$PR_NUMBER"

  if [[ "$decision" == "APPROVED" && "$unresolved_threads" -eq 0 ]]; then
    echo -e "\n  ${GREEN}${BOLD}✓ APPROVED — All threads resolved. Loop complete.${NC}"
    exit 0
  elif [[ "$decision" == "APPROVED" ]]; then
    echo -e "\n  ${YELLOW}Approved but $unresolved_threads thread(s) remain. Resolve them manually.${NC}"
    exit 1
  elif [[ -n "$just_pushed" ]]; then
    echo -e "\n  ${YELLOW}Changes pushed. PR is not yet approved. Run again after next review.${NC}"
    echo -e "  Run: ${BOLD}pr-review-loop${NC}"
    exit 1
  elif git diff --quiet HEAD 2>/dev/null; then
    echo -e "\n  ${RED}No changes found but PR is not approved.${NC}"
    echo -e "  ${YELLOW}Either fix the issues first with 'pr-review-loop read', or the next review cycle is needed.${NC}"
    exit 2
  else
    echo -e "\n  ${YELLOW}Uncommitted changes detected. Commit and push with:${NC}"
    echo -e "    ${BOLD}pr-review-loop push \"fix: address PR review feedback\"${NC}"
    exit 1
  fi
}

main() {
  local cmd="${1:-}"
  shift 2>/dev/null || true

  case "$cmd" in
    read)   cmd_read ;;
    push)   cmd_push "$@" ;;
    verify) cmd_verify ;;
    "")
      cmd_read
      echo ""
      info "Make your fixes, then run: pr-review-loop push \"fix: address PR review feedback\""
      ;;
    *)
      echo "Usage: pr-review-loop [read|push [message]|verify]"
      exit 1
      ;;
  esac
}

main "$@"
