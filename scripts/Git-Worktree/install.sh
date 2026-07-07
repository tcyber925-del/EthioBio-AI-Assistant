#!/usr/bin/env bash
set -euo pipefail

GT_SOURCE="$(cd "$(dirname "$0")" && pwd)/gt"
GT_BIN_DIR="${GT_BIN_DIR:-$HOME/.local/bin}"

echo "Installing gt to $GT_BIN_DIR/gt"

mkdir -p "$GT_BIN_DIR"

cp "$GT_SOURCE" "$GT_BIN_DIR/gt"
chmod +x "$GT_BIN_DIR/gt"

# Install shell function wrapper for cd-capable gt switch
SHELL_CONFIG="${SHELL_CONFIG:-$HOME/.zshrc}"
GT_FUNC_MARKER="# gt shell function"

if grep -q "$GT_FUNC_MARKER" "$SHELL_CONFIG" 2>/dev/null; then
  # Remove existing function block so the new version replaces it
  sed -i "/^$GT_FUNC_MARKER/,/^}/d" "$SHELL_CONFIG"
  echo "Updated gt() shell function in $SHELL_CONFIG"
else
  echo "Added gt() shell function to $SHELL_CONFIG"
fi

cat >> "$SHELL_CONFIG" << 'FUNC'

# gt shell function
gt() {
  if [[ "$1" == "switch" ]]; then
    local has_opencode=false name=""
    for arg in "$@"; do
      [[ "$arg" == "-o" || "$arg" == "--opencode" ]] && has_opencode=true
      [[ "$arg" == "switch" || "$arg" == "-o" || "$arg" == "--opencode" ]] && continue
      [[ -z "$name" ]] && name="$arg"
    done

    if $has_opencode && [[ -n "$name" ]]; then
      local target
      target="$(command ~/.local/bin/gt switch "$name" 2>/dev/null)"
      target="$(printf '%s\n' "$target" | tail -1)"
      cd "$target"
      # Skip opencode for root switch — no worktree to open
      if [[ "$name" != "." && "$name" != "root" ]]; then
        command ~/.local/bin/gt opencode "$name"
      fi
    else
      local output
      output=$(command ~/.local/bin/gt "$@")
      local exit_code=$?
      if [[ $exit_code -eq 0 ]] && [[ -n "$output" ]]; then
        cd "$(printf '%s\n' "$output" | tail -1)"
      fi
      return $exit_code
    fi
  else
    command ~/.local/bin/gt "$@"
  fi
}
FUNC
echo "Run: source $SHELL_CONFIG  (or open a new terminal)"

echo "Install complete. Run 'gt help' to get started."
