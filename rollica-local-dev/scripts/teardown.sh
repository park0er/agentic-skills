#!/usr/bin/env bash
# Tear down the local Multica dev stack. Run from the multica checkout root.
#
# Stops, in order: the `local` source daemon, `make dev` + its children
# (Go server :8080, Next.js web :3000, turbo), the Postgres container, and the
# Colima VM. By default `colima stop` keeps the VM + cached images so the next
# run is fast; pass --delete-vm to `colima delete` (full removal — next run
# re-pulls images and re-provisions the VM).
#
# It deliberately does NOT touch a Multica.app / Cloud daemon: those run under a
# different profile (e.g. desktop-api.multica.ai) and only `--profile local` /
# the make-dev children are killed here.
#
# Usage: teardown.sh [--profile local] [--delete-vm] [--i-mean-it]
# Refuses to run when ~/.rollica/local-dev.yaml (or $MULTICA_CONFIG_HOME)
# says kind=persistent-qa, unless --i-mean-it is passed.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE="local"
DELETE_VM=0
I_MEAN_IT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --delete-vm) DELETE_VM=1; shift ;;
    --i-mean-it) I_MEAN_IT=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if python3 "$HERE/load_config.py" get kind >/tmp/rollica-local-dev-kind 2>/dev/null; then
  kind="$(cat /tmp/rollica-local-dev-kind)"
  if [ "$kind" = "persistent-qa" ] && [ "$I_MEAN_IT" -ne 1 ]; then
    echo "teardown.sh: local-dev.yaml kind=persistent-qa; refusing to destroy the QA stack." >&2
    echo "If you really want that, pass --i-mean-it." >&2
    exit 3
  fi
fi

echo "==> stop daemon (profile $PROFILE)"
[ -x ./server/bin/multica ] && ./server/bin/multica daemon stop --profile "$PROFILE" 2>/dev/null || true

echo "==> stop make dev + children"
pkill -f "make dev" 2>/dev/null || true
pkill -f "cmd/server" 2>/dev/null || true
pkill -f "bin/server" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "dev:web" 2>/dev/null || true
pkill -f "turbo dev" 2>/dev/null || true
sleep 2

echo "==> stop Postgres container"
docker compose down 2>/dev/null || true

if [ "$DELETE_VM" -eq 1 ]; then
  echo "==> colima delete (removing VM + cached images)"
  colima delete -f 2>/dev/null || true
else
  echo "==> colima stop (keeping VM + image cache)"
  colima stop 2>/dev/null || true
fi

echo "==> remaining dev ports (expect none):"
lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | grep -E ":3000|:8080" || echo "   3000/8080 free"
echo "✓ teardown complete."
