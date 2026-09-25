# shellcheck shell=bash
# Shared helpers for reading configuration and state files.
# Source after log.sh. Expects SKILL_DIR to be set by the caller.

HELPER_DIR="$HOME/.ccpocket-helper"
CONFIG_FILE="$HELPER_DIR/config.json"
STATE_FILE="$HELPER_DIR/state.json"

json_get() {
  # json_get <file> <key>  -> prints value (empty string if missing); exit 0 either way
  node "$SKILL_DIR/scripts/lib/json.js" get "$1" "$2"
}

json_set() {
  # json_set <file> <key> <value>  -> writes atomically
  node "$SKILL_DIR/scripts/lib/json.js" set "$1" "$2" "$3"
}

config_get() { json_get "$CONFIG_FILE" "$1"; }
state_get()  { json_get "$STATE_FILE"  "$1"; }
state_set()  { json_set "$STATE_FILE"  "$1" "$2"; }

require_config() {
  if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Config missing at $CONFIG_FILE — run install.sh first."
    return 1
  fi
}

# ------------------------------------------------------------------------------
# Adoption metadata
#
# When the helper adopts a bridge that it did not itself start (a "foreign"
# bridge discovered on port 8765 during install), it records who launched it,
# what env it inherited, and when the adoption happened. This lets status and
# doctor subcommands report the provenance honestly.
#
# json.js only handles top-level keys, so we flatten all adoption fields under
# the `adoption_*` prefix.
# ------------------------------------------------------------------------------

# adoption_record kind launcher_home key_synced
#   kind          : "foreign" | "self"   (self = we started the bridge)
#   launcher_home : $HOME of the launcher that created the bridge (foreign only)
#   key_synced    : "true" | "false"     whether config.api_key was rewritten to
#                                        match the running bridge
adoption_record() {
  local kind="${1:-self}"
  local launcher_home="${2:-}"
  local key_synced="${3:-false}"
  state_set adoption_kind "$kind"
  state_set adoption_key_synced "$key_synced"
  state_set adopted_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [ -n "$launcher_home" ]; then
    state_set adoption_launcher_home "$launcher_home"
  else
    node "$SKILL_DIR/scripts/lib/json.js" del "$STATE_FILE" adoption_launcher_home 2>/dev/null || true
  fi
}

adoption_clear() {
  for k in adoption_kind adoption_key_synced adoption_launcher_home adopted_at; do
    node "$SKILL_DIR/scripts/lib/json.js" del "$STATE_FILE" "$k" 2>/dev/null || true
  done
}

adoption_kind() { state_get adoption_kind; }
