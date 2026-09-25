#!/usr/bin/env bash
# Main entry point: detect VPN IP change + refresh bridge accordingly.
#
# This is the script the skill invokes on a typical user request like
# "VPN 重连了 刷新 bridge". It is idempotent and safe to run at any time.
#
# Decision matrix (post-discovery):
#   classify == idle                       -> start bridge (fresh or from last IP)
#   classify == managed + IP same          -> no-op
#   classify == managed + IP changed       -> restart with new IP (config key stays,
#                                             so phone pairing survives)
#   classify == foreign                    -> DO NOT RESTART (would break pairing);
#                                             point user at doctor
#   classify == stranger                   -> error out
#
# Exit codes:
#   0  ok
#   4  VPN not connected
#   5  port held by non-bridge process
#   7  foreign bridge detected — user action needed (run doctor)

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/log.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/state.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/discover.sh"

# First-run bootstrap: if config is missing, run the installer.
if [ ! -f "$CONFIG_FILE" ]; then
  log_warn "First run detected — no config at $CONFIG_FILE"
  log_info "Bootstrapping via install.sh…"
  hr
  if ! bash "$SCRIPT_DIR/install.sh"; then
    log_error "Install failed. Fix the error above and re-run refresh."
    exit $?
  fi
  hr
  log_info "Install done. Proceeding with refresh…"
fi

IFACE=$(config_get vpn_interface)
PORT=$(config_get bridge_port)
PID_FILE=$(config_get bridge_pid_file)

current_ip=$(ifconfig "$IFACE" 2>/dev/null | awk '/inet / { print $2; exit }')
if [ -z "${current_ip:-}" ]; then
  detected_vpn=$(bash "$SCRIPT_DIR/lib/detect-vpn.sh" 2>/dev/null | head -n1 || true)
  if [ -n "$detected_vpn" ]; then
    new_iface=$(printf '%s\n' "$detected_vpn" | awk '{print $1}')
    new_ip=$(printf '%s\n' "$detected_vpn" | awk '{print $2}')
    if [ -n "$new_iface" ] && [ -n "$new_ip" ] && [ "$new_iface" != "$IFACE" ]; then
      log_warn "Configured interface $IFACE has no IPv4, but VPN is up on $new_iface ($new_ip)."
      log_info "Updating config vpn_interface: $IFACE → $new_iface"
      json_set "$CONFIG_FILE" vpn_interface "$new_iface"
      IFACE="$new_iface"
      current_ip="$new_ip"
    fi
  fi
fi

if [ -z "${current_ip:-}" ]; then
  log_error "Interface $IFACE has no IPv4 address. Connect the VPN and try again."
  exit 4
fi

# Port-level truth before trusting PID file or state.
discover_port "$PORT"
classify_port

last_ip=$(state_get last_vpn_ip 2>/dev/null || true)

ip_state="same"
if [ -z "${last_ip:-}" ]; then
  ip_state="first_run"
elif [ "$current_ip" != "$last_ip" ]; then
  ip_state="changed"
fi

hr
log_info "VPN interface: $IFACE"
log_info "Current IP:    $current_ip"
log_info "Last known IP: ${last_ip:-<none>}"
log_info "Bridge:        $CLASSIFY_KIND${DISCOVER_PID:+ (PID $DISCOVER_PID)}"
log_info "IP state:      $ip_state"
hr

case "$CLASSIFY_KIND" in
  stranger)
    log_error "Port $PORT is held by a non-bridge process (PID $DISCOVER_PID)."
    log_error "Free the port, then re-run refresh."
    exit 5
    ;;

  foreign)
    log_warn "A bridge is running, but it's not (fully) managed by this helper."
    [ -n "$CLASSIFY_NOTES" ] && log_warn "  $CLASSIFY_NOTES"
    log_warn "Refusing to restart — doing so would break your iPhone's current pairing."
    log_warn "Run $(bold "bridge-ctl.sh doctor") for specific remedies. Usual choice:"
    log_warn "  • $(bold "bridge-ctl.sh sync-from-live")  — inherit live key, preserve pairing"
    log_warn "  • $(bold "bridge-ctl.sh reset-pair")      — clean restart; user re-pairs from phone"
    exit 7
    ;;

  idle)
    case "$ip_state" in
      same|first_run)
        log_info "Bridge is not running. Starting with current VPN IP ($current_ip)…"
        bash "$SCRIPT_DIR/bridge-ctl.sh" start
        log_info "Connect URL: ws://$current_ip:$PORT"
        if [ "$ip_state" = "first_run" ]; then
          log_info "Initial QR (scan once from the CC Pocket iPhone app):"
          hr
          bash "$SCRIPT_DIR/bridge-ctl.sh" qr
          hr
        else
          log_info "If iPhone was paired before with this key, it should reconnect on its own."
        fi
        ;;
      changed)
        log_info "Bridge not running and IP changed ($last_ip → $current_ip). Starting…"
        bash "$SCRIPT_DIR/bridge-ctl.sh" start
        log_info "New QR (re-scan from iPhone — the URL changed, old pairing is stale):"
        hr
        bash "$SCRIPT_DIR/bridge-ctl.sh" qr
        hr
        ;;
    esac
    ;;

  managed)
    case "$ip_state" in
      same)
        log_ok "Bridge healthy and IP unchanged — nothing to do."
        log_info "Connect URL: ws://$current_ip:$PORT"
        ;;
      changed)
        log_warn "VPN IP changed ($last_ip → $current_ip). Restarting bridge with same key…"
        bash "$SCRIPT_DIR/bridge-ctl.sh" restart
        log_info "New QR (same key as before; phone should auto-reconnect once URL updates):"
        hr
        bash "$SCRIPT_DIR/bridge-ctl.sh" qr
        hr
        log_info "If the iPhone app still shows 'reconnecting' after a few seconds, it may be"
        log_info "the old ws:// URL cached — tap the pairing entry to refresh, or re-scan the QR."
        ;;
      first_run)
        log_warn "Bridge is alive but state has no last_vpn_ip — recording it now."
        state_set last_vpn_ip "$current_ip"
        log_ok "State repaired. Bridge left running."
        ;;
    esac
    ;;
esac
