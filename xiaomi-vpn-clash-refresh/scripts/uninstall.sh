#!/bin/zsh
set -euo pipefail
plist="$HOME/Library/LaunchAgents/com.park0er.clash-vpn-refresh.plist"
launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
/bin/rm -f "$plist"
print -r -- "Removed the VPN-to-Clash watcher. Profile backups were preserved."
