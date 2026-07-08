# `gt` — Git Worktree Orchestrator

**Date:** 2026-07-07
**Status:** Draft
**Author:** Agent (via brainstorming)

## Problem

The missing `scripts/Git-Worktree/opencode_orchestrator.sh` managed git worktree lifecycle and opencode context switching across multiple worktrees. It was deleted and never committed to git. A replacement is needed — one that is reusable across projects, not tied to EthioBio alone.

## Solution

A global CLI tool `gt` (short for "git worktree") installed at `~/.local/bin/gt`, with subcommands as individual scripts in `~/.local/share/gt/lib/`. Per-project config in `.gt/config.json`.

## Architecture

### Installation Layout

```
~/.local/bin/gt              →  thin shell dispatcher
~/.local/share/gt/lib/
  gt-list                    →  list worktrees
  gt-switch                  →  switch to a worktree
  gt-create                  →  create a new worktree
  gt-remove                  →  remove a worktree
  gt-opencode                →  launch opencode in worktree context
  gt-init                    →  bootstrap .gt/config.json
  gt-completions             →  bash/zsh completion helpers
```

### Per-Project Config (`.gt/config.json`)

```jsonc
{
  "worktrees_dir": ".worktrees",
  "default_branch": "main",
  "opencode_config": "opencode.jsonc",
  "project_root": ".",
  "worktrees": {
    "agents":          { "branch": "main", "auto_attach": true },
    "backend":         { "branch": "ethibio-knowledge-platform", "auto_attach": true },
    "bot":             { "branch": "main", "auto_attach": true },
    "frontend":        { "branch": "main", "auto_attach": true },
    "memory-timeline": { "branch": "feat/memory-timeline-misconceptions", "auto_attach": true }
  }
}
```

### `gt switch` Directory Change Mechanism

The `gt` command uses a **shell function wrapper** installed by `install.sh`. This allows `gt switch <name>` to natively change the shell's working directory (a subprocess cannot change the parent shell's `cwd`). Pattern: `zoxide`, `jump`, `fasd`.

```sh
# Shell function added to ~/.zshrc / ~/.bashrc
gt() {
  local output
  output=$(command ~/.local/bin/gt "$@")
  local exit_code=$?
  if [[ "$1" == "switch" && $exit_code -eq 0 ]]; then
    cd "$(echo "$output" | tail -1)"  # last line is the cd path
  else
    echo "$output"
  fi
  return $exit_code
}
```

### Subcommand Specifications

#### `gt list`

Prints a formatted table of worktrees from `.gt/config.json`:

- **Name** — key from config
- **Branch** — configured branch
- **Path** — resolved absolute path
- **Status** — `✓` (clean), `✗` (dirty), `D` (detached), `-` (missing)
- **Last Commit** — abbreviated hash + relative date

Flags: `--json` for machine-readable output. `--quiet` suppresses headers.

#### `gt switch <name> [--opencode | -o]`

1. Resolve worktree path from config
2. If worktree missing and `auto_attach=true`, auto-create via `git worktree add`
3. Run `git worktree prune` if `auto_attach=true`
4. Output the absolute path (shell function picks it up for `cd`)
5. If `--opencode` / `-o`, chain into `gt-opencode` after `cd`

#### `gt create <name> [branch] [--no-config]`

1. `git worktree add .worktrees/<name> <branch>` (default branch = `default_branch`)
2. If branch doesn't exist, create it from `default_branch`
3. Add entry to `.gt/config.json` with `auto_attach: true`
4. `--no-config` skips config update (useful for temporary worktrees)

#### `gt remove <name> [--force]`

1. Check for uncommitted changes — prompt unless `--force`
2. `git worktree remove .worktrees/<name>`
3. Remove entry from `.gt/config.json`
4. `--force` skips prompt and uses `git worktree remove --force`

#### `gt opencode <name>`

1. `cd .worktrees/<name>`
2. Launch `opencode` (respects `opencode_config` from config)
3. On exit, print reminder: "Exited opencode in <name> worktree"

#### `gt init [--auto-detect]`

1. If `--auto-detect`, scan `git worktree list` and existing `.worktrees/` directory, auto-generate `.gt/config.json`
2. Otherwise, interactive prompts for each worktree entry
3. Creates `.gt/` directory and writes config

### Error Handling

- Exit 0 on success, non-zero on error
- Error messages go to stderr
- `--quiet` suppresses non-essential stdout
- `--help` on every subcommand

### Future Extensions (not in scope)

- `gt sync` — pull/merge operations across worktrees (opted out due to merge conflict risk)
- `gt pr` — `gh pr create` from current worktree context
- `gt feature <name>` — create branch + worktree + config entry
- Completions for bash/zsh/fish
