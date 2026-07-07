# gt — Git Worktree Orchestrator

`gt` is a global CLI for managing git worktrees. It lets you jump between
branches without stashing, switching, or cluttering a single checkout — each
worktree is an independent working directory on its own branch.

## Installation

```bash
# One-time install
bash scripts/Git-Worktree/install.sh

# Reload your shell
source ~/.zshrc

# Verify
gt --version   # → gt v0.1.0
gt help        # → subcommand list
```

The installer does two things:
1. Copies the `gt` script to `~/.local/bin/gt`
2. Adds a shell function to `~/.zshrc` — this makes `gt switch` actually
   change your current directory (a subprocess can't do that on its own)

**Upgrade:** Re-run `install.sh` anytime you pull new changes — it
automatically replaces the binary and updates the shell function.

**Agent skill:** A `gt` skill is available at `~/.opencode/skills/gt/SKILL.md`
for AI agents. Agents will auto-load it when worktree tasks are detected.

## Usage

### This Project (EthioBio AI Assistant)

The project is already configured with 5 worktrees. Jump straight in:

```bash
# See everything at a glance
gt list

# Jump into a worktree
gt switch agents            # main branch — specs, plans, codebase-wide
gt switch backend           # ethibio-knowledge-platform branch — API, DB, core
gt switch bot               # main branch — Telegram bot
gt switch frontend          # main branch — Next.js dashboard
gt switch memory-timeline   # feat/memory-timeline-misconceptions — feature branch

# Jump + launch opencode
gt switch -o agents

# PWD changed — verify
pwd   # → .../.worktrees/agents
```

All 5 worktrees live in `.worktrees/`. Switch between them freely — no stashing,
no branch switching, no merge conflicts from context changes.

### Any Other Project

```bash
cd /path/to/other/project

# Auto-detect existing worktrees
gt init --auto-detect

# Or create from scratch
gt init
# → creates .gt/config.json
# → edit to add worktrees, or create them with:
gt create frontend          # new branch + worktree + config entry
gt create backend main      # existing branch + worktree + config entry
```

### Worktree Lifecycle

```bash
# Create
gt create my-feature                     # new branch my-feature from default
gt create my-feature feat/my-feature     # explicit branch name
gt create scratch --no-config            # temporary — skip .gt/config.json

# List
gt list

# Switch
gt switch my-feature
gt switch -o my-feature                  # + launch opencode

# Remove
gt remove my-feature
gt remove scratch --force                # skip dirty check
```

## Subcommands

| Command | Action |
|---------|--------|
| `gt list` | Table of worktrees: name, branch, status (clean/dirty/missing), path |
| `gt switch <name> [-o]` | `cd` into a worktree; `-o` also launches opencode |
| `gt create <name> [branch] [--no-config]` | Create worktree + branch + config entry |
| `gt remove <name> [--force]` | Remove worktree + config entry |
| `gt opencode <name>` | Launch opencode in a worktree's directory |
| `gt init [--auto-detect]` | Bootstrap `.gt/config.json` for a project |
| `gt help` | Show usage |
| `gt --version` | Show version |

## Config

Per-project config at `.gt/config.json`:

```json
{
  "worktrees_dir": ".worktrees",
  "default_branch": "main",
  "opencode_config": "opencode.jsonc",
  "worktrees": {
    "agents":          { "branch": "main", "auto_attach": true },
    "backend":         { "branch": "ethibio-knowledge-platform", "auto_attach": true }
  }
}
```

- **`worktrees_dir`** — directory inside the project where worktrees live
- **`default_branch`** — branch used when creating without an explicit branch
- **`opencode_config`** — config file name for `gt opencode`
- **`worktrees.<name>`** — each worktree maps to a branch
- **`auto_attach`** — auto-create worktree on `switch` if missing

## How It Works

### Root Detection

`gt` walks up from your current directory looking for `.gt/config.json`. This
means it works from any subdirectory, not just the project root.

If you're inside a git worktree (`.git` is a file, not a directory), `gt` skips
that directory's config and continues up to the real project root.

### Shell Function

`gt switch` changes directory through a shell function in `.zshrc` (installed
by `install.sh`). The function:

- For `gt switch <name>`: runs `gt` in a subshell, captures the output path,
  and `cd`s to it
- For `gt switch -o <name>`: `cd`s first, then launches opencode in the
  foreground
- For other commands: runs `gt` directly, printing output to the terminal

Without the shell function, `gt switch` would only print the path — you'd need
to run `eval "$(gt switch agents)"` or `cd "$(gt switch agents)"`.

### Status Detection

`gt list` checks each worktree's git status:
- **clean** — no uncommitted changes
- **DIRTY** — has uncommitted changes (visible in bold)
- **missing** — directory doesn't exist (auto-attach will recreate it)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `gt: command not found` | Re-run `install.sh`, then `source ~/.zshrc` |
| `gt switch` doesn't change directory | Run `source ~/.zshrc` — shell function not loaded |
| `Worktree X not found` | Run `gt switch X` again — `auto_attach` creates it if true |
| `Config already exists` | Delete `.gt/config.json` and re-run `gt init --auto-detect` |
| Paths with spaces in error | Should not happen since `0f27ba6` — re-install if you see this |
