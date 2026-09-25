#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/_check_env.sh"
_check_env_python || exit 1
_check_env_playwright || exit 1

exec "$PYTHON_BIN" "$SCRIPT_DIR/silent_refresh.py" "$@"
