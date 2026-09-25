# Troubleshooting

## 443 Not Reachable (VPN not working)

Check in this order (outer → inner):

### 1. Oracle Security List

Console → Networking → VCN `vcn-20260704-1457` → Security Lists → Default Security List.
Verify ingress rule exists: `0.0.0.0/0 TCP 443`.

### 2. Instance iptables

```bash
sudo iptables -L INPUT -n | grep 443
# Should show ACCEPT for tcp dpt:443
# If missing:
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT -p udp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 3. Xray process

```bash
sudo systemctl status x-ui
# Check if xray child process is running
ps aux | grep xray
# If not running:
sudo systemctl restart x-ui
```

### 4. Port binding conflict

```bash
sudo ss -tlnp | grep 443
# Should show x-ui/xray. If something else is on 443, stop it.
```

### 5. Test from server itself

```bash
curl -v --connect-timeout 5 https://www.apple.com 2>&1 | grep "Connected"
# If this fails, server has no outbound internet → check route table / internet gateway
```

## Panel Login Fails (403 / Connection Refused)

- SSH tunnel not running? Start it: `ssh -L 2053:localhost:2053 ...`
- Wrong web path? Current path: `/parko-3xui-dashboard/`
- Wrong credentials? Reset: `sudo /usr/local/x-ui/x-ui setting -username park0er -password <new>`
- Service down? `sudo systemctl restart x-ui`

## 下载慢、上传快（不对称）→ 开 BBR

**症状**：测速下载只有 0.5~1Mbps，上传却有 30+Mbps。同一 WiFi、同一时刻。

**根因**：服务器默认拥塞控制算法 `cubic` 在跨境有损线路上把"假丢包"误判为拥塞而疯狂降速。下载方向由服务器发送侧控制（cubic），上传方向由客户端控制（iOS 现代算法），所以不对称。

**修复**：启用 BBR（详见 [performance-tuning.md](performance-tuning.md) §1）。
```bash
sudo modprobe tcp_bbr
echo "tcp_bbr" | sudo tee /etc/modules-load.d/bbr.conf
printf 'net.core.default_qdisc = fq\nnet.ipv4.tcp_congestion_control = bbr\n' | sudo tee /etc/sysctl.d/99-bbr.conf
sudo sysctl -p /etc/sysctl.d/99-bbr.conf
sudo systemctl restart x-ui   # 让新连接用 BBR
```
客户端需断开重连（TCP 连接重建后才走 BBR）。实测下载 1→42Mbps。

## WiFi 能连、蜂窝(5G/4G)连不上 → MSS clamp

**症状**：手机连 WiFi 时 VPN 正常，切到 5G/4G 就连不上。配置、服务器都没问题（WiFi 能证明）。

**根因**：网卡 MTU 9000（巨型帧），蜂窝网络 MTU 仅 ~1400 且运营商屏蔽 ICMP（PMTUD 失效）→ REALITY 握手大包在蜂窝链路上被黑洞丢弃 → 握手失败。

**修复**：MSS clamp，强制建连时限制分段大小（详见 [performance-tuning.md](performance-tuning.md) §2）。
```bash
sudo iptables -t mangle -A POSTROUTING -o ens3 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
sudo netfilter-persistent save
sudo sysctl net.ipv4.tcp_mtu_probing=1
```
1360 覆盖国内所有 5G/4G。改完让用户切 5G 重连测试。

## Subscription Returns localhost in vless:// Link

The inbound's `shareAddr` is not set to public IP.

```bash
sudo sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET share_addr='141.147.189.28', share_addr_strategy='custom' WHERE id=1;"
sudo systemctl restart x-ui
```

## Clash Subscription Returns "invalid yaml"

Clash Verge needs the **Clash format** endpoint, not the base64 one:
- ✅ `http://141.147.189.28:2096/parko-clash/<subId>`
- ❌ `http://141.147.189.28:2096/parko-sub/<subId>` (this is base64, for v2rayN/Shadowrocket)

## IP Possibly Blocked / High Latency

Oracle Free Tier IPs have poor reputation. If connection works but is very slow or gets reset:

> **注意**：换 IP 前先确认不是 **BBR / MSS** 问题（见本文档上方两条）。本机遇到的"慢"实际是 cubic 而非 IP 被墙——换 IP 没用，开 BBR 才有用。IP 被墙的典型特征是**完全连不上或频繁 reset**，不是单纯慢。

换 IP 现在可用 **OCI CLI 全自动完成**（推荐，见 [oracle-cloud.md](oracle-cloud.md) "Rotate Public IP via CLI"），或手动控制台操作：

1. Release current Reserved IP
2. Reserve a new one (Console → Networking → IP Management → Reserved Public IPs)
3. Assign new IP to the VNIC
4. Update SKILL.md and 3x-ui `shareAddr` with new IP
5. Clients using subscription links will auto-update on next refresh

```bash
# Update shareAddr + subscription URIs after IP change (关键：三处都要改)
sudo sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET share_addr='<NEW_IP>' WHERE id=1;"
sudo sqlite3 /etc/x-ui/x-ui.db "UPDATE settings SET value='http://<NEW_IP>:2096/parko-sub/' WHERE key='subURI';"
sudo sqlite3 /etc/x-ui/x-ui.db "UPDATE settings SET value='http://<NEW_IP>:2096/parko-clash/' WHERE key='subClashURI';"
sudo systemctl restart x-ui
```

> 换 IP 后**订阅链接的地址也变了**，客户端"刷新"拉的是旧地址（已失效）——必须在客户端里把订阅 URL 改成新 IP，或删旧订阅重新添加。

## 3x-ui Database Location

```
/etc/x-ui/x-ui.db   (SQLite3)
```

All settings, inbounds, clients stored here. Back up before major changes:
```bash
sudo cp /etc/x-ui/x-ui.db /etc/x-ui/x-ui.db.bak.$(date +%Y%m%d)
```

## Server Ran Out of Memory (OOM)

E2.1.Micro only has 1 GB RAM. **本机已配置 2GB swap**（见 [performance-tuning.md](performance-tuning.md) §4）。如需在新机器上重建：

```bash
# Check dmesg for OOM
dmesg | grep -i "out of memory" | tail -5

# Add 2GB swap if not present
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness = 10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl vm.swappiness=10
```
