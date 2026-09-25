#!/usr/bin/env bash
# Remove everything this skill created on the local machine.
#
# What it does:
#   1. Stops the running bridge (if any)
#   2. Deletes ~/.ccpocket-helper/ (config, state, logs, pid file)
#
# What it does NOT do:
#   - Delete the skill directory itself (that's the user's to manage)
#   - Uninstall Node.js or any npm cache

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/log.sh"

HELPER_DIR="$HOME/.ccpocket-helper"

log_info "Uninstalling ccpocket-vpn-refresh state…"

# 1. Stop bridge (best effort)
if [ -f "$HELPER_DIR/config.json" ]; then
  if ! bash "$SCRIPT_DIR/bridge-ctl.sh" stop; then
    log_warn "bridge-ctl.sh stop reported an error — continuing anyway."
  fi
fi

# 2. Report (but do NOT kill) bridges we don't own.
# We used to `pkill -f ccpocket-bridge` here to clean up orphans, but that
# indiscriminately killed any ccpocket-bridge the user was running outside
# this skill (for example, from a plain `npx @ccpocket/bridge@latest` in a
# terminal). That is not our process to kill — uninstalling *this skill*
# should never touch bridges the skill did not start.
# If the user wants to clean up non-skill-managed bridges, they can do so
# themselves: `pkill -f ccpocket-bridge`.
if pgrep -f 'ccpocket-bridge' >/dev/null 2>&1; then
  log_info "Note: there are still ccpocket-bridge processes running — those were"
  log_info "  not started by this skill, so uninstall is leaving them alone."
  log_info "  If you want to stop them too: pkill -f ccpocket-bridge"
fi

# 3. Delete state dir
if [ -d "$HELPER_DIR" ]; then
  rm -rf "$HELPER_DIR"
  log_ok "Removed $HELPER_DIR"
else
  log_info "$HELPER_DIR already absent."
fi

hr
log_ok "Uninstalled."
log_info "The skill directory itself ($SKILL_DIR) is untouched — delete manually if desired."
