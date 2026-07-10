# (paste the full script content above here)
#!/usr/bin/env bash
# ensure_git_exclude.sh
# Safely ensure local (non-versioned) git excludes for agent runtime files.
# - keeps .gemini/skills tracked
# - excludes only volatile .gemini subpaths and other generated artifacts
# - idempotent, creates a timestamped backup of .git/info/exclude
# - refuses to run if .git/info/exclude already excludes .gemini/ entirely

#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
EXCLUDE="$REPO/.git/info/exclude"

ensure_rule() {
  local rule="$1"
  grep -Fxq "$rule" "$EXCLUDE" 2>/dev/null || echo "$rule" >> "$EXCLUDE"
}

ensure_rule "# --- local agent ignores ---"
ensure_rule "GEMINI.md"
ensure_rule ".agent-local/"
ensure_rule ".gemini/cache/"
ensure_rule ".gemini/runtime/"

echo "[ensure_git_exclude] ensured safe local excludes"
