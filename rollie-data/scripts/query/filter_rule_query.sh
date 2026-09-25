#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[runner] python not found" >&2
    exit 1
  fi
elif ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[runner] python not found: $PYTHON_BIN" >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/filter_rule_query.py" "$@"
