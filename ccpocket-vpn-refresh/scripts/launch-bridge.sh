#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/claude-env.sh"

PUBLIC_WS_URL="${1:?public ws url required}"
PORT="${2:?port required}"
API_KEY="${3:?api key required}"
PKG="${4:?bridge package required}"
LOG_PATH="${5:?log path required}"
NPX_BIN="${6:-npx}"

exec >> "$LOG_PATH" 2>&1
export PATH="$(dirname "$NPX_BIN"):/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

load_claude_env

CLAUDE_ENV_ARGS=()
for key in \
  ANTHROPIC_BASE_URL \
  ANTHROPIC_AUTH_TOKEN \
  ANTHROPIC_API_KEY \
  ANTHROPIC_DEFAULT_HAIKU_MODEL \
  ANTHROPIC_DEFAULT_SONNET_MODEL \
  ANTHROPIC_DEFAULT_OPUS_MODEL
do
  if [ "${!key+x}" = "x" ]; then
    CLAUDE_ENV_ARGS+=("$key=${!key}")
  fi
done

while IFS= read -r key; do
  case "$key" in
    CLAUDE_CODE_*) CLAUDE_ENV_ARGS+=("$key=${!key}") ;;
  esac
done < <(compgen -e)

cd "$HOME"
exec env \
  BRIDGE_PUBLIC_WS_URL="$PUBLIC_WS_URL" \
  BRIDGE_PORT="$PORT" \
  BRIDGE_API_KEY="$API_KEY" \
  "${CLAUDE_ENV_ARGS[@]}" \
  "$NPX_BIN" --yes "$PKG"
