#!/usr/bin/env bash
# verify-server.sh — read-only health check for a 3x-ui VLESS REALITY server.
# Does not restart anything or generate heavy traffic. Usage: sudo bash verify-server.sh
set -uo pipefail
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; FAIL=1; }
FAIL=0
chk() { [[ "$2" == "$3" ]] && ok "$1 = $2" || bad "$1 = $2 (want $3)"; }

echo "== kernel / tuning"
chk congestion "$(sysctl -n net.ipv4.tcp_congestion_control)" bbr
chk qdisc      "$(sysctl -n net.core.default_qdisc)" fq
chk rmem_max   "$(sysctl -n net.core.rmem_max)" 16777216
chk mtu_probe  "$(sysctl -n net.ipv4.tcp_mtu_probing)" 1
iptables -t mangle -S POSTROUTING 2>/dev/null | grep -q 'TCPMSS.*1360' && ok "MSS clamp 1360" || bad "MSS clamp missing"
swapon --show | grep -q . && ok "swap: $(swapon --show --noheadings | awk '{print $3}')" || bad "no swap"

echo "== firewall (iptables INPUT)"
for r in "tcp 443" "udp 443" "tcp 2096"; do
  set -- $r; iptables -C INPUT -p "$1" --dport "$2" -j ACCEPT >/dev/null 2>&1 && ok "$1/$2 allowed" || bad "$1/$2 not allowed"
done

echo "== services"
[[ "$(systemctl is-active x-ui 2>/dev/null)" == active ]] && ok "x-ui active" || bad "x-ui not active"
XPID=$(pgrep -f 'xray-linux' | head -1)
if [[ -n "$XPID" ]]; then
  chk nofile "$(awk '/Max open files/{print $4}' /proc/$XPID/limits)" 1048576
else bad "xray not running"; fi
ss -ltn | grep -q ':443 '  && ok "listening :443"  || bad ":443 not listening"
ss -ltn | grep -q ':2096 ' && ok "listening :2096" || bad ":2096 not listening"
if ss -ltn | awk '{print $4}' | grep -qE '^(0\.0\.0\.0|\*|\[::\]):2053$'; then
  echo "  NOTE panel 2053 binds all interfaces; OK only if Security List does NOT open 2053"
fi

echo "== anti-reclaim"
systemctl is-enabled oci-anti-reclaim.timer >/dev/null 2>&1 && ok "timer enabled" || bad "anti-reclaim timer not enabled"

echo
[[ $FAIL -eq 0 ]] && echo "ALL OK" || { echo "SOME CHECKS FAILED"; exit 1; }
