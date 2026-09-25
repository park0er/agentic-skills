# shellcheck shell=bash
# Port discovery + classification for the bridge.
#
# Source this after log.sh and state.sh. Expects $PORT (or caller passes a port
# to discover_port). Exports DISCOVER_* globals describing whatever is on the
# port, and (via classify_port) CLASSIFY_* globals describing whether that
# thing belongs to us, belongs to somebody else, or isn't even a bridge.
#
# Why separate discover from classify:
#   - discover_port only inspects the system (lsof / ps / curl). It's usable
#     during install (before config exists) AND during refresh.
#   - classify_port consults config + state to decide "is this my bridge?"
#     which is the question that actually drives UX branches.

# ------------------------------------------------------------------------------
# discover_port [port]
#
# Populates:
#   DISCOVER_STATUS         "idle" | "occupied_bridge" | "occupied_other"
#   DISCOVER_PID            PID of the listener (empty if idle)
#   DISCOVER_CMD            full command line of the listener
#   DISCOVER_PPID           parent PID (1 = detached daemon)
#   DISCOVER_API_KEY        BRIDGE_API_KEY from the live process env (if bridge)
#   DISCOVER_WS_URL         BRIDGE_PUBLIC_WS_URL from the live env (if bridge)
#   DISCOVER_HOME           $HOME inherited by the live bridge (if bridge)
#   DISCOVER_PWD            $PWD at launch (if bridge)
#   DISCOVER_VERSION        version string from /version (if bridge)
#   DISCOVER_UPTIME         uptime seconds from /version (if bridge)
# ------------------------------------------------------------------------------
discover_port() {
  local port="${1:-${PORT:-8765}}"
  DISCOVER_STATUS="idle"
  DISCOVER_PID=""
  DISCOVER_CMD=""
  DISCOVER_PPID=""
  DISCOVER_API_KEY=""
  DISCOVER_WS_URL=""
  DISCOVER_HOME=""
  DISCOVER_PWD=""
  DISCOVER_VERSION=""
  DISCOVER_UPTIME=""

  # Who's listening on the port? lsof is authoritative; if it fails (e.g. sandbox)
  # fall back to `curl /version` to detect liveness without a PID.
  local pid=""
  pid=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null \
        | awk 'NR>1 {print $2; exit}' || true)

  # Fallback: lsof might be blocked in some sandboxes. Probe /version directly.
  if [ -z "$pid" ]; then
    local probe
    probe=$(curl -s -m 2 "http://127.0.0.1:$port/version" 2>/dev/null || true)
    if [ -n "$probe" ] && printf '%s' "$probe" | grep -q '"nodeVersion"'; then
      # It's a bridge but we can't see its PID. Record what we can.
      DISCOVER_STATUS="occupied_bridge"
      DISCOVER_VERSION=$(printf '%s' "$probe" | sed -En 's/.*"version":"([^"]+)".*/\1/p')
      DISCOVER_UPTIME=$(printf '%s' "$probe" | sed -En 's/.*"uptime":([0-9]+).*/\1/p')
    fi
    return 0
  fi

  DISCOVER_PID="$pid"
  DISCOVER_STATUS="occupied_other"
  DISCOVER_CMD=$(ps -o command= -p "$pid" 2>/dev/null || true)
  DISCOVER_PPID=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ' || true)

  # Is it a ccpocket-bridge? Two gates: the command line mentions it, OR the
  # /version endpoint responds like one. Either is sufficient; we cross-check
  # only to be defensive against unrelated Node processes on the same port.
  local probe
  probe=$(curl -s -m 2 "http://127.0.0.1:$port/version" 2>/dev/null || true)
  local cmd_is_bridge=0
  [ -n "$DISCOVER_CMD" ] && printf '%s' "$DISCOVER_CMD" | grep -q 'ccpocket-bridge' && cmd_is_bridge=1
  local probe_is_bridge=0
  [ -n "$probe" ] && printf '%s' "$probe" | grep -q '"nodeVersion"' && probe_is_bridge=1

  if [ "$cmd_is_bridge" -eq 1 ] || [ "$probe_is_bridge" -eq 1 ]; then
    DISCOVER_STATUS="occupied_bridge"
    if [ "$probe_is_bridge" -eq 1 ]; then
      DISCOVER_VERSION=$(printf '%s' "$probe" | sed -En 's/.*"version":"([^"]+)".*/\1/p')
      DISCOVER_UPTIME=$(printf '%s' "$probe" | sed -En 's/.*"uptime":([0-9]+).*/\1/p')
    fi

    # Extract env. `ps eww` works when the caller owns the process (same UID),
    # which is our expected case — the user is always running their own bridge.
    local env_dump
    env_dump=$(ps eww "$pid" 2>/dev/null || true)
    if [ -n "$env_dump" ]; then
      DISCOVER_API_KEY=$(printf '%s' "$env_dump" | tr ' ' '\n' \
                          | awk -F= '/^BRIDGE_API_KEY=/ { sub(/^BRIDGE_API_KEY=/, "", $0); print; exit }')
      DISCOVER_WS_URL=$(printf '%s' "$env_dump" | tr ' ' '\n' \
                         | awk -F= '/^BRIDGE_PUBLIC_WS_URL=/ { sub(/^BRIDGE_PUBLIC_WS_URL=/, "", $0); print; exit }')
      DISCOVER_HOME=$(printf '%s' "$env_dump" | tr ' ' '\n' \
                       | awk -F= '/^HOME=/ { sub(/^HOME=/, "", $0); print; exit }')
      DISCOVER_PWD=$(printf '%s' "$env_dump" | tr ' ' '\n' \
                      | awk -F= '/^PWD=/ { sub(/^PWD=/, "", $0); print; exit }')
    fi
  fi
}

# ------------------------------------------------------------------------------
# classify_port
#
# Requires: discover_port has been called, and CONFIG_FILE is in scope (may be
# missing — idle/first-install scenarios are fine).
#
# Populates:
#   CLASSIFY_KIND    "idle"     | no listener
#                    "managed"  | bridge matches our config/state
#                    "foreign"  | bridge but key/pid/home drifted from ours
#                    "stranger" | something else on the port (not a bridge)
#   CLASSIFY_NOTES   human-readable "why" (empty for idle/managed)
# ------------------------------------------------------------------------------
classify_port() {
  CLASSIFY_KIND=""
  CLASSIFY_NOTES=""

  case "$DISCOVER_STATUS" in
    idle)
      CLASSIFY_KIND="idle"
      return 0
      ;;
    occupied_other)
      CLASSIFY_KIND="stranger"
      CLASSIFY_NOTES="port held by non-bridge process: ${DISCOVER_CMD:-unknown}"
      return 0
      ;;
    occupied_bridge)
      : # fall through to the foreign-vs-managed logic below
      ;;
  esac

  # Pull our view of the world. If config doesn't exist yet, everything is "foreign"
  # by definition — there's nothing to compare against.
  local our_pid="" our_key="" pid_file=""
  if [ -f "${CONFIG_FILE:-}" ]; then
    our_key=$(config_get bridge_api_key 2>/dev/null || true)
    pid_file=$(config_get bridge_pid_file 2>/dev/null || true)
    [ -n "$pid_file" ] && [ -f "$pid_file" ] && our_pid=$(cat "$pid_file" 2>/dev/null || true)
  fi

  local pid_matches=0 key_matches=0 home_matches=1
  # `npx` keeps a parent process alive while the actual bridge listener is a
  # node child. Treat either PID as ours so helper-started bridges do not look
  # foreign just because lsof reports the listener child.
  [ -n "$our_pid" ] && [ "$our_pid" = "$DISCOVER_PID" ] && pid_matches=1
  [ -n "$our_pid" ] && [ "$our_pid" = "$DISCOVER_PPID" ] && pid_matches=1
  [ -n "$our_key" ] && [ -n "$DISCOVER_API_KEY" ] && [ "$our_key" = "$DISCOVER_API_KEY" ] && key_matches=1
  [ -n "$DISCOVER_HOME" ] && [ -n "${HOME:-}" ] && [ "$DISCOVER_HOME" != "$HOME" ] && home_matches=0

  if [ "$pid_matches" -eq 1 ] && [ "$key_matches" -eq 1 ] && [ "$home_matches" -eq 1 ]; then
    CLASSIFY_KIND="managed"
    return 0
  fi

  CLASSIFY_KIND="foreign"
  local reasons=""
  if [ -z "${CONFIG_FILE:-}" ] || [ ! -f "${CONFIG_FILE:-}" ]; then
    reasons="no helper config yet"
  else
    [ -z "$our_pid" ] && reasons="${reasons:+$reasons; }no bridge.pid tracked"
    [ -n "$our_pid" ] && [ "$pid_matches" -eq 0 ] && reasons="${reasons:+$reasons; }PID mismatch (stored=$our_pid, live=$DISCOVER_PID)"
    [ -z "$our_key" ] && reasons="${reasons:+$reasons; }no api_key in config"
    [ -n "$our_key" ] && [ -n "$DISCOVER_API_KEY" ] && [ "$our_key" != "$DISCOVER_API_KEY" ] \
      && reasons="${reasons:+$reasons; }api_key drift (config=${our_key:0:6}…, live=${DISCOVER_API_KEY:0:6}…)"
    [ "$home_matches" -eq 0 ] && reasons="${reasons:+$reasons; }started by external launcher (its HOME=$DISCOVER_HOME)"
  fi
  CLASSIFY_NOTES="$reasons"
}

# ------------------------------------------------------------------------------
# discover_print_summary
#
# Pretty-prints a discovery block to stderr via log_* helpers. Safe to call
# after discover_port + classify_port.
# ------------------------------------------------------------------------------
discover_print_summary() {
  local port="${PORT:-8765}"
  case "$CLASSIFY_KIND" in
    idle)
      log_info "Port $port: idle — no bridge running."
      ;;
    managed)
      log_ok "Port $port: managed bridge (PID $DISCOVER_PID, v${DISCOVER_VERSION:-?})"
      ;;
    foreign)
      log_warn "Port $port: foreign bridge detected — not (fully) managed by this helper."
      [ -n "$DISCOVER_PID" ]     && log_warn "  PID:          $DISCOVER_PID (PPID $DISCOVER_PPID)"
      [ -n "$DISCOVER_VERSION" ] && log_warn "  Bridge:       v$DISCOVER_VERSION, uptime ${DISCOVER_UPTIME:-?}s"
      [ -n "$DISCOVER_API_KEY" ] && log_warn "  Live key:     ${DISCOVER_API_KEY:0:8}…${DISCOVER_API_KEY: -4}"
      [ -n "$DISCOVER_WS_URL" ]  && log_warn "  Live WS URL:  $DISCOVER_WS_URL"
      [ -n "$DISCOVER_HOME" ]    && log_warn "  Launcher HOME: $DISCOVER_HOME"
      [ -n "$CLASSIFY_NOTES" ]   && log_warn "  Why foreign:  $CLASSIFY_NOTES"
      ;;
    stranger)
      log_warn "Port $port: held by non-bridge process."
      [ -n "$DISCOVER_PID" ] && log_warn "  PID $DISCOVER_PID: $DISCOVER_CMD"
      ;;
  esac
}
