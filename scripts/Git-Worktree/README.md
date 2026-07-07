# gt — Git Worktree Orchestrator

A global CLI tool for managing git worktrees and launching opencode in context.

## Quick Start

```bash
# Install
bash scripts/Git-Worktree/install.sh
source ~/.zshrc

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
| `switch <name>` | `cd` into a worktree (requires shell function) |
| `create <name> [branch]` | Create worktree + config entry |
| `remove <name>` | Remove worktree + config entry |
| `opencode <name>` | Launch opencode in worktree |
| `init` | Bootstrap `.gt/config.json` |

## Shell Function

`gt switch` changes your shell's working directory via a shell function wrapper
installed by `install.sh`. Without the wrapper, `gt switch` prints the path to
stdout instead of changing directory.
