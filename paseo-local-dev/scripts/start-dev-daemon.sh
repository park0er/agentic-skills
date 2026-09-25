#!/usr/bin/env bash
# Start an isolated Paseo dev daemon on port 6768.
# Run from the worktree root.
set -euo pipefail

WORKTREE=$(pwd)
DEV_HOME="$WORKTREE/.dev/paseo-home"
PORT=${PASEO_DEV_PORT:-6768}
PIDFILE="$WORKTREE/.dev/daemon.pid"
LOGFILE="$WORKTREE/.dev/daemon.log"

# Ensure dev home exists
mkdir -p "$DEV_HOME"
if [ ! -f "$DEV_HOME/config.json" ]; then
  cat > "$DEV_HOME/config.json" << EOF
{
  "version": 1,
  "daemon": {
    "listen": "127.0.0.1:$PORT",
    "cors": { "allowedOrigins": ["*"] }
  }
}
EOF
  echo "Seeded $DEV_HOME/config.json"
fi

# Kill existing daemon on this port
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Stopping existing daemon (pid $(cat "$PIDFILE"))..."
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  sleep 2
fi

# Also kill anything else on the port
lsof -ti:"$PORT" 2>/dev/null | xargs kill 2>/dev/null || true

# Build server if not already built
if [ ! -d packages/server/dist ]; then
  echo "Building server..."
  npm run build:server-deps && npm run build:server
fi

# Start daemon
echo "Starting dev daemon on 127.0.0.1:$PORT (PASEO_HOME=$DEV_HOME)..."
nohup env PASEO_HOME="$DEV_HOME" PASEO_LISTEN="127.0.0.1:$PORT" \
  npm run dev:server > "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "Daemon PID: $(cat "$PIDFILE"), log: $LOGFILE"

# Wait for it to come alive
for i in $(seq 1 15); do
  if curl -sf -o /dev/null http://127.0.0.1:"$PORT"/ 2>/dev/null; then
    echo "✓ Daemon alive on port $PORT"
    exit 0
  fi
  sleep 1
done
echo "⚠ Daemon did not respond within 15s. Check $LOGFILE"
exit 1
