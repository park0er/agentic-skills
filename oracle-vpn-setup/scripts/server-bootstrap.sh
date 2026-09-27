#!/usr/bin/env bash
# server-bootstrap.sh — Oracle Ubuntu 22.04 VPN server init (idempotent)
#   1. iptables: allow 443/tcp, 443/udp, 2096/tcp (inserted before Oracle's default REJECT)
#   2. BBR + fq, TCP buffers 16MB, mtu_probing, fastopen
#   3. MSS clamp 1360 on the primary NIC (auto-detected: ens3 on x86, enp0s6 on ARM)
#   4. 2G swap, swappiness 10
#   5. x-ui LimitNOFILE=1048576 (drop-in; takes effect once x-ui is installed/restarted)
# Usage: sudo bash server-bootstrap.sh          (safe to re-run)
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }

PORTS_TCP=(443 2096)
PORTS_UDP=(443)

NIC=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
echo "primary NIC: ${NIC}"

command -v netfilter-persistent >/dev/null 2>&1 || {
  DEBIAN_FRONTEND=noninteractive apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent netfilter-persistent
}

allow() { # proto port
  if iptables -C INPUT -p "$1" --dport "$2" -j ACCEPT >/dev/null 2>&1; then
    echo "  $1/$2 already allowed"; return
  fi
  local pos
  pos=$(iptables -L INPUT --line-numbers -n | awk '$2=="REJECT"{print $1; exit}')
  if [[ -n "$pos" ]]; then iptables -I INPUT "$pos" -p "$1" --dport "$2" -j ACCEPT
  else iptables -A INPUT -p "$1" --dport "$2" -j ACCEPT; fi
  echo "  $1/$2 allowed"
}
echo ">>> 1/5 iptables"
for p in "${PORTS_TCP[@]}"; do allow tcp "$p"; done
for p in "${PORTS_UDP[@]}"; do allow udp "$p"; done

echo ">>> 2/5 BBR + sysctl"
modprobe tcp_bbr
echo tcp_bbr > /etc/modules-load.d/bbr.conf
cat > /etc/sysctl.d/99-bbr.conf <<'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_mtu_probing = 1
net.core.netdev_max_backlog = 250000
net.ipv4.tcp_fastopen = 3
EOF
sysctl -p /etc/sysctl.d/99-bbr.conf >/dev/null

echo ">>> 3/5 MSS clamp 1360 on ${NIC}"
MSS=(POSTROUTING -o "$NIC" -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360)
iptables -t mangle -C "${MSS[@]}" >/dev/null 2>&1 || iptables -t mangle -A "${MSS[@]}"
netfilter-persistent save >/dev/null

echo ">>> 4/5 swap"
if swapon --show | grep -q /swapfile; then echo "  swapfile exists"; else
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
echo 'vm.swappiness = 10' > /etc/sysctl.d/99-swap.conf
sysctl -w vm.swappiness=10 >/dev/null

echo ">>> 5/5 x-ui LimitNOFILE"
mkdir -p /etc/systemd/system/x-ui.service.d
printf '[Service]\nLimitNOFILE=1048576\n' > /etc/systemd/system/x-ui.service.d/limits.conf
systemctl daemon-reload
if systemctl list-unit-files | grep -q '^x-ui.service'; then
  echo "  x-ui present; restart it when convenient: systemctl restart x-ui"
fi
echo "done. run verify-server.sh to check."
