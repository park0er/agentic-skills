#!/usr/bin/env bash
# paseo-local-dev health check
# Run from the worktree root (e.g. ~/coding/paseo-contrib/paseo-features)
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

check() { # $1=label $2=command
  if eval "$2" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} $1"; ((PASS++))
  else
    echo -e "${RED}✗${NC} $1"; ((FAIL++))
  fi
}

warn_check() { # $1=label $2=command
  if eval "$2" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} $1"; ((PASS++))
  else
    echo -e "${YELLOW}⚠${NC} $1 (optional)"; ((WARN++))
  fi
}

echo "=== Paseo Local Dev Health Check ==="
echo

# --- Prerequisites ---
echo "Prerequisites:"
check "Node.js installed" "node -v"
check "npm installed" "npm -v"
check "gh CLI installed" "which gh"
warn_check "CocoaPods installed" "which pod"
warn_check "applesimutils installed" "which applesimutils"
warn_check "Playwright chromium" "npx playwright --version"
echo

# --- Daemon ---
echo "Dev Daemon (6768):"
check "Daemon responding" "curl -sf -o /dev/null -w '' http://127.0.0.1:6768/"
warn_check "Daemon PID file" "test -f .dev/daemon.pid && kill -0 \$(cat .dev/daemon.pid)"
echo

# --- Metro ---
echo "Metro Dev Server (8081):"
warn_check "Metro running" "curl -sf http://localhost:8081/status | grep -q packager-status"
echo

# --- Code Quality ---
echo "Code Quality:"
check "Server typecheck" "npm run typecheck --workspace=@getpaseo/server"
check "App typecheck" "npm run typecheck --workspace=@getpaseo/app"
echo

# --- iOS (optional) ---
echo "iOS Build (optional):"
warn_check "ios/ directory exists" "test -d packages/app/ios"
warn_check "Pods installed" "test -d packages/app/ios/Pods"
warn_check "Xcode available" "xcodebuild -version"
warn_check "Simulator booted" "xcrun simctl list devices booted 2>/dev/null | grep -qi booted"
echo

# --- Summary ---
echo "=== Summary ==="
echo -e "${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}  ${YELLOW}Warnings: $WARN${NC}"
[ $FAIL -eq 0 ] && echo -e "${GREEN}Environment healthy.${NC}" || echo -e "${RED}Issues found — fix failed checks above.${NC}"
exit $FAIL
