#!/bin/zsh
set -euo pipefail

label='com.park0er.clash-vpn-refresh'
plist="$HOME/Library/LaunchAgents/$label.plist"
target="gui/$(id -u)/$label"

case "${1:-status}" in
  status)
    launchctl print "$target" 2>/dev/null | /usr/bin/grep -E 'state =|last exit code' || print -r -- 'not loaded'
    ;;
  start)
    launchctl bootstrap "gui/$(id -u)" "$plist" 2>/dev/null || true
    launchctl kickstart -k "$target"
    ;;
  stop)
    launchctl bootout "gui/$(id -u)" "$plist"
    ;;
  restart)
    launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    launchctl kickstart -k "$target"
    ;;
  set-interval)
    seconds="${2:-}"
    [[ "$seconds" =~ '^[1-9][0-9]*$' ]] || { print -u2 -- 'Interval must be a positive integer in seconds.'; exit 2; }
    /usr/libexec/PlistBuddy -c "Set :StartInterval $seconds" "$plist"
    launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    print -r -- "Polling interval set to $seconds seconds."
    ;;
  *)
    print -u2 -- "Usage: $0 {status|start|stop|restart|set-interval <seconds>}"
    exit 2
    ;;
esac
