#!/bin/zsh
set -euo pipefail
app_dir="$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
state_file="$app_dir/vpn-refresh/current-interface"
company_dns='10.234.253.8'
current=$(/sbin/route -n get "$company_dns" 2>/dev/null | /usr/bin/awk '/^[[:space:]]*interface: utun[0-9]+$/ { print $2; exit }')
tracked=''; [[ -f "$state_file" ]] && tracked=$(/bin/cat "$state_file")
print -r -- "system=$current tracked=$tracked"
launchctl print "gui/$(id -u)/com.park0er.clash-vpn-refresh" 2>/dev/null | /usr/bin/grep -E 'state =|last exit code' || true
