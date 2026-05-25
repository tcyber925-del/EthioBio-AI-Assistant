# Ralph Upstream Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align local `scripts/ralph/` with upstream `snarktank/ralph` by adding missing skills, updating the shell driver with argument parsing, and aligning file formats — while keeping all local customizations (PRD validation, project context, OpenCode integration).

**Architecture:** Copy/adapt upstream's `skills/prd/SKILL.md` and `skills/ralph/SKILL.md` into `scripts/ralph/skills/`, update `ralph.sh` to accept `--tool opencode` argument, align `prd.json.example` to upstream format, and add browser testing section to `RALPH.md`.

**Tech Stack:** Bash, jq, opencode, Markdown

---

### Task 1: Create `skills/prd/SKILL.md`

**Files:**
- Create: `scripts/ralph/skills/prd/SKILL.md`

- [ ] **Create the PRD Generator skill**

Write upstream's `skills/prd/SKILL.md` content (fetched earlier) to `scripts/ralph/skills/prd/SKILL.md`. The body is tool-agnostic — it generates PRDs via clarifying questions. No adaptations needed beyond adding a note at the top that this is adapted from snarktank/ralph.

Verify: `ls scripts/ralph/skills/prd/SKILL.md` shows the file.

---

### Task 2: Create `skills/ralph/SKILL.md`

**Files:**
- Create: `scripts/ralph/skills/ralph/SKILL.md`

- [ ] **Create the Ralph PRD Converter skill**

Write upstream's `skills/ralph/SKILL.md` content (fetched earlier) to `scripts/ralph/skills/ralph/SKILL.md`. The body is tool-agnostic — it converts markdown PRDs to JSON.

Verify: `ls scripts/ralph/skills/ralph/SKILL.md` shows the file.

---

### Task 3: Update `ralph.sh` with argument parsing

**Files:**
- Modify: `scripts/ralph/ralph.sh` (lines 1-12)

- [ ] **Replace argument parsing to support `--tool opencode` pattern**

Current lines 1-12:
```bash
#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop for OpenCode
# Usage: ./ralph.sh [max_iterations]

set -euo pipefail

MAX_ITERATIONS=10

if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  MAX_ITERATIONS="$1"
  shift
fi
```

Replace with:
```bash
#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop for OpenCode
# Usage: ./ralph.sh [--tool opencode] [max_iterations]

set -euo pipefail

TOOL="opencode"
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    *)
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

if [[ "$TOOL" != "opencode" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'opencode'."
  exit 1
fi
```

- [ ] **Update opencode invocation to use TOOL variable**

Line ~155, change:
```
if opencode run --dangerously-skip-permissions "$(cat "$SCRIPT_DIR/RALPH.md")" 2>&1 | tee "$OUTPUT_FILE"; then
```
To:
```
if $TOOL run --dangerously-skip-permissions "$(cat "$SCRIPT_DIR/RALPH.md")" 2>&1 | tee "$OUTPUT_FILE"; then
```

- [ ] **Update echo messages**

Line ~142, change `echo "Starting Ralph - Tool: opencode - Max iterations: $MAX_ITERATIONS"` to `echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"`

Line ~149, change `echo "  Ralph Iteration $i of $MAX_ITERATIONS (opencode)"` to `echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL)"`

- [ ] **Verify syntax**

Run: `bash -n scripts/ralph/ralph.sh`
Expected: clean exit, no output

---

### Task 4: Update `RALPH.md` with Browser Testing section

**Files:**
- Modify: `scripts/ralph/RALPH.md`

- [ ] **Add Browser Testing section after Project Context**

Insert before the "Stop Condition" section:

```
## Browser Testing (Required for Frontend Stories)

For any story that changes UI, verify it works:
1. Use OpenCode's Playwright browser tools to navigate to the relevant page
2. Interact with the UI and confirm changes work as expected
3. If no browser tools are available, note in the progress report that manual verification is needed
```

---

### Task 5: Update `prd.json.example` to match upstream format

**Files:**
- Modify: `scripts/ralph/prd.json.example`

- [ ] **Update example with upstream fields**

Replace content with:
```json
{
  "title": "Feature Title",
  "branchName": "ralph/feature-name",
  "description": "Feature Description - What this feature does",
  "userStories": [
    {
      "id": "US-001",
      "title": "Story title",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Specific verifiable criterion 1",
        "Specific verifiable criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "Another story",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Specific verifiable criterion 1",
        "Specific verifiable criterion 2",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    }
  ]
}
```

Verify: `jq empty scripts/ralph/prd.json.example` should exit cleanly with no output.

---

### Task 6: Final verification

- [ ] **Syntax check ralph.sh**
Run: `bash -n scripts/ralph/ralph.sh`
Expected: no output

- [ ] **Check example JSON validity**
Run: `jq empty scripts/ralph/prd.json.example`
Expected: no output

- [ ] **Verify new skills exist**
Run: `ls scripts/ralph/skills/prd/SKILL.md scripts/ralph/skills/ralph/SKILL.md`
Expected: both files listed

- [ ] **List all ralph files**
Run: `find scripts/ralph -type f | sort`
Expected: all files present
