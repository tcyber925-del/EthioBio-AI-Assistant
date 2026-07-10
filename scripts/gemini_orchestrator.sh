#!/usr/bin/env bash
# gemini_orchestrator.sh
# Reliable Gemini CLI multi-agent orchestrator using git worktrees + tmux
# Adds persona generation, meta-orchestrator, headless/task hooks, and local excludes to avoid merge conflicts.

set -euo pipefail

### CONFIG (edit if needed)
REPO="/home/tcyber/Projects/Doc-Consult-Agent"
WORKTREES_DIR="$REPO/../worktrees"
SESSION_NAME="gemini-agents"
LOG_DIR="$WORKTREES_DIR/logs"

# safety: if true, never remove worktree directories automatically
PRESERVE_WORKTREES="${PRESERVE_WORKTREES:-true}"

BRANCHES=(
  "feat/frontend"
  "feat/backend"
  "main"
)

PERSONA_TEMPLATE="$REPO/scripts/templates/GEMINI.md.template"
META_SCRIPT="$REPO/scripts/meta_orchestrator.sh"

RESTART_DELAY=${RESTART_DELAY:-2}
MAX_RESTARTS=${MAX_RESTARTS:-0} # 0 = unlimited
### END CONFIG

mkdir -p "$WORKTREES_DIR" "$LOG_DIR" "$REPO/scripts/templates"

sanitize() {
  echo "$1" | sed 's#[/ ]#-#g'
}

is_blank() {
  [ -z "${1//[[:space:]]/}" ]
}

ensure_git_exclude() {
  # Add patterns to .git/info/exclude to avoid committing generated GEMINI.md or .agent-local/*
  local exclude="$REPO/.git/info/exclude"
  grep -Fq "GEMINI.md" "$exclude" 2>/dev/null || printf "\n# ignore generated agent files\nGEMINI.md\n.agent-local/\n" >> "$exclude"
  echo "[orchestrator] Ensured local git excludes at $exclude"
}

generate_persona() {
  # Generate a simple GEMINI.md into the worktree if missing.
  # Template variables: {{BRANCH}} are replaced.
  local branch="$1"
  local wt="$2"
  local safe
  safe=$(sanitize "$branch")
  local persona_path="$wt/GEMINI.md"

  if [ -f "$persona_path" ]; then
    echo " - persona exists for $branch"
    return
  fi

  if [ ! -f "$PERSONA_TEMPLATE" ]; then
    # fallback default template
    cat > "$PERSONA_TEMPLATE" <<'EOF'
# GEMINI.md template
<PROTOCOL:INSTRUCTIONS>
You are the "{{BRANCH}}" agent. Focus on changes within this repository path.
- Keep suggestions safe and explain any code modifications.
- Never push changes without human confirmation.
- Provide short PR-ready change lists.
</PROTOCOL:INSTRUCTIONS>
EOF
  fi

  # generate into worktree
  sed "s/{{BRANCH}}/$branch/g" "$PERSONA_TEMPLATE" > "$persona_path"
  echo " + wrote persona: $persona_path"
}

create_worktrees() {
  # optional non-destructive prune (cleans registry only; does not remove dirs)
  # Only perform a prune of stale registry entries if PRESERVE_WORKTREES is false.
  if [ "$PRESERVE_WORKTREES" = "false" ]; then
    git -C "$REPO" worktree prune || true
  else
    echo "[orchestrator] PRESERVE_WORKTREES=true -> skipping automatic git worktree prune"
  fi

  echo "[orchestrator] Ensuring valid worktrees in $WORKTREES_DIR"

  for b in "${BRANCHES[@]}"; do
    if is_blank "$b"; then
      continue
    fi
    safe=$(sanitize "$b")
    wt="$WORKTREES_DIR/$safe"

    # If the worktree already exists properly, ensure persona and continue
    if [ -d "$wt/.git" ]; then
      echo " ✔ worktree OK: $wt"
      generate_persona "$b" "$wt"
      continue
    fi

    # If the directory exists but is not a registered worktree, warn and skip (don't delete)
    if [ -d "$wt" ]; then
      echo " ⚠ directory exists but is not a registered worktree: $wt"
      echo "   -> Skipping creation for safety. To override, set PRESERVE_WORKTREES=false or run cleanup manually."
      continue
    fi

    # If branch exists locally or remotely, create a new worktree for it
    startpoint=""
    if git -C "$REPO" rev-parse --verify --quiet "refs/heads/$b" >/dev/null 2>&1; then
      startpoint="$b"
      echo " - using existing local branch: $b"
      if git -C "$REPO" worktree add "$wt" "$startpoint"; then
        echo "   created worktree for $b at $wt"
        generate_persona "$b" "$wt"
      else
        echo " ❌ failed to create worktree for $b from local branch"
      fi
    elif git -C "$REPO" ls-remote --exit-code --heads origin "$b" >/dev/null 2>&1; then
      echo " - found origin/$b; fetching to create local branch $b"
      git -C "$REPO" fetch origin "$b:$b"
      if git -C "$REPO" worktree add "$wt" "$b"; then
        echo "   created worktree for $b at $wt (from origin/$b)"
        generate_persona "$b" "$wt"
      else
        echo " ❌ failed to create worktree for $b after fetching origin/$b"
      fi
    else
      # branch doesn't exist: create from a safe startpoint
      base="main"
      if ! git -C "$REPO" rev-parse --verify --quiet "refs/heads/$base" >/dev/null 2>&1; then
        base="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
      fi
      echo " - branch $b not found; creating new branch from $base"
      if git -C "$REPO" worktree add -b "$b" "$wt" "$base"; then
        echo "   created new worktree/branch $b at $wt (from $base)"
        generate_persona "$b" "$wt"
      else
        echo " ❌ failed to create new branch/worktree $b from $base"
      fi
    fi
  done
}


start_session() {
  ensure_git_exclude
  create_worktrees

  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[orchestrator] tmux session '$SESSION_NAME' already exists"
  else
    echo "[orchestrator] Creating tmux session: $SESSION_NAME"
    tmux new-session -d -s "$SESSION_NAME" -n "orchestrator" "bash -lc 'cd $REPO && echo \"[orchestrator] PWD=$(pwd)\" && exec $SHELL'"
  fi

  for b in "${BRANCHES[@]}"; do
    if is_blank "$b"; then
      continue
    fi
    safe=$(sanitize "$b")
    wt="$WORKTREES_DIR/$safe"
    winname="$safe"
    logfile="$LOG_DIR/$safe.log"

    if tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -q " $winname"; then
      echo " - window $winname exists, skipping creation"
    else
      echo " - creating window: $winname (worktree: $wt)"
      tmux new-window \
        -t "$SESSION_NAME" \
        -n "$safe" \
        "bash -lc '
          set -e
          cd \"$wt\"
          echo \"[agent:$b] PWD=\$(pwd)\"
          exec \"$REPO/scripts/run_gemini_agent.sh\" \"$b\" \"$wt\" \"$logfile\"
        '"
    fi
  done

  # add a meta-orchestrator window at repo root for cross-branch review (human interactive)
  if tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -q " meta-orchestrator"; then
    echo " - meta-orchestrator window exists, skipping"
  else
    echo " - creating meta-orchestrator window (interactive) at repo root"
    tmux new-window -t "$SESSION_NAME" -n "meta-orchestrator" "bash -lc 'cd \"$REPO\" && exec \"$REPO/scripts/meta_orchestrator.sh\"'"
  fi

  echo "[orchestrator] Started session. Attach with: tmux attach -t $SESSION_NAME"
}
  # Ensure tmux session exists before adding merge-coordinator
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "[orchestrator] tmux session missing, creating: $SESSION_NAME"
  tmux new-session -d -s "$SESSION_NAME" -n "orchestrator" \
    "bash -lc 'cd \"$REPO\" && exec $SHELL'"
fi

   # create merge-coordinator window (non-destructive, interactive summary runner)
  if tmux list-windows -t "$SESSION_NAME" 2>/dev/null | grep -q " merge-coordinator"; then
    echo " - merge-coordinator window exists, skipping"
  else
    echo " - creating merge-coordinator window (interactive/summary) at repo root"
    tmux new-window -t "$SESSION_NAME" -n "merge-coordinator" "bash -lc 'cd \"$REPO\" && exec \"$REPO/scripts/merge_coordinator.sh\"'"
  fi


stop_session() {
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[orchestrator] Killing tmux session: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
  else
    echo "[orchestrator] No session named $SESSION_NAME found"
  fi
}

status() {
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[orchestrator] Session '$SESSION_NAME' is running. Windows:"
    tmux list-windows -t "$SESSION_NAME"
    echo -e "\nLogs in: $LOG_DIR"
  else
    echo "[orchestrator] No session named '$SESSION_NAME'"
  fi
}

attach_session() {
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux attach -t "$SESSION_NAME"
  else
    echo "[orchestrator] No session to attach. Start first: ./gemini_orchestrator.sh start"
  fi
}

cleanup_worktrees() {
  echo "[orchestrator] WARNING: this will remove worktrees under $WORKTREES_DIR. Press Enter to continue or Ctrl+C to abort."
  read -r
  for b in "${BRANCHES[@]}"; do
    if is_blank "$b"; then
      continue
    fi
    safe=$(sanitize "$b")
    wt="$WORKTREES_DIR/$safe"
    if [ -d "$wt" ]; then
      echo " - removing worktree $wt"
      git -C "$REPO" worktree remove --force "$wt" || rm -rf "$wt"
    else
      echo " - no worktree found for $b"
    fi
  done
  git -C "$REPO" worktree prune || true
}

print_help() {
  cat <<EOF
Usage: $0 <command>
Commands:
  start    - create worktrees (if needed) and start tmux session with agents
  stop     - stop the tmux session
  status   - show session status and windows
  attach   - attach to the tmux session
  cleanup  - interactively remove created worktrees (DANGEROUS)
  help     - show this help
EOF
}

# dispatch
cmd=${1:-help}
case "$cmd" in
  start) start_session ;; 
  stop) stop_session ;; 
  status) status ;; 
  attach) attach_session ;; 
  cleanup) cleanup_worktrees ;; 
  help|*) print_help ;;
esac
