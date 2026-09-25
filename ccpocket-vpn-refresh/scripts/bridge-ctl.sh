#!/usr/bin/env bash
# Unified lifecycle management for @ccpocket/bridge.
#
# Subcommands:
#   start       Start bridge as a background daemon using current VPN IP
#   stop        Stop the running bridge (if any)
#   restart     stop + start
#   status      Report PID, URL, last refresh time; also calls out drift
#   logs        tail -f bridge.log
#   qr          Print the most recent QR block from bridge.log
#   doctor      Active health audit: flags auth mismatches, key drift,
#               IP drift, foreign launcher takeover
#   reset-pair  Purposeful pair regeneration: stop → start (using config's
#               current api_key) → print new QR. User must unpair on phone.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/log.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/state.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/discover.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/claude-env.sh"

SUBCOMMAND="${1:-}"

# Only `status` tolerates a missing config; every other subcommand needs one.
load_config_if_present=true
if [ "$SUBCOMMAND" != "status" ]; then
  require_config
fi
if [ ! -f "$CONFIG_FILE" ]; then
  load_config_if_present=false
fi

if $load_config_if_present; then
  IFACE=$(config_get vpn_interface)
  PORT=$(config_get bridge_port)
  API_KEY=$(config_get bridge_api_key)
  BRIDGE_LOG=$(config_get bridge_log)
  PID_FILE=$(config_get bridge_pid_file)
  PKG=$(config_get bridge_package)
  [ -z "$PKG" ] && PKG="@ccpocket/bridge@latest"
else
  IFACE=""; PORT="8765"; API_KEY=""; BRIDGE_LOG=""; PID_FILE=""; PKG="@ccpocket/bridge@latest"
fi

current_ip() {
  ifconfig "$IFACE" 2>/dev/null | awk '/inet / { print $2; exit }'
}

is_alive() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  [ -f "$PID_FILE" ] && cat "$PID_FILE" 2>/dev/null || true
}

_kill_tree() {
  local pid="$1"
  [ -z "$pid" ] && return 0
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill  -TERM    "$pid" 2>/dev/null || true
  sleep 1
  pkill -KILL -P "$pid" 2>/dev/null || true
  kill  -KILL    "$pid" 2>/dev/null || true
}

remove_ccpocket_launchd_job() {
  local domain="gui/$(id -u)"
  if launchctl print "$domain/com.ccpocket.bridge" >/dev/null 2>&1; then
    log_warn "Removing launchd job com.ccpocket.bridge so helper-managed env can take effect."
    launchctl remove com.ccpocket.bridge >/dev/null 2>&1 || \
      launchctl bootout "$domain/com.ccpocket.bridge" >/dev/null 2>&1 || true
    sleep 1
  fi
}

prepare_launchd_runtime() {
  local runtime_dir="$HOME/.ccpocket-helper/runtime"
  mkdir -p "$runtime_dir/lib"

  # launchd may be unable to execute scripts directly from iCloud-backed
  # AgentSync/ClaudeSync paths. Stage the tiny runtime locally first.
  cp -f "$SCRIPT_DIR/launch-bridge.sh" "$runtime_dir/launch-bridge.sh"
  cp -f "$SCRIPT_DIR/lib/claude-env.sh" "$runtime_dir/lib/claude-env.sh"
  chmod 700 "$runtime_dir" "$runtime_dir/lib"
  chmod 700 "$runtime_dir/launch-bridge.sh" "$runtime_dir/lib/claude-env.sh"

  printf '%s\n' "$runtime_dir/launch-bridge.sh"
}

CLAUDE_ENV_ARGS=()
collect_claude_env_args() {
  CLAUDE_ENV_ARGS=()

  local key
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
}

start_bridge_process() {
  local public_ws_url="$1"
  local npx_bin
  npx_bin="$(command -v npx || echo npx)"

  if [ "$(uname -s)" = "Darwin" ] && command -v launchctl >/dev/null 2>&1; then
    local launch_script
    launch_script="$(prepare_launchd_runtime)"
    launchctl submit -l com.ccpocket.bridge -- \
      /bin/bash "$launch_script" \
      "$public_ws_url" "$PORT" "$API_KEY" "$PKG" "$BRIDGE_LOG" "$npx_bin" \
      >> "$BRIDGE_LOG" 2>&1
    return 0
  fi

  (
    cd "$HOME"
    nohup env \
      BRIDGE_PUBLIC_WS_URL="$public_ws_url" \
      BRIDGE_PORT="$PORT" \
      BRIDGE_API_KEY="$API_KEY" \
      "${CLAUDE_ENV_ARGS[@]}" \
      "$npx_bin" --yes "$PKG" \
      > "$BRIDGE_LOG" 2>&1 &
    echo $! > "$PID_FILE"
    disown
  )
}

cmd_start() {
  local ip
  ip=$(current_ip)
  if [ -z "${ip:-}" ]; then
    log_error "Interface $IFACE has no IPv4 — is the VPN connected?"
    exit 4
  fi

  local existing
  existing=$(read_pid)
  if is_alive "$existing"; then
    log_warn "Bridge already running (PID $existing). Use 'restart' to apply changes."
    exit 0
  fi

  remove_ccpocket_launchd_job

  # Safety net: even if our PID file is stale, the port might be held by a
  # foreign bridge that we'd clobber. Probe before calling nohup.
  discover_port "$PORT"
  if [ "$DISCOVER_STATUS" = "occupied_bridge" ]; then
    log_warn "A bridge is already listening on port $PORT (PID $DISCOVER_PID)."
    log_warn "Run 'doctor' to decide how to handle it, or 'reset-pair' to replace it cleanly."
    exit 1
  elif [ "$DISCOVER_STATUS" = "occupied_other" ]; then
    log_error "Port $PORT held by non-bridge process $DISCOVER_PID: $DISCOVER_CMD"
    exit 5
  fi

  log_info "Starting bridge: ws://$ip:$PORT (interface $IFACE)"
  : > "$BRIDGE_LOG"  # truncate so 'qr' always finds the fresh one
  load_claude_env
  collect_claude_env_args

  start_bridge_process "ws://$ip:$PORT"

  local pid
  for _ in {1..30}; do
    sleep 1
    discover_port "$PORT"
    pid="${DISCOVER_PID:-$(read_pid)}"
    if is_alive "$pid" && curl -s -m 3 "http://127.0.0.1:$PORT/version" >/dev/null 2>&1; then
      break
    fi
  done
  [ -n "$pid" ] && echo "$pid" > "$PID_FILE"

  if is_alive "$pid" && curl -s -m 3 "http://127.0.0.1:$PORT/version" >/dev/null 2>&1; then
    log_ok "Bridge up (PID $pid)."
    state_set last_vpn_ip "$ip"
    state_set last_bridge_pid "$pid"
    state_set bridge_port "$PORT"
    state_set last_started_at "$(date -Iseconds 2>/dev/null || date +%FT%T%z)"
    # We started it ourselves — provenance is self.
    adoption_record self "" false
  else
    log_error "Bridge failed to become healthy. Last 20 log lines:"
    tail -20 "$BRIDGE_LOG" | sed 's/^/  /' >&2
    rm -f "$PID_FILE"
    remove_ccpocket_launchd_job
    exit 5
  fi
}

cmd_stop() {
  remove_ccpocket_launchd_job

  local pid
  pid=$(read_pid)
  if [ -z "$pid" ] || ! is_alive "$pid"; then
    log_info "No running bridge."
    rm -f "$PID_FILE"
    return 0
  fi
  log_info "Stopping bridge (PID $pid)…"
  _kill_tree "$pid"
  rm -f "$PID_FILE"
  log_ok "Stopped."
}

cmd_restart() {
  cmd_stop || true
  cmd_start
}

cmd_status() {
  hr
  if [ ! -f "$CONFIG_FILE" ]; then
    # Graceful "not installed yet" mode.
    printf "  %-20s %s\n" "Skill state:"  "not installed"
    printf "  %-20s %s\n" "Config file:"  "$CONFIG_FILE (missing)"

    local vpn
    vpn=$(bash "$SCRIPT_DIR/lib/detect-vpn.sh" 2>/dev/null || true)
    if [ -n "$vpn" ]; then
      printf "  %-20s %s\n" "Detected VPN:" "$(printf '%s' "$vpn" | awk '{printf "%s (%s)\n", $1, $2}' | paste -sd', ' -)"
    else
      printf "  %-20s %s\n" "Detected VPN:" "(none — connect 小米 VPN first)"
    fi

    # Probe port 8765 even without config so the user sees any stray bridge.
    discover_port "${PORT:-8765}"
    if [ "$DISCOVER_STATUS" = "occupied_bridge" ]; then
      printf "  %-20s ${_CLR_YELLOW}running (not managed)${_CLR_RESET} PID %s\n" "Bridge:" "$DISCOVER_PID"
    elif [ "$DISCOVER_STATUS" = "occupied_other" ]; then
      printf "  %-20s ${_CLR_YELLOW}port held by non-bridge${_CLR_RESET} PID %s\n" "Bridge:" "$DISCOVER_PID"
    else
      printf "  %-20s %s\n" "Bridge:" "not running"
    fi

    hr
    log_info "To start using this skill: bash $SCRIPT_DIR/install.sh"
    return 0
  fi

  # Normal path — config is present. Use discover + classify for honest picture.
  discover_port "$PORT"
  classify_port

  local ip last_ip last_refresh url
  ip=$(current_ip)
  last_ip=$(state_get last_vpn_ip 2>/dev/null || echo "-")
  last_refresh=$(state_get last_started_at 2>/dev/null || echo "-")
  url="ws://${ip:-?}:$PORT"

  printf "  %-20s %s\n" "Interface:"     "$IFACE"
  printf "  %-20s %s\n" "Current IP:"    "${ip:-<no IP / VPN down>}"
  printf "  %-20s %s\n" "Port:"          "$PORT"
  printf "  %-20s %s\n" "Connect URL:"   "$url"

  case "$CLASSIFY_KIND" in
    idle)
      printf "  %-20s ${_CLR_YELLOW}not running${_CLR_RESET}\n" "Bridge:"
      ;;
    managed)
      printf "  %-20s ${_CLR_GREEN}managed${_CLR_RESET} (PID %s, v%s)\n" "Bridge:" \
        "$DISCOVER_PID" "${DISCOVER_VERSION:-?}"
      ;;
    foreign)
      printf "  %-20s ${_CLR_YELLOW}foreign${_CLR_RESET} (PID %s, v%s)\n" "Bridge:" \
        "$DISCOVER_PID" "${DISCOVER_VERSION:-?}"
      printf "  %-20s %s\n" "  Why foreign:" "$CLASSIFY_NOTES"
      ;;
    stranger)
      printf "  %-20s ${_CLR_RED}port held by non-bridge process${_CLR_RESET}\n" "Bridge:"
      printf "  %-20s %s\n" "  Process:" "PID $DISCOVER_PID — $DISCOVER_CMD"
      ;;
  esac

  printf "  %-20s %s\n" "Last known IP:"   "$last_ip"
  printf "  %-20s %s\n" "Last started:"    "$last_refresh"

  local adoption
  adoption=$(adoption_kind 2>/dev/null || echo "")
  if [ "$adoption" = "foreign" ]; then
    local adopted_at home_hint key_synced
    adopted_at=$(state_get adopted_at 2>/dev/null || echo "-")
    home_hint=$(state_get adoption_launcher_home 2>/dev/null || echo "")
    key_synced=$(state_get adoption_key_synced 2>/dev/null || echo "?")
    printf "  %-20s %s  (key_synced=%s)\n" "Adopted at:" "$adopted_at" "$key_synced"
    [ -n "$home_hint" ] && printf "  %-20s %s\n" "Adopted from:" "$home_hint"
  fi
  hr
}

cmd_logs() {
  if [ ! -f "$BRIDGE_LOG" ]; then
    log_error "No bridge log at $BRIDGE_LOG"
    exit 1
  fi
  tail -f "$BRIDGE_LOG"
}

cmd_qr() {
  if [ ! -f "$BRIDGE_LOG" ]; then
    log_error "No bridge log at $BRIDGE_LOG"
    exit 1
  fi
  local start_line
  start_line=$(grep -n -E "Scan this QR|Bridge server|ccpocket://|ws://" "$BRIDGE_LOG" 2>/dev/null \
               | tail -1 | cut -d: -f1 || true)
  if [ -n "${start_line:-}" ]; then
    local from=$(( start_line - 40 ))
    [ "$from" -lt 1 ] && from=1
    sed -n "${from},\$p" "$BRIDGE_LOG"
  else
    log_warn "No startup marker found in log; showing last 60 lines:"
    tail -60 "$BRIDGE_LOG"
  fi
}

# ──────────────────────────────────────────────────────────────────────────────
# qr-image — render the current pairing deep link as a PNG and open it
#
# Terminal QR rendering is fragile (narrow windows, dark themes, non-UTF8
# terminals). This produces a crisp PNG that's easy to AirDrop/iMessage
# to the phone or scan from the Mac screen. Reuses the `qrcode` npm module
# already present in the bridge's npx cache — no extra install.
# ──────────────────────────────────────────────────────────────────────────────
cmd_qr_image() {
  if [ ! -f "$BRIDGE_LOG" ]; then
    log_error "No bridge log at $BRIDGE_LOG — start the bridge first."
    exit 1
  fi

  local deeplink
  deeplink=$(grep "Deep Link:" "$BRIDGE_LOG" 2>/dev/null | tail -1 \
             | sed -E 's/.*Deep Link: //' | tr -d '[:space:]')
  if [ -z "$deeplink" ]; then
    log_error "No 'Deep Link:' entry found in $BRIDGE_LOG."
    log_error "Bridge may not have finished starting. Try 'logs' to check."
    exit 1
  fi

  local qrmod
  qrmod=$(find "$HOME/.npm/_npx" -type d -path "*/node_modules/qrcode" 2>/dev/null | head -1)
  if [ -z "$qrmod" ]; then
    log_error "qrcode npm module not found under $HOME/.npm/_npx."
    log_error "Start the bridge at least once to populate the npx cache."
    exit 1
  fi

  local out_dir out_path
  out_dir=$(dirname "$BRIDGE_LOG")
  out_path="$out_dir/qr.png"

  log_info "Rendering QR for: $deeplink"
  node -e '
    const q = require(process.argv[1]);
    q.toFile(process.argv[2], process.argv[3], {
      errorCorrectionLevel: "H",
      width: 512,
      margin: 2,
    }, (err) => { if (err) { console.error(err.message); process.exit(1); } });
  ' "$qrmod" "$out_path" "$deeplink"

  log_ok "QR image saved: $out_path"

  if command -v open >/dev/null 2>&1; then
    open "$out_path" 2>/dev/null && log_info "Opened in default image viewer."
  fi
}

count_current_auth_rejections() {
  local lf="$1"
  awk '
    /\[ws\] Client connected/ || /\[ws\] Received:/ {
      rejections = 0
      next
    }
    /Client rejected: invalid token/ {
      rejections++
    }
    END {
      print rejections + 0
    }
  ' "$lf" 2>/dev/null || echo 0
}

# ──────────────────────────────────────────────────────────────────────────────
# doctor — active audit of the running bridge
#
# Each check has a severity (ok / warn / error) and prints a suggested remedy.
# Intended as the first thing to run whenever the phone shows "reconnecting"
# or the user suspects something is off.
# ──────────────────────────────────────────────────────────────────────────────
cmd_doctor() {
  hr
  log_info "$(bold "Doctor — auditing bridge health")"
  hr

  local findings_warn=0 findings_err=0

  # Check 1: port classification
  discover_port "$PORT"
  classify_port
  discover_print_summary

  case "$CLASSIFY_KIND" in
    idle)
      log_error "[E1] Bridge is NOT running. Run: bridge-ctl.sh start"
      findings_err=$((findings_err + 1))
      hr
      printf "  Summary: %d error(s), %d warning(s)\n" "$findings_err" "$findings_warn"
      hr
      return 0
      ;;
    stranger)
      log_error "[E2] Port $PORT occupied by non-bridge process (PID $DISCOVER_PID)."
      log_error "      Free the port, then run: bridge-ctl.sh start"
      findings_err=$((findings_err + 1))
      hr
      return 0
      ;;
    foreign|managed)
      : # keep going
      ;;
  esac

  # Check 2: config's API key vs running process's API key
  if [ -n "$DISCOVER_API_KEY" ] && [ "$API_KEY" != "$DISCOVER_API_KEY" ]; then
    log_warn "[W1] API key drift detected."
    log_warn "      config.json: ${API_KEY:0:8}…${API_KEY: -4}"
    log_warn "      live bridge: ${DISCOVER_API_KEY:0:8}…${DISCOVER_API_KEY: -4}"
    log_warn "      → A restart via bridge-ctl.sh would start a new bridge with"
    log_warn "        config's key, which differs from the one the phone is paired to."
    log_warn "      Remedy: 'bridge-ctl.sh sync-from-live'  (inherit live key into config)"
    log_warn "           or: 'bridge-ctl.sh reset-pair'      (restart + user re-pairs phone)"
    findings_warn=$((findings_warn + 1))
  fi

  # Check 3: bridge's HOME vs current $HOME (foreign launcher detection)
  if [ -n "$DISCOVER_HOME" ] && [ "$DISCOVER_HOME" != "$HOME" ]; then
    log_warn "[W2] Bridge was started under a different HOME ($DISCOVER_HOME)."
    log_warn "      This means another process/launcher (eval harness, script, etc.) owns it."
    log_warn "      If that launcher re-runs, it may spawn a new bridge with a new random key"
    log_warn "      and your phone pairing will break again. Consider disabling that launcher."
    findings_warn=$((findings_warn + 1))
  fi

  # Check 4: BRIDGE_PUBLIC_WS_URL vs current VPN IP
  local cur_ip advertised_ip
  cur_ip=$(current_ip)
  if [ -n "$DISCOVER_WS_URL" ]; then
    advertised_ip=$(printf '%s' "$DISCOVER_WS_URL" | sed -En 's|^ws://([^:/]+).*|\1|p')
    if [ -n "$advertised_ip" ] && [ -n "$cur_ip" ] && [ "$advertised_ip" != "$cur_ip" ]; then
      log_warn "[W3] WS URL advertises $advertised_ip but current VPN IP is $cur_ip."
      log_warn "      Phone may be trying to reach a stale IP. Remedy: refresh.sh"
      findings_warn=$((findings_warn + 1))
    fi
  fi

  # Check 5: log scan for auth rejections.
  #
  # We scan two kinds of log files:
  #   - our helper's bridge.log (if this is a bridge we started)
  #   - any .log file the live bridge has open (via lsof) — covers foreign
  #     bridges that write to a launcher-chosen path like
  #     ~/eval-workspace/.../bridge.log
  local -a log_candidates=()
  [ -f "$BRIDGE_LOG" ] && log_candidates+=("$BRIDGE_LOG")
  if [ -n "$DISCOVER_PID" ]; then
    while IFS= read -r lf; do
      [ -n "$lf" ] && log_candidates+=("$lf")
    done < <(lsof -p "$DISCOVER_PID" 2>/dev/null | awk '$NF ~ /\.log$/ { print $NF }' | sort -u)
  fi

  if [ "${#log_candidates[@]}" -gt 0 ]; then
    local reject_total=0 scanned=""
    local seen="" lf n
    for lf in "${log_candidates[@]}"; do
      [ -f "$lf" ] || continue
      case ":$seen:" in *":$lf:"*) continue ;; esac  # dedupe
      seen="$seen:$lf"
      n=$(count_current_auth_rejections "$lf")
      n=$(printf '%s' "$n" | tr -cd '0-9')
      [ -z "$n" ] && n=0
      if [ "$n" -gt 0 ]; then
        scanned="$scanned\n      $lf: $n current rejection(s)"
      fi
      reject_total=$((reject_total + n))
    done

    if [ "$reject_total" -ge 5 ]; then
      log_error "[E3] Bridge log shows $reject_total current 'Client rejected: invalid token' entries."
      printf "%b\n" "$scanned" >&2
      log_error "      The phone's stored token does NOT match the live bridge's key."
      log_error "      Remedy: 'bridge-ctl.sh reset-pair' → user unpairs in CC Pocket app → scans new QR."
      findings_err=$((findings_err + 1))
    elif [ "$reject_total" -gt 0 ]; then
      log_warn "[W4] Bridge log shows $reject_total current auth rejection(s) — low rate, but worth noting."
      findings_warn=$((findings_warn + 1))
    fi
  fi

  # Check 6: adoption metadata consistency
  local adoption
  adoption=$(adoption_kind 2>/dev/null || echo "")
  if [ "$adoption" = "foreign" ] && [ "$CLASSIFY_KIND" = "managed" ]; then
    log_info "[I1] State marked 'foreign' but live bridge now matches config — adoption stable."
  fi

  hr
  if [ "$findings_err" -eq 0 ] && [ "$findings_warn" -eq 0 ]; then
    log_ok "All checks passed. Bridge is healthy."
  else
    printf "  Summary: %d error(s), %d warning(s).\n" "$findings_err" "$findings_warn"
    if [ "$findings_err" -gt 0 ]; then
      printf "  The errors above point to why the phone may be stuck in 'reconnecting'.\n"
    fi
  fi
  hr
}

# ──────────────────────────────────────────────────────────────────────────────
# sync-from-live — inherit the live bridge's API key into config.json
#
# Non-destructive. Use when doctor flags W1 (key drift) and you want to preserve
# the existing phone pairing. After this, a future restart will use the key the
# phone already knows.
# ──────────────────────────────────────────────────────────────────────────────
cmd_sync_from_live() {
  discover_port "$PORT"
  if [ "$DISCOVER_STATUS" != "occupied_bridge" ]; then
    log_error "No live bridge on port $PORT to sync from."
    exit 1
  fi
  if [ -z "$DISCOVER_API_KEY" ]; then
    log_error "Could not read live bridge's BRIDGE_API_KEY (ps eww gave nothing)."
    log_error "Try running without sandbox / as the same user that launched the bridge."
    exit 1
  fi
  if [ "$API_KEY" = "$DISCOVER_API_KEY" ]; then
    echo "$DISCOVER_PID" > "$PID_FILE"
    state_set last_bridge_pid "$DISCOVER_PID"
    [ -n "$(current_ip)" ] && state_set last_vpn_ip "$(current_ip)"
    adoption_record foreign "${DISCOVER_HOME:-}" true
    log_ok "Keys already match — bridge PID re-tracked as $DISCOVER_PID."
    return 0
  fi
  log_info "Inheriting live bridge's key into config.json…"
  log_info "  was:  ${API_KEY:0:8}…${API_KEY: -4}"
  log_info "  now:  ${DISCOVER_API_KEY:0:8}…${DISCOVER_API_KEY: -4}"
  json_set "$CONFIG_FILE" bridge_api_key "$DISCOVER_API_KEY"
  adoption_record foreign "${DISCOVER_HOME:-}" true
  echo "$DISCOVER_PID" > "$PID_FILE"
  state_set last_bridge_pid "$DISCOVER_PID"
  [ -n "$(current_ip)" ] && state_set last_vpn_ip "$(current_ip)"
  log_ok "Synced. Phone pairing preserved; future restarts will use this key."
}

# ──────────────────────────────────────────────────────────────────────────────
# reset-pair — force a pairing regeneration
#
# Destructive by design: kills the current bridge, starts a new one with
# config.json's current api_key, prints the new QR. User must unpair the old
# entry in CC Pocket and scan the new QR.
#
# Use when the phone's stored token is unrecoverable (doctor's E3) and you
# don't care about preserving the old pairing — cleanest reset.
# ──────────────────────────────────────────────────────────────────────────────
cmd_reset_pair() {
  log_warn "$(bold "reset-pair is destructive — the current bridge will be killed.")"
  log_warn "You WILL need to:"
  log_warn "  1) Open CC Pocket on iPhone"
  log_warn "  2) Delete the existing pairing entry for this Mac"
  log_warn "  3) Scan the new QR printed at the end of this command"
  hr

  # Stop whatever's on the port (ours or foreign — doesn't matter, we're
  # replacing it). Use discover to get the actual live PID rather than trusting
  # our PID file.
  discover_port "$PORT"
  if [ "$DISCOVER_STATUS" = "occupied_bridge" ] && [ -n "$DISCOVER_PID" ]; then
    log_info "Killing bridge PID ${DISCOVER_PID}..."
    _kill_tree "$DISCOVER_PID"
    # If our PID file pointed to a different PID, clean it too.
    local ours
    ours=$(read_pid)
    [ -n "$ours" ] && [ "$ours" != "$DISCOVER_PID" ] && _kill_tree "$ours"
  elif [ "$DISCOVER_STATUS" = "occupied_other" ]; then
    log_error "Port $PORT held by non-bridge process — refusing to kill."
    exit 5
  fi
  rm -f "$PID_FILE"
  sleep 1

  # Start fresh using config's current api_key.
  cmd_start

  hr
  log_info "New QR (unpair old entry on phone, then scan this):"
  hr
  cmd_qr
  hr
  log_info "After re-pairing from iPhone, run 'bridge-ctl.sh doctor' to confirm health."
}

case "${1:-}" in
  start)          cmd_start ;;
  stop)           cmd_stop ;;
  restart)        cmd_restart ;;
  status)         cmd_status ;;
  logs)           cmd_logs ;;
  qr)             cmd_qr ;;
  qr-image)       cmd_qr_image ;;
  doctor)         cmd_doctor ;;
  sync-from-live) cmd_sync_from_live ;;
  reset-pair)     cmd_reset_pair ;;
  "" | -h | --help)
    cat <<EOF
Usage: $(basename "$0") <subcommand>

  start            Start bridge as a background daemon
  stop             Stop the running bridge
  restart          Stop then start
  status           Show bridge state (uses port discovery)
  logs             Tail the bridge log
  qr               Print the last printed QR (ASCII, from the log)
  qr-image         Render the current pairing deep link as a PNG and open it
  doctor           Audit bridge health — flags auth mismatches, drift, stale IP
  sync-from-live   Inherit live bridge's API key into config (non-destructive)
  reset-pair       Restart bridge with config's key + print new QR (user re-pairs)
EOF
    ;;
  *)
    log_error "Unknown subcommand: $1"
    exit 2
    ;;
esac
