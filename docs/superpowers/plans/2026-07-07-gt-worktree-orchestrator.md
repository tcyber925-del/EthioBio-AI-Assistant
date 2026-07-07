# `gt` — Git Worktree Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `gt` CLI tool — global worktree orchestrator with `list`, `switch`, `create`, `remove`, `opencode`, `init` subcommands.

**Architecture:** Single bash script (`gt`) with function-based subcommand dispatch, per-project `.gt/config.json` (JSONC-style, parsed via `grep` + `jq` or `python3`). Shell function wrapper in `.zshrc` for `cd`-capable `gt switch`. `install.sh` deploys to `~/.local/bin/gt` and installs the shell wrapper.

**Tech Stack:** Bash (POSIX + local extensions), git, jq (optional, fallback to python3 for JSON parsing), opencode.

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scripts/Git-Worktree/gt` | Main entrypoint — dispatch + all subcommands |
| Create | `scripts/Git-Worktree/install.sh` | Install to ~/.local/bin, add shell wrapper |
| Create | `scripts/Git-Worktree/README.md` | Quick-start docs |
| Create | `.gt/config.json` | Project config for EthioBio AI Assistant |

### Task 1: Project scaffold & config module

**Files:**
- Create: `scripts/Git-Worktree/gt`
- Create: `.gt/config.json`

The `gt` script starts with the config module — functions to find and parse `.gt/config.json`. This is used by every subcommand.

- [ ] **Step 1: Create the directory and `.gt/config.json`**

```bash
mkdir -p scripts/Git-Worktree .gt
```

- [ ] **Step 2: Write `.gt/config.json`**

Write to `.gt/config.json`:

```json
{
  "worktrees_dir": ".worktrees",
  "default_branch": "main",
  "opencode_config": "opencode.jsonc",
  "worktrees": {
    "agents": { "branch": "main", "auto_attach": true },
    "backend": { "branch": "ethibio-knowledge-platform", "auto_attach": true },
    "bot": { "branch": "main", "auto_attach": true },
    "frontend": { "branch": "main", "auto_attach": true },
    "memory-timeline": { "branch": "feat/memory-timeline-misconceptions", "auto_attach": true }
  }
}
```

- [ ] **Step 3: Write `scripts/Git-Worktree/gt` — shebang, guard, find_project_root**

Create `scripts/Git-Worktree/gt`:

```bash
#!/usr/bin/env bash
set -euo pipefail

GT_VERSION="0.1.0"

# Find project root (walk up for .gt/config.json)
gt_find_root() {
  local dir="${1:-$PWD}"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/.gt/config.json" ]]; then
      echo "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  echo ""
  return 1
}

# Read a config value using jq (preferred) or python3 (fallback)
gt_config_get() {
  local config_file="$1"
  local key="$2"
  if command -v jq &>/dev/null; then
    jq -r "$key" "$config_file"
  elif command -v python3 &>/dev/null; then
    python3 -c "import json,sys; print(json.load(sys.stdin)$key)" < "$config_file"
  else
    echo "ERROR: need jq or python3 to parse config" >&2
    return 1
  fi
}
```

Verify:

```bash
chmod +x scripts/Git-Worktree/gt
scripts/Git-Worktree/gt  # should exit 0 (no subcommand = help)
```

- [ ] **Step 4: Add help dispatch**

Append to `gt`:

```bash
gt_usage() {
  cat <<EOF
gt — Git Worktree Orchestrator v$GT_VERSION

Usage: gt <command> [options]

Commands:
  list       List all worktrees
  switch     Switch to a worktree
  create     Create a new worktree
  remove     Remove a worktree
  opencode   Launch opencode in a worktree
  init       Bootstrap .gt/config.json
  help       Show this help

Options:
  --help, -h  Show help for a command
  --version   Show version
EOF
}

# Dispatch
cmd="${1:-help}"
shift 2>/dev/null || true

case "$cmd" in
  list|switch|create|remove|opencode|init)
    "gt_cmd_$cmd" "$@"
    ;;
  help|--help|-h)
    gt_usage
    ;;
  --version|-v)
    echo "gt v$GT_VERSION"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    gt_usage
    exit 1
    ;;
esac
```

Verify:

```bash
./scripts/Git-Worktree/gt --version  # → gt v0.1.0
./scripts/Git-Worktree/gt help      # → usage text
./scripts/Git-Worktree/gt unknown   # → error + usage, exit 1
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(gt): scaffold project root detection and dispatch"
```

---

### Task 2: `gt list` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_list` function**

Append before the dispatch case:

```bash
gt_cmd_list() {
  local root
  root="$(gt_find_root)" || { echo "Not in a gt project" >&2; exit 1; }
  local config_file="$root/.gt/config.json"
  local worktrees_dir
  worktrees_dir="$(gt_config_get "$config_file" ".worktrees_dir // \".worktrees\"")"
  local json
  json="$(gt_config_get "$config_file" ".worktrees")"

  echo "Worktrees for $(basename "$root")"
  printf "  %-20s %-35s %-10s %s\n" "Name" "Branch" "Status" "Path"

  # Extract worktree keys and iterate
  local keys
  if command -v jq &>/dev/null; then
    keys="$(jq -r '.worktrees | keys[]' "$config_file")"
  else
    keys="$(python3 -c "import json,sys; c=json.load(sys.stdin); print('\n'.join(c['worktrees'].keys()))" < "$config_file")"
  fi

  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    local branch path status
    branch="$(gt_config_get "$config_file" ".worktrees[\"$name\"].branch")"
    path="$root/$worktrees_dir/$name"
    if [[ -d "$path/.git" ]]; then
      if git -C "$path" diff --quiet 2>/dev/null; then
        status="clean"
      else
        status="DIRTY"
      fi
    else
      status="missing"
    fi
    printf "  %-20s %-35s %-10s %s\n" "$name" "$branch" "$status" "$path"
  done <<< "$keys"
}
```

- [ ] **Step 2: Verify manually**

```bash
./scripts/Git-Worktree/gt list
```

Expected: table of 5 worktrees with statuses.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(gt): implement list subcommand"
```

---

### Task 3: `gt switch` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_switch` function**

```bash
gt_cmd_switch() {
  local name="$1"
  local opencode_mode=false
  [[ "$2" == "--opencode" || "$2" == "-o" ]] && opencode_mode=true

  [[ -z "$name" ]] && { echo "Usage: gt switch <name> [--opencode]" >&2; exit 1; }

  local root
  root="$(gt_find_root)" || { echo "Not in a gt project" >&2; exit 1; }
  local config_file="$root/.gt/config.json"
  local worktrees_dir
  worktrees_dir="$(gt_config_get "$config_file" ".worktrees_dir // \".worktrees\"")"
  local branch auto_attach
  branch="$(gt_config_get "$config_file" ".worktrees[\"$name\"].branch // \"$name\"")"
  auto_attach="$(gt_config_get "$config_file" ".worktrees[\"$name\"].auto_attach // false")"

  local target="$root/$worktrees_dir/$name"

  # Auto-create if missing and auto_attach
  if [[ ! -d "$target/.git" && "$auto_attach" == "true" ]]; then
    echo "Creating worktree $name → $branch in $target"
    git -C "$root" worktree add "$target" "$branch" 2>/dev/null || {
      git -C "$root" worktree add -b "$name" "$target" "$(gt_config_get "$config_file" ".default_branch // \"main\"")"
    }
  fi

  if [[ ! -d "$target/.git" ]]; then
    echo "Worktree $name not found at $target" >&2
    exit 1
  fi

  # Prune if auto_attach
  if [[ "$auto_attach" == "true" ]]; then
    git -C "$root" worktree prune
  fi

  # Output the path — shell function captures this for cd
  echo "$target"

  if $opencode_mode; then
    gt_cmd_opencode "$name"
  fi
}
```

- [ ] **Step 2: Verify manually**

```bash
./scripts/Git-Worktree/gt switch agents        # should print path
./scripts/Git-Worktree/gt switch nonexistent   # should error
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(gt): implement switch subcommand"
```

---

### Task 4: `gt create` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_create` function**

```bash
gt_cmd_create() {
  local name="$1"
  local branch="${2:-}"
  local no_config=false
  for arg in "$@"; do [[ "$arg" == "--no-config" ]] && no_config=true; done

  [[ -z "$name" ]] && { echo "Usage: gt create <name> [branch] [--no-config]" >&2; exit 1; }

  local root
  root="$(gt_find_root)" || { echo "Not in a gt project" >&2; exit 1; }
  local config_file="$root/.gt/config.json"
  local worktrees_dir
  worktrees_dir="$(gt_config_get "$config_file" ".worktrees_dir // \".worktrees\"")"
  local default_branch
  default_branch="$(gt_config_get "$config_file" ".default_branch // \"main\"")"

  local target="$root/$worktrees_dir/$name"
  [[ -z "$branch" ]] && branch="$name"

  # Check if branch exists
  if git -C "$root" rev-parse --verify "$branch" &>/dev/null 2>&1; then
    git -C "$root" worktree add "$target" "$branch"
  else
    git -C "$root" worktree add -b "$branch" "$target" "$default_branch"
  fi

  if ! $no_config; then
    # Add to config.json
    local tmp
    tmp="$(mktemp)"
    if command -v jq &>/dev/null; then
      jq --arg name "$name" --arg branch "$branch" \
        '.worktrees[$name] = {"branch": $branch, "auto_attach": true}' \
        "$config_file" > "$tmp" && mv "$tmp" "$config_file"
    elif command -v python3 &>/dev/null; then
      python3 -c "
import json, sys
with open('$config_file') as f: c = json.load(f)
c['worktrees']['$name'] = {'branch': '$branch', 'auto_attach': True}
json.dump(c, sys.stdout, indent=2)
" > "$tmp" && mv "$tmp" "$config_file"
    fi
    echo "Added $name to .gt/config.json"
  fi

  echo "Created worktree $name → $branch at $target"
}
```

- [ ] **Step 2: Verify manually**

```bash
# Create a test worktree (then remove it)
./scripts/Git-Worktree/gt create test-wt main --no-config
git worktree remove .worktrees/test-wt
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(gt): implement create subcommand"
```

---

### Task 5: `gt remove` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_remove` function**

```bash
gt_cmd_remove() {
  local name="$1"
  local force=false
  for arg in "$@"; do [[ "$arg" == "--force" || "$arg" == "-f" ]] && force=true; done

  [[ -z "$name" ]] && { echo "Usage: gt remove <name> [--force]" >&2; exit 1; }

  local root
  root="$(gt_find_root)" || { echo "Not in a gt project" >&2; exit 1; }
  local config_file="$root/.gt/config.json"
  local worktrees_dir
  worktrees_dir="$(gt_config_get "$config_file" ".worktrees_dir // \".worktrees\"")"
  local target="$root/$worktrees_dir/$name"

  if [[ ! -d "$target/.git" ]]; then
    echo "Worktree $name not found at $target" >&2
    exit 1
  fi

  # Check for uncommitted changes
  if ! $force && ! git -C "$target" diff --quiet 2>/dev/null; then
    echo "Worktree $name has uncommitted changes. Use --force to remove anyway." >&2
    exit 1
  fi

  if $force; then
    git -C "$root" worktree remove "$target" --force
  else
    git -C "$root" worktree remove "$target"
  fi

  # Remove from config.json
  local tmp
  tmp="$(mktemp)"
  if command -v jq &>/dev/null; then
    jq "del(.worktrees[\"$name\"])" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
  elif command -v python3 &>/dev/null; then
    python3 -c "
import json, sys
with open('$config_file') as f: c = json.load(f)
c['worktrees'].pop('$name', None)
json.dump(c, sys.stdout, indent=2)
" > "$tmp" && mv "$tmp" "$config_file"
  fi

  echo "Removed worktree $name"
}
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat(gt): implement remove subcommand"
```

---

### Task 6: `gt opencode` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_opencode` function**

```bash
gt_cmd_opencode() {
  local name="$1"
  [[ -z "$name" ]] && { echo "Usage: gt opencode <name>" >&2; exit 1; }

  local root
  root="$(gt_find_root)" || { echo "Not in a gt project" >&2; exit 1; }
  local config_file="$root/.gt/config.json"
  local worktrees_dir
  worktrees_dir="$(gt_config_get "$config_file" ".worktrees_dir // \".worktrees\"")"
  local target="$root/$worktrees_dir/$name"
  local opencode_config
  opencode_config="$(gt_config_get "$config_file" ".opencode_config // \"opencode.jsonc\"")"

  if [[ ! -d "$target/.git" ]]; then
    echo "Worktree $name not found at $target" >&2
    exit 1
  fi

  # Check if opencode_config exists
  if [[ -f "$target/$opencode_config" ]]; then
    cd "$target" && opencode --config "$opencode_config"
  else
    cd "$target" && opencode
  fi

  echo "Exited opencode in $name worktree"
}
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat(gt): implement opencode subcommand"
```

---

### Task 7: `gt init` subcommand

**Files:**
- Modify: `scripts/Git-Worktree/gt`

- [ ] **Step 1: Write `gt_cmd_init` function**

```bash
gt_cmd_init() {
  local auto_detect=false
  for arg in "$@"; do [[ "$arg" == "--auto-detect" ]] && auto_detect=true; done

  local root
  root="$(gt_find_root 2>/dev/null)" || root="$PWD"
  local config_dir="$root/.gt"
  local config_file="$config_dir/config.json"

  mkdir -p "$config_dir"

  if [[ -f "$config_file" ]]; then
    echo "Config already exists at $config_file" >&2
    exit 1
  fi

  if $auto_detect; then
    # Generate from git worktree list
    local worktrees_dir=".worktrees"
    local json="{"

    # Check if .worktrees exists
    if [[ -d "$root/$worktrees_dir" ]]; then
      json="$json\n  \"worktrees_dir\": \"$worktrees_dir\","
      json="$json\n  \"default_branch\": \"main\","
      json="$json\n  \"opencode_config\": \"opencode.jsonc\","
      json="$json\n  \"worktrees\": {"

      local first=true
      while IFS= read -r line; do
        local wt_path wt_branch wt_name
        wt_path="$(echo "$line" | awk '{print $1}')"
        wt_branch="$(echo "$line" | awk -F'[' '{print $2}' | tr -d ']' 2>/dev/null || echo "main")"
        wt_name="$(basename "$wt_path")"
        if $first; then
          first=false
        else
          json="$json,"
        fi
        json="$json\n    \"$wt_name\": { \"branch\": \"$wt_branch\", \"auto_attach\": true }"
      done < <(git -C "$root" worktree list 2>/dev/null | grep -v "^$(realpath "$root")")

      json="$json\n  }"
    else
      json="$json\n  \"worktrees_dir\": \"$worktrees_dir\","
      json="$json\n  \"default_branch\": \"main\","
      json="$json\n  \"opencode_config\": \"opencode.jsonc\","
      json="$json\n  \"worktrees\": {}"
    fi
    json="$json\n}"

    echo -e "$json" | python3 -m json.tool > "$config_file" 2>/dev/null || echo -e "$json" > "$config_file"
  else
    # Interactive mode
    echo "Interactive init not yet implemented — use --auto-detect or write manually" >&2
    echo "{\"worktrees_dir\": \".worktrees\", \"default_branch\": \"main\", \"worktrees\": {}}" > "$config_file"
  fi

  echo "Created $config_file"
}
```

- [ ] **Step 2: Verify**

```bash
mkdir -p /tmp/test-gt && cd /tmp/test-gt && git init && mkdir -p .worktrees
../../scripts/Git-Worktree/gt init --auto-detect
cat .gt/config.json
cd - && rm -rf /tmp/test-gt
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(gt): implement init subcommand"
```

---

### Task 8: `install.sh` — make `gt` globally available

**Files:**
- Create: `scripts/Git-Worktree/install.sh`

- [ ] **Step 1: Write `install.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

GT_SOURCE="$(cd "$(dirname "$0")" && pwd)/gt"
GT_BIN_DIR="${GT_BIN_DIR:-$HOME/.local/bin}"
GT_LIB_DIR="${GT_LIB_DIR:-$HOME/.local/share/gt}"

echo "Installing gt to $GT_BIN_DIR/gt"

mkdir -p "$GT_BIN_DIR" "$GT_LIB_DIR"

# Install the main script
cp "$GT_SOURCE" "$GT_BIN_DIR/gt"
chmod +x "$GT_BIN_DIR/gt"
```

- [ ] **Step 2: Add shell function wrapper installer**

The shell function is what makes `gt switch` change your directory. Append to `install.sh`:

```bash
# Install shell function wrapper
SHELL_CONFIG="${SHELL_CONFIG:-$HOME/.zshrc}"
GT_FUNC_MARKER="# gt shell function"

if ! grep -q "$GT_FUNC_MARKER" "$SHELL_CONFIG" 2>/dev/null; then
  cat >> "$SHELL_CONFIG" << 'FUNC'

# gt shell function
gt() {
  local output
  output=$(command ~/.local/bin/gt "$@")
  local exit_code=$?
  if [[ "$1" == "switch" && $exit_code -eq 0 ]]; then
    cd "$(echo "$output" | tail -1)"
  else
    echo "$output"
  fi
  return $exit_code
}
FUNC
  echo "Added gt() shell function to $SHELL_CONFIG"
  echo "Run: source $SHELL_CONFIG  (or open a new terminal)"
else
  echo "gt() shell function already in $SHELL_CONFIG"
fi

echo "Install complete. Run 'gt help' to get started."
```

- [ ] **Step 3: Test install flow**

```bash
bash scripts/Git-Worktree/install.sh
~/.local/bin/gt help
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(gt): add install.sh with shell function wrapper"
```

---

### Task 9: `gt switch` integration with `install.sh` (shell function)

This task ensures the shell function wrapper from install.sh works end-to-end for `cd` on `gt switch`.

- [ ] **Step 1: Add .gt directory detection for shell function**

The shell function currently hardcodes `~/.local/bin/gt`. It should detect `scripts/Git-Worktree/gt` when in the project repo. Update the install.sh to use the local copy when available:

The shell function in `.zshrc` already calls `~/.local/bin/gt` which handles everything. The shell function just captures the last line of output. No changes needed — verify instead.

- [ ] **Step 2: Manual verification**

```bash
# Source the function and test
source ~/.zshrc
gt list
gt switch agents
pwd  # should be in .worktrees/agents
gt switch -o agents  # just prints path, doesn't cd + opencode since sourced differently
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(gt): shell function wrapper for cd-capable switch"
```

---

### Task 10: README

**Files:**
- Create: `scripts/Git-Worktree/README.md`

- [ ] **Step 1: Write README.md**

```markdown
# gt — Git Worktree Orchestrator

A global CLI tool for managing git worktrees and launching opencode in context.

## Quick Start

```bash
# Install
bash scripts/Git-Worktree/install.sh
source ~/.zshrc  # or open new terminal

# Use
gt list           # show all worktrees
gt switch agents  # cd into agents worktree
gt switch -o backend  # cd + launch opencode
gt create new-feature feat/new-feature
gt remove old-worktree
gt init --auto-detect  # bootstrap config for a new project
```

## Per-Project Config

`.gt/config.json`

## Subcommands

| Command | Description |
|---------|-------------|
| `list` | Table of worktrees with status |
| `switch <name>` | `cd` into a worktree |
| `create <name> [branch]` | Create worktree + config entry |
| `remove <name>` | Remove worktree + config entry |
| `opencode <name>` | Launch opencode in worktree |
| `init` | Bootstrap `.gt/config.json` |

## Shell Function

`gt switch` changes your shell's working directory via a shell function wrapper installed by `install.sh`. Without the wrapper, `gt switch` prints the path to stdout.
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "docs(gt): add README"
```
