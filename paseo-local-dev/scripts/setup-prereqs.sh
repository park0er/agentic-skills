#!/usr/bin/env bash
# Install missing prerequisites for paseo-local-dev.
# Safe to run repeatedly — skips already-installed tools.
set -euo pipefail

echo "=== Paseo Local Dev: Prerequisite Setup ==="

install_if_missing() { # $1=binary $2=install_cmd $3=label
  if command -v "$1" >/dev/null 2>&1; then
    echo "✓ $3 already installed ($(command -v "$1"))"
  else
    echo "→ Installing $3..."
    eval "$2"
    echo "✓ $3 installed"
  fi
}

# Homebrew (needed for most installs on macOS)
install_if_missing brew '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' "Homebrew"

# Node.js (via nvm or brew)
if command -v node >/dev/null 2>&1; then
  echo "✓ Node.js already installed ($(node -v))"
else
  echo "→ Installing Node.js via brew..."
  brew install node
  echo "✓ Node.js installed ($(node -v))"
fi

# gh CLI
install_if_missing gh "brew install gh" "GitHub CLI"

# CocoaPods (for iOS builds)
install_if_missing pod "brew install cocoapods" "CocoaPods"

# applesimutils (for simulator permission management)
install_if_missing applesimutils "brew install wix/brew/applesimutils" "applesimutils"

# Playwright browsers
if npx playwright --version >/dev/null 2>&1; then
  echo "✓ Playwright already available"
else
  echo "→ Installing Playwright chromium..."
  npx playwright install chromium
  echo "✓ Playwright chromium installed"
fi

# Xcode Command Line Tools
if xcode-select -p >/dev/null 2>&1; then
  echo "✓ Xcode CLT installed"
else
  echo "→ Installing Xcode Command Line Tools..."
  xcode-select --install
  echo "  (Follow the dialog to complete installation)"
fi

echo
echo "=== All prerequisites ready. ==="
