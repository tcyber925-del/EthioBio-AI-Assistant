# gt — Git Worktree Orchestrator

`gt` is a global CLI for managing git worktrees. Jump between branches without
stashing, switching, or cluttering a single checkout — each worktree is an
independent working directory on its own branch.

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

The installer:
1. Copies `gt` to `~/.local/bin/gt`
2. Adds a shell function to `~/.zshrc` — this makes `gt switch` actually
   change your current directory (a subprocess can't do that)

**Upgrade:** Re-run `install.sh` after pulling new changes — it replaces the
binary and updates the shell function.

## Quick Reference

```bash
# Navigation
gt switch agents        # cd into a worktree
gt switch -o backend    # cd + launch opencode
gt switch .             # cd back to project root
gt switch root          # same as '.'

# Lifecycle
gt list                 # show all worktrees
gt create my-feature    # new branch + worktree + config
gt remove my-feature    # remove worktree + config entry

# New project
cd /other/project && gt init --auto-detect
```

## In This Project (EthioSci)

5 pre-configured worktrees in `.worktrees/`:

| Command | Branch | For |
|---------|--------|-----|
| `gt switch agents` | `main` | Codebase-wide, agents, specs, plans |
| `gt switch backend` | `ethibio-knowledge-platform` | API, DB, core logic |
| `gt switch bot` | `main` | Telegram bot |
| `gt switch frontend` | `main` | Next.js dashboard |
| `gt switch memory-timeline` | `feat/memory-timeline-misconceptions` | Feature branch |

Switch freely between them — no stashing, no branch switching, no merge
conflicts.

## Switching Worktrees

**From the shell:** `gt switch <name>` — changes directory immediately.

**From inside opencode:** `gt` can't change a running opencode session's
directory. Two options:

**A) Tmux panes (best):** Run opencode in separate panes, each in a
different worktree. Switch panes instead of switching sessions.

```bash
# Pane 1                # Pane 2                # Pane 3
gt switch -o agents     gt switch -o backend    gt switch -o frontend
```

**B) Exit + re-launch:** Exit opencode (`Ctrl+C` or `/exit`), then run
`gt switch -o <name>` to cd and re-launch.

## Commands

| Command | Action |
|---------|--------|
| `gt list` | Table: name, branch, status (clean/dirty/missing), path |
| `gt switch <name> [-o]` | cd into a worktree; `-o` also launches opencode |
| `gt switch .` or `root` | cd back to project root |
| `gt create <name> [branch] [--no-config]` | Create worktree + branch + config |
| `gt remove <name> [--force]` | Remove worktree + config entry |
| `gt opencode <name>` | Launch opencode in a worktree |
| `gt init [--auto-detect]` | Bootstrap `.gt/config.json` |
| `gt help` | Show help |
| `gt --version` | Show version |

## Config

Per-project config at `.gt/config.json`:

```json
{
  "worktrees_dir": ".worktrees",
  "default_branch": "main",
  "worktrees": {
    "agents":  { "branch": "main", "auto_attach": true },
    "backend": { "branch": "ethibio-knowledge-platform", "auto_attach": true }
  }
}
```

| Field | Description |
|-------|-------------|
| `worktrees_dir` | Directory for worktrees (relative to project root) |
| `default_branch` | Branch used when creating without explicit branch |
| `worktrees.<name>.branch` | Branch this worktree tracks |
| `worktrees.<name>.auto_attach` | Auto-create on `switch` if missing |

## How It Works

**Root detection:** `gt` walks up from `pwd` looking for `.gt/config.json`.
Works from any subdirectory. Skips worktree-internal configs (`.git` is a
file, not a directory).

**Shell function:** `gt switch` changes directory via a `.zshrc` shell
function. Without it, `gt switch` just prints the path.

**Status:** `gt list` checks each worktree — `clean` (no changes),
`DIRTY` (has uncommitted changes), `missing` (not created yet).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `gt: command not found` | Re-run `install.sh`, then `source ~/.zshrc` |
| `gt switch` doesn't cd | Run `source ~/.zshrc` — shell function not loaded |
| `Worktree X not found` | Run again — `auto_attach` creates it if `true` |
| `Config already exists` | Delete `.gt/config.json` and re-run `gt init --auto-detect` |

## Agent Skill

A `gt` skill is available at `~/.opencode/skills/gt/SKILL.md`. Agents
auto-load it when worktree tasks are detected.
