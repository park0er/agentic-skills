#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
AUTH_LOG_DIR="$HOME/.rollie/auth/logs"

source "$SCRIPT_DIR/_check_env.sh"

_json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

_auth_env_log_path() {
  mkdir -p "$AUTH_LOG_DIR"
  mktemp "$AUTH_LOG_DIR/check_cookies-env.XXXXXX.log"
}

_emit_env_failure() {
  local reason="$1"
  local summary="$2"
  local log_file="$3"
  printf '{"ok":false,"reason":"%s","summary":"%s","auth_log_file":"%s"}\n' \
    "$(_json_escape "$reason")" \
    "$(_json_escape "$summary")" \
    "$(_json_escape "$log_file")"
}

_run_env_check() {
  local reason="$1"
  local summary="$2"
  shift 2
  local log_file
  log_file="$(_auth_env_log_path)"
  if "$@" >"$log_file" 2>&1; then
    rm -f "$log_file"
    return 0
  fi
  _emit_env_failure "$reason" "$summary" "$log_file"
  return 1
}

_run_env_check "environment_python_failed" "Python 环境检查失败,详见 auth_log_file" _check_env_python || exit 1
_run_env_check "environment_playwright_failed" "Playwright Chromium 环境检查失败,详见 auth_log_file" _check_env_playwright || exit 1

exec "$PYTHON_BIN" "$SCRIPT_DIR/check_cookies.py" "$@"
