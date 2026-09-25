#!/bin/zsh
set -euo pipefail

app_dir="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
vault="$app_dir/vpn-refresh/backups"
profile_path_file="$app_dir/vpn-refresh/profile-script-path"

if [[ "${1:-}" == '--list' ]]; then
  find "$vault" -maxdepth 1 -type f -name '*.bak' -print 2>/dev/null | sort
  exit 0
fi

[[ "${1:-}" == '--latest' && "${2:-}" == '--yes' ]] || {
  print -u2 -- "Usage: $0 --list | $0 --latest --yes"
  exit 2
}

backup=$(find "$vault" -maxdepth 1 -type f -name '*.bak' -print 2>/dev/null | sort | tail -n 1)
[[ -n "$backup" ]] || { print -u2 -- 'No local recovery backup found.'; exit 1; }

[[ -f "$profile_path_file" ]] || { print -u2 -- 'No saved active profile path found.'; exit 1; }
current=$(/bin/cat "$profile_path_file")
[[ -f "$current" ]] || { print -u2 -- 'Could not identify a local profile script.'; exit 1; }
mkdir -p "$vault"
stamp=$(/bin/date '+%Y%m%d-%H%M%S')
/bin/cp -p "$current" "$vault/pre-restore-$stamp.bak"
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.park0er.clash-vpn-refresh.plist" 2>/dev/null || true
/bin/cp -p "$backup" "$current"
print -r -- "Restored $backup. Reactivate the profile in Clash Verge to apply it."
