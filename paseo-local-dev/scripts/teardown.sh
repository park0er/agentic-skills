#!/usr/bin/env bash
# Tear down the Paseo local dev environment.
# Modes: --soft (keep worktree, remove artifacts) or --full (remove everything)
set -euo pipefail

MODE="${1:---soft}"
WORKTREE=$(pwd)

echo "=== Paseo Local Dev Teardown (mode: $MODE) ==="

# Stop daemon
if [ -f .dev/daemon.pid ] && kill -0 "$(cat .dev/daemon.pid)" 2>/dev/null; then
  echo "→ Stopping dev daemon..."
  kill "$(cat .dev/daemon.pid)" 2>/dev/null || true
fi
# Kill anything on 6768
lsof -ti:6768 2>/dev/null | xargs kill 2>/dev/null || true

# Remove iOS build artifacts
if [ -d packages/app/ios ]; then
  echo "→ Removing packages/app/ios/"
  rm -rf packages/app/ios
fi
rm -rf packages/app/.expo

# Remove DerivedData
DD=$(find ~/Library/Developer/Xcode/DerivedData -maxdepth 1 -name "Paseo-*" 2>/dev/null | head -1)
if [ -n "$DD" ]; then
  echo "→ Removing DerivedData: $DD"
  rm -rf "$DD"
fi

# Shutdown simulators
xcrun simctl shutdown all 2>/dev/null || true

if [ "$MODE" = "--full" ]; then
  echo "→ Removing .dev/ (daemon home + logs)..."
  rm -rf .dev

  echo "→ Removing node_modules..."
  rm -rf node_modules packages/*/node_modules

  # Remove worktree registration
  WORKTREE_NAME=$(basename "$WORKTREE")
  echo "→ Removing git worktree '$WORKTREE_NAME'..."
  cd ..
  git worktree remove "$WORKTREE_NAME" --force 2>/dev/null || echo "  (manual removal may be needed)"
fi

echo "✓ Teardown complete."
