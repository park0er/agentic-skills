#!/usr/bin/env bash
# install-3xui.sh — non-interactive 3x-ui install on the server.
# Usage (run with ssh -t so the password prompt works):
#   sudo XUI_USERNAME=park0er XUI_PANEL_PORT=2053 XUI_WEB_BASE_PATH=/parko-3xui-dashboard/ bash install-3xui.sh
# The password is read with `read -s` (never passed on the command line).
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }
: "${XUI_USERNAME:?set XUI_USERNAME}"
: "${XUI_PANEL_PORT:=2053}"
: "${XUI_WEB_BASE_PATH:?set XUI_WEB_BASE_PATH, e.g. /my-panel/}"

if [[ -z "${XUI_PASSWORD:-}" ]]; then
  read -rsp "3x-ui panel password: " P1; echo
  read -rsp "repeat password: " P2; echo
  [[ "$P1" == "$P2" && -n "$P1" ]] || { echo "passwords differ or empty"; exit 1; }
  XUI_PASSWORD="$P1"
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --retry 3 -o "$TMP/install.sh" https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh

export XUI_NONINTERACTIVE=1 XUI_USERNAME XUI_PASSWORD XUI_PANEL_PORT XUI_WEB_BASE_PATH
export XUI_SSL_MODE="${XUI_SSL_MODE:-none}"          # panel is only reached via SSH tunnel
export XUI_ENABLE_FAIL2BAN="${XUI_ENABLE_FAIL2BAN:-true}"
bash "$TMP/install.sh" </dev/null

systemctl daemon-reload
systemctl restart x-ui
sleep 3
systemctl is-active x-ui
/usr/local/x-ui/x-ui setting -show true | grep -Ev -i 'password|token' || true
echo "panel: ssh -L ${XUI_PANEL_PORT}:localhost:${XUI_PANEL_PORT} ... then http://localhost:${XUI_PANEL_PORT}${XUI_WEB_BASE_PATH}"
