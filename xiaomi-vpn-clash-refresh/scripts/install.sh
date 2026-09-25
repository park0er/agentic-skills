#!/bin/zsh
set -euo pipefail

usage() {
  print -r -- "Usage: $0 --profile-script /absolute/path/to/active-extend-script.js [--company-dns IP]"
  exit 2
}

profile_script=''
company_dns='10.234.253.8'
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-script) profile_script="${2:-}"; shift 2 ;;
    --company-dns) company_dns="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -n "$profile_script" && -f "$profile_script" ]] || usage

app_dir=${profile_script:h:h}
runtime_config="$app_dir/clash-verge.yaml"
[[ -f "$runtime_config" ]] || { print -u2 -- "Missing runtime config: $runtime_config"; exit 1; }

backup_dir="$app_dir/vpn-refresh/backups"
script_dir="$app_dir/scripts"
state_dir="$app_dir/vpn-refresh"
watcher="$script_dir/company-vpn-clash-refresh.sh"
plist="$HOME/Library/LaunchAgents/com.park0er.clash-vpn-refresh.plist"
mkdir -p "$backup_dir" "$script_dir" "$state_dir"

stamp=$(/bin/date '+%Y%m%d-%H%M%S')
backup="$backup_dir/${profile_script:t}.$stamp.bak"
/bin/cp -p "$profile_script" "$backup"
print -r -- "$profile_script" > "$state_dir/profile-script-path"

/usr/bin/perl -0pi -e 's/utun[0-9]+/VPN_INTERFACE_PLACEHOLDER/g' "$profile_script"
/usr/bin/perl -0pi -e 's/VPN_INTERFACE_PLACEHOLDER/utun9/g' "$profile_script"

cat > "$watcher" <<EOF
#!/bin/zsh
set -euo pipefail
app_dir='$app_dir'
profile_script='$profile_script'
runtime_config='\$app_dir/clash-verge.yaml'
state_dir='\$app_dir/vpn-refresh'
state_file='\$state_dir/current-interface'
log_file='\$state_dir/refresh.log'
socket='/tmp/verge/verge-mihomo.sock'
company_dns='$company_dns'
mkdir -p "\$state_dir"
vpn_interface=\$(/sbin/route -n get "\$company_dns" 2>/dev/null | /usr/bin/awk '/^[[:space:]]*interface: utun[0-9]+\$/ { print \$2; exit }')
[[ -n "\$vpn_interface" ]] || exit 0
previous=''; [[ -f "\$state_file" ]] && previous=\$(/bin/cat "\$state_file")
[[ "\$vpn_interface" != "\$previous" ]] || exit 0
export VPN_INTERFACE="\$vpn_interface"
/usr/bin/perl -0pi -e 's/utun[0-9]+/\$ENV{VPN_INTERFACE}/g' "\$profile_script"
/usr/bin/perl -0pi -e 's/(10\\.234\\.(?:253\\.8|254\\.8)#)utun[0-9]+/\${1}\$ENV{VPN_INTERFACE}/g; s/(name: 公司VPN直连.*?interface-name: )utun[0-9]+/\${1}\$ENV{VPN_INTERFACE}/s' "\$runtime_config"
if /usr/bin/curl --unix-socket "\$socket" --silent --show-error --fail -X PUT 'http://localhost/configs?force=true' -H 'Content-Type: application/json' --data '{"path":"'"\$runtime_config"'"}' >/dev/null; then
  /usr/bin/curl --unix-socket "\$socket" --silent --fail -X POST http://localhost/cache/dns/flush >/dev/null || true
  /usr/bin/curl --unix-socket "\$socket" --silent --fail -X POST http://localhost/cache/fakeip/flush >/dev/null || true
  print -r -- "\$vpn_interface" > "\$state_file"
  print -r -- "\$(/bin/date '+%Y-%m-%d %H:%M:%S') switched to \$vpn_interface" >> "\$log_file"
fi
EOF
chmod 700 "$watcher"

cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.park0er.clash-vpn-refresh</string>
<key>ProgramArguments</key><array><string>/bin/zsh</string><string>$watcher</string></array>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>5</integer>
<key>StandardOutPath</key><string>$state_dir/launchd.out.log</string>
<key>StandardErrorPath</key><string>$state_dir/launchd.err.log</string>
</dict></plist>
EOF

plutil -lint "$plist" >/dev/null
launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl kickstart -k "gui/$(id -u)/com.park0er.clash-vpn-refresh"
print -r -- "Installed watcher. Profile backup: $backup"
