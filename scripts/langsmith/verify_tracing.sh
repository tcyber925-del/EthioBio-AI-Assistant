#!/usr/bin/env sh
# Verify LangSmith tracing is flowing for the ethiobio project.
#
# Usage:
#   LANGSMITH_API_KEY=lsv2_... scripts/langsmith/verify_tracing.sh [--last-n-minutes 60]
#
# Requires the langsmith CLI (https://cli.langsmith.com/install.sh).
set -eu

PROJECT="${LANGSMITH_PROJECT:-ethiobio}"
ARGS="--project $PROJECT"

# Optional time filter: default to the last hour of traces
FILTER="${1:---last-n-minutes 60}"
ARGS="$ARGS $FILTER"

if [ -z "${LANGSMITH_API_KEY:-}" ]; then
    echo "error: LANGSMITH_API_KEY is not set" >&2
    exit 1
fi

echo "== Projects =="
langsmith project list --api-key "$LANGSMITH_API_KEY" || true

echo
echo "== Recent traces ($PROJECT, hierarchy) =="
langsmith trace list --limit 5 --show-hierarchy --api-key "$LANGSMITH_API_KEY" $ARGS

echo
echo "== Failed traces (last 24h) =="
langsmith trace list --error --last-n-minutes 1440 --api-key "$LANGSMITH_API_KEY" --project "$PROJECT" --limit 5 || true

echo
echo "== LLM runs (last 24h) =="
langsmith run list --run-type llm --limit 5 --api-key "$LANGSMITH_API_KEY" --project "$PROJECT" || true

echo
echo "Done. Drill into a trace with: langsmith trace get <trace-id> --api-key \$LANGSMITH_API_KEY"