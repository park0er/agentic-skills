#!/usr/bin/env bash
# Pre-compile ("warm") the Next.js dev routes so the manual browser click-through
# does not stall. In dev mode each route is webpack-compiled on its FIRST request
# (tens of seconds for a big app), and an in-flight compile can surface as a
# ChunkLoadError in the browser. Curling each route with a long timeout forces
# the compile to finish; afterwards the page loads fast. Re-run after any
# frontend code change (it invalidates the chunks of routes importing the file).
#
# Usage: warm-dev-pages.sh <workspaceSlug> [baseURL] [extraPath ...]
#   baseURL default http://localhost:3000
set -euo pipefail

SLUG="${1:?usage: warm-dev-pages.sh <workspaceSlug> [baseURL] [extraPath ...]}"
BASE="${2:-http://localhost:3000}"
shift || true; shift || true
EXTRA=("$@")

PATHS=(
  "/$SLUG/runtimes"
  "/$SLUG/agents"
  "/$SLUG/agents/new"
  "/$SLUG/issues"
  "/$SLUG/inbox"
  "/$SLUG/settings"
)
PATHS+=("${EXTRA[@]}")

for p in "${PATHS[@]}"; do
  curl -sS -m 200 -o /dev/null -w "%{http_code}  %{time_total}s  $p\n" "$BASE$p" || echo "FAILED  $p"
done
echo "✓ warmed. Tip: warm a specific issue with: warm-dev-pages.sh $SLUG $BASE /$SLUG/issues/<issue-id>"
