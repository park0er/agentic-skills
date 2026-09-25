#!/usr/bin/env bash
# First-run installer for ccpocket-vpn-refresh.
# Idempotent: safe to re-run.
#
# Preflight:
#   Before generating any key or writing any config, probe port 8765. If
#   a live bridge is already running there (started by some other launcher
#   — think eval harness, a prior manual `npx @ccpocket/bridge`, etc.), we
#   MUST NOT clobber its key. The --adopt-mode flag decides what to do.
#
# Flags:
#   --interface utun4       Skip VPN auto-detection, use this interface
#   --port 8765             Override the default bridge port
#   --api-key KEY           Use this BRIDGE_API_KEY (default: random 32-hex)
#   --adopt-mode MODE       How to handle an existing bridge on the port:
#                             sync    (default) inherit its API key into config;
#                                     phone pairing survives across future
#                                     helper-managed restarts
#                             keep    keep config's own key, just track the PID;
#                                     ⚠ a future restart will break pairing
#                             replace kill it, start a fresh helper-managed
#                                     bridge; user must re-pair from phone
#   --no-smoke-test         Skip the "bridge starts up correctly" sanity check
#   --force                 Overwrite existing config without asking
#
# Exit codes:
#   0   success
#   2   unknown flag / ambiguous VPN interface
#   3   Node.js missing or too old
#   4   VPN not connected
#   5   port 8765 held by a non-bridge process — refuse to proceed
#   6   adopt-mode=replace needs explicit --force-kill to kill foreign bridge

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/log.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/state.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/discover.sh"

IFACE_OVERRIDE=""
PORT="8765"
API_KEY=""
ADOPT_MODE="sync"
SKIP_SMOKE=0
FORCE=0
FORCE_KILL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --interface)     IFACE_OVERRIDE="$2"; shift 2 ;;
    --port)          PORT="$2"; shift 2 ;;
    --api-key)       API_KEY="$2"; shift 2 ;;
    --adopt-mode)    ADOPT_MODE="$2"; shift 2 ;;
    --no-smoke-test) SKIP_SMOKE=1; shift ;;
    --force)         FORCE=1; shift ;;
    --force-kill)    FORCE_KILL=1; shift ;;
    -h|--help)
      sed -n '2,33p' "$0"; exit 0 ;;
    *) log_error "Unknown flag: $1"; exit 2 ;;
  esac
done

case "$ADOPT_MODE" in
  sync|keep|replace) : ;;
  *) log_error "Invalid --adopt-mode: $ADOPT_MODE (want sync|keep|replace)"; exit 2 ;;
esac

log_info "$(bold "ccpocket-vpn-refresh installer")"
hr

# ──────────────────────────────────────────────────────────────────────────────
# 1. Node check
# ──────────────────────────────────────────────────────────────────────────────
if ! command -v node >/dev/null 2>&1; then
  log_error "Node.js is not installed. Install Node 18+ first:"
  log_error "  brew install node       # if you have Homebrew"
  log_error "  or https://nodejs.org/  # official installer"
  exit 3
fi
node_ver=$(node -v 2>/dev/null | tr -d 'v' | cut -d. -f1)
if [ -z "$node_ver" ] || [ "$node_ver" -lt 18 ]; then
  log_error "Node.js 18+ required. Detected: $(node -v 2>/dev/null || echo none)"
  exit 3
fi
log_ok "Node.js $(node -v) detected."

if ! command -v npx >/dev/null 2>&1; then
  log_error "npx not found — install npm along with Node."
  exit 3
fi
log_ok "npx detected."

# ──────────────────────────────────────────────────────────────────────────────
# 2. State dir + tmp
# ──────────────────────────────────────────────────────────────────────────────
mkdir -p "$HELPER_DIR/tmp"
export TMPDIR="$HELPER_DIR/tmp"
log_ok "State dir: $HELPER_DIR  (TMPDIR redirected here)"

# ──────────────────────────────────────────────────────────────────────────────
# 3. Port discovery — before touching keys or config
#
# This is the big change vs. the old installer. Old flow: generate random key →
# write config → try to start bridge → maybe fail. New flow: find out what's
# already on the port first, then decide whether to generate a key at all.
# ──────────────────────────────────────────────────────────────────────────────
log_info "Probing port $PORT before generating any key…"
discover_port "$PORT"

INHERIT_KEY=""
INHERIT_WS_URL=""
INHERIT_HOME=""
ADOPTION_KIND="self"

case "$DISCOVER_STATUS" in
  idle)
    log_ok "Port $PORT is idle — proceeding with a clean install."
    ;;

  occupied_other)
    log_error "Port $PORT is held by something that isn't a ccpocket-bridge:"
    log_error "  PID $DISCOVER_PID: ${DISCOVER_CMD:-unknown}"
    log_error "Free the port (kill that process, or install.sh --port N) and re-run."
    exit 5
    ;;

  occupied_bridge)
    log_warn "A ccpocket-bridge is ALREADY running on port $PORT:"
    [ -n "$DISCOVER_PID" ]     && log_warn "  PID:          $DISCOVER_PID (PPID $DISCOVER_PPID)"
    [ -n "$DISCOVER_VERSION" ] && log_warn "  Version:      $DISCOVER_VERSION, uptime ${DISCOVER_UPTIME:-?}s"
    [ -n "$DISCOVER_API_KEY" ] && log_warn "  Live API key: ${DISCOVER_API_KEY:0:8}…${DISCOVER_API_KEY: -4}"
    [ -n "$DISCOVER_WS_URL" ]  && log_warn "  Live WS URL:  $DISCOVER_WS_URL"
    [ -n "$DISCOVER_HOME" ]    && log_warn "  Started under HOME=$DISCOVER_HOME"
    log_warn "Applying --adopt-mode=$ADOPT_MODE."

    case "$ADOPT_MODE" in
      sync)
        if [ -z "$DISCOVER_API_KEY" ]; then
          log_warn "Live bridge's API key couldn't be read (ps eww gave nothing)."
          log_warn "Falling back to adopt-mode=keep semantics. Run with --adopt-mode=replace"
          log_warn "if you want a clean re-pair instead."
          ADOPT_MODE="keep"
        else
          INHERIT_KEY="$DISCOVER_API_KEY"
          INHERIT_WS_URL="$DISCOVER_WS_URL"
          INHERIT_HOME="$DISCOVER_HOME"
          ADOPTION_KIND="foreign"
          log_ok "Will inherit the live bridge's key into our config (pairing preserved)."
        fi
        ;;
      keep)
        ADOPTION_KIND="foreign"
        log_warn "Will NOT inherit. Config gets its own fresh key; next restart breaks pairing."
        ;;
      replace)
        if [ "$FORCE_KILL" -eq 0 ]; then
          log_error "--adopt-mode=replace kills the running bridge (PID $DISCOVER_PID)."
          log_error "This WILL break the phone's current pairing — user must re-pair from iPhone."
          log_error "Re-run with --force-kill to confirm."
          exit 6
        fi
        log_warn "Killing live bridge (PID $DISCOVER_PID) per --adopt-mode=replace…"
        kill -TERM "$DISCOVER_PID" 2>/dev/null || true
        pkill -TERM -P "$DISCOVER_PID" 2>/dev/null || true
        sleep 1
        kill -KILL "$DISCOVER_PID" 2>/dev/null || true
        pkill -KILL -P "$DISCOVER_PID" 2>/dev/null || true
        # Re-probe so the rest of the script sees idle.
        discover_port "$PORT"
        if [ "$DISCOVER_STATUS" != "idle" ]; then
          log_error "Port still occupied after kill. Aborting."
          exit 5
        fi
        log_ok "Port cleared."
        ;;
    esac
    ;;
esac

# ──────────────────────────────────────────────────────────────────────────────
# 4. VPN interface detection
# ──────────────────────────────────────────────────────────────────────────────
if [ -n "$IFACE_OVERRIDE" ]; then
  IFACE="$IFACE_OVERRIDE"
  IP=$(ifconfig "$IFACE" 2>/dev/null | awk '/inet / { print $2; exit }')
  if [ -z "${IP:-}" ]; then
    log_error "Interface $IFACE has no IPv4 address. Is the VPN connected?"
    exit 4
  fi
  log_ok "Using interface (override): $IFACE ($IP)"
else
  log_info "Auto-detecting VPN interfaces…"
  candidates=$(bash "$SCRIPT_DIR/lib/detect-vpn.sh")
  count=$(printf "%s" "$candidates" | grep -c . || true)
  case "$count" in
    0)
      log_error "No utun interface with a private IP found."
      log_error "Connect to the corporate VPN first, then re-run this installer."
      exit 4
      ;;
    1)
      IFACE=$(printf "%s" "$candidates" | awk '{print $1}')
      IP=$(printf "%s" "$candidates" | awk '{print $2}')
      log_ok "Picked single candidate: $IFACE ($IP)"
      ;;
    *)
      log_warn "Multiple VPN interfaces found — cannot auto-pick."
      printf "%s\n" "$candidates" | while IFS=$'\t' read -r i ip; do
        printf "  - %s (%s)\n" "$i" "$ip"
      done
      log_error "Re-run with --interface <name>, e.g. --interface $(printf "%s" "$candidates" | head -1 | awk '{print $1}')"
      exit 2
      ;;
  esac
fi

# Cross-check: if we inherited a WS URL from a foreign bridge, warn if its IP
# doesn't match our current VPN IP. That's a separate signal worth surfacing.
if [ -n "$INHERIT_WS_URL" ]; then
  live_ip=$(printf '%s' "$INHERIT_WS_URL" | sed -En 's|^ws://([^:/]+).*|\1|p')
  if [ -n "$live_ip" ] && [ "$live_ip" != "$IP" ]; then
    log_warn "Heads-up: live bridge advertises $live_ip, but current VPN IP is $IP."
    log_warn "If you see 'reconnecting' on the phone, run refresh.sh to update the URL."
  fi
fi

# ──────────────────────────────────────────────────────────────────────────────
# 5. API key resolution
#
# Three sources, in priority order:
#   a) --api-key flag (explicit override)
#   b) inherited from a foreign bridge (adopt-mode=sync)
#   c) existing config key (idempotent re-run)
#   d) freshly generated random 32-hex
# ──────────────────────────────────────────────────────────────────────────────
if [ -z "$API_KEY" ]; then
  if [ -n "$INHERIT_KEY" ]; then
    API_KEY="$INHERIT_KEY"
    log_ok "Using inherited key from live bridge: ${API_KEY:0:6}…${API_KEY: -4}"
  else
    existing_key=""
    if [ -f "$CONFIG_FILE" ]; then
      existing_key=$(config_get bridge_api_key 2>/dev/null || true)
    fi
    if [ -n "$existing_key" ] && [ "$FORCE" -eq 0 ]; then
      API_KEY="$existing_key"
      log_info "Reusing existing BRIDGE_API_KEY from config."
    else
      API_KEY=$(node -e "console.log(require('crypto').randomBytes(16).toString('hex'))")
      log_ok "Generated BRIDGE_API_KEY: ${API_KEY:0:6}…${API_KEY: -4}"
    fi
  fi
fi

# ──────────────────────────────────────────────────────────────────────────────
# 6. Write config atomically
# ──────────────────────────────────────────────────────────────────────────────
tmp_config=$(mktemp "$TMPDIR/config.XXXXXX")
sed \
  -e "s|__VPN_INTERFACE__|$IFACE|g" \
  -e "s|__BRIDGE_API_KEY__|$API_KEY|g" \
  -e "s|__HOME__|$HOME|g" \
  "$SKILL_DIR/defaults/config.json.template" > "$tmp_config"
if [ "$PORT" != "8765" ]; then
  node "$SCRIPT_DIR/lib/json.js" set "$tmp_config" bridge_port "$PORT"
fi
mv "$tmp_config" "$CONFIG_FILE"
log_ok "Wrote config: $CONFIG_FILE"

# ──────────────────────────────────────────────────────────────────────────────
# 7. Record adoption provenance in state.json
# ──────────────────────────────────────────────────────────────────────────────
if [ "$ADOPTION_KIND" = "foreign" ]; then
  key_synced_str=$([ -n "$INHERIT_KEY" ] && echo true || echo false)
  adoption_record foreign "$INHERIT_HOME" "$key_synced_str"

  # If the foreign bridge is still alive AND we're in sync/keep mode, record
  # its PID so doctor/status recognize it as "ours now".
  if [ "$DISCOVER_STATUS" = "occupied_bridge" ] && [ -n "$DISCOVER_PID" ]; then
    pid_file_path=$(config_get bridge_pid_file)
    echo "$DISCOVER_PID" > "$pid_file_path"
    state_set last_bridge_pid "$DISCOVER_PID"
    state_set last_vpn_ip "$IP"
    log_ok "Adopted live bridge (PID $DISCOVER_PID) into helper state."
  fi
else
  adoption_record self "" false
fi

# ──────────────────────────────────────────────────────────────────────────────
# 8. Smoke test
#
# Skipped when we adopted a live bridge — it's already responding, no need
# to bounce it. Also skipped if --no-smoke-test.
# ──────────────────────────────────────────────────────────────────────────────
if [ "$SKIP_SMOKE" -eq 1 ]; then
  log_warn "Skipping smoke test (--no-smoke-test)."
elif [ "$ADOPTION_KIND" = "foreign" ] && [ "$DISCOVER_STATUS" = "occupied_bridge" ]; then
  log_info "Skipping smoke test — live bridge already responding on /version."
else
  log_info "Running smoke test: start bridge → probe /version → stop."
  export BRIDGE_PUBLIC_WS_URL="ws://$IP:$PORT"
  export BRIDGE_PORT="$PORT"
  export BRIDGE_API_KEY="$API_KEY"
  TEST_LOG=$(mktemp "$TMPDIR/smoketest.XXXXXX")
  (nohup npx @ccpocket/bridge@latest > "$TEST_LOG" 2>&1 &) &
  sleep 6
  test_pid=$(pgrep -f 'ccpocket-bridge' | head -1 || true)
  if [ -n "$test_pid" ] && curl -s -m 3 "http://127.0.0.1:$PORT/version" >/dev/null; then
    log_ok "Smoke test passed."
    kill "$test_pid" 2>/dev/null || true
    pkill -P "$test_pid" 2>/dev/null || true
  else
    log_warn "Smoke test failed — bridge did not respond on port $PORT."
    log_warn "Last 20 lines of bridge output:"
    tail -20 "$TEST_LOG" | sed 's/^/  /' >&2
    log_warn "This is often benign inside a sandbox (npm registry blocked); see references/troubleshooting.md"
  fi
  rm -f "$TEST_LOG"
fi

hr
log_ok "$(bold "Install complete.")"
if [ "$ADOPTION_KIND" = "foreign" ]; then
  log_info "Live bridge adopted. Run $(bold "bridge-ctl.sh doctor") if the phone still shows 'reconnecting'."
else
  log_info "Next: run $(bold "$SCRIPT_DIR/refresh.sh") (or tell Claude '刷新 bridge') to start the bridge."
fi
