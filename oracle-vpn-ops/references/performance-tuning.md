# Performance Tuning（网络性能调优）

自建 VPN 在**跨境有损线路**（日本→中国）上，默认的 Linux 网络参数会严重拖慢速度。本文档记录本机已应用的全部调优、每一项解决什么问题、以及可复现的命令。

> **实测效果**：应用 BBR 前下载 1Mbps / 上传 30Mbps（诡异的不对称）；应用后下载 42.4Mbps / 上传 44.9Mbps（对称正常）。

## 一图看懂：诊断决策树

| 症状 | 根因 | 修复 |
|---|---|---|
| **下载慢、上传快**（不对称） | 服务器发送侧用 cubic，跨境丢包被误判为拥塞 → 疯狂降速 | 开 **BBR** |
| **WiFi 能连、蜂窝(5G/4G)连不上** | 蜂窝 MTU 小 + PMTUD 被墙 → 大包黑洞 | **MSS clamp** + tcp_mtu_probing |
| 速度冲不上去、达不到带宽上限 | TCP 缓冲区太小，高 BDP 链路填不满 | 加大 **TCP 缓冲区** |
| xray 偶发崩溃 / 被 kill | 1GB 内存无 swap，OOM | 加 **swap** |
| 连接数一多就卡死 / 拒绝新连接 | 文件描述符上限 1024 | 提高 **LimitNOFILE** |

---

## 1. BBR 拥塞控制（最高优先级）

**问题**：默认拥塞控制算法 `cubic` 靠"检测到丢包"来判断网络拥塞。跨境线路天然丢包（不代表真拥塞），cubic 把这些"假丢包"当真，一次次踩死刹车 → 下载卡在 1Mbps。而上传方向由客户端（iOS 现代协议栈）控制，不受影响 → 表现为"上快下慢"的不对称。

**原理**：BBR（Google 2016）不靠丢包判断，而是主动测量**瓶颈带宽 + 往返时延**，匀速填满管道。丢包不再触发降速 → 在有损线路上维持高吞吐。

**命令**：
```bash
sudo modprobe tcp_bbr
echo "tcp_bbr" | sudo tee /etc/modules-load.d/bbr.conf     # 开机自动加载模块
sudo tee /etc/sysctl.d/99-bbr.conf > /dev/null << 'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF
sudo sysctl -p /etc/sysctl.d/99-bbr.conf
```

**验证**：
```bash
sysctl net.ipv4.tcp_congestion_control   # 应为 bbr
sysctl net.core.default_qdisc            # 应为 fq
lsmod | grep bbr                         # 模块已加载
```

> 注意：BBR 在**任何 Ubuntu**（Minimal 或完整版）上都不是默认开启的，需手动启用。内核模块两个版本都自带。改动对**新建连接**生效，改完重启 x-ui 或断开重连客户端。

---

## 2. MSS Clamp + MTU 探测（解决蜂窝连不上）

**问题**：网卡 MTU 是 9000（Oracle 巨型帧）。蜂窝网络 MTU 通常仅 ~1400，且运营商常屏蔽 ICMP（PMTUD 失效）。REALITY 握手的大包在蜂窝链路上被默默丢弃 → 握手完不成 → **WiFi 能连、5G 连不上**。

**原理**：MSS clamp 在 TCP 建连（SYN/SYN-ACK）时强制把分段大小限制在蜂窝也能通过的尺寸（MSS 1360 ≈ MTU 1400），从源头避免大包。tcp_mtu_probing 作为补充，让内核遇到黑洞时自动缩小包。

**命令**：
```bash
# MSS clamp（1360 覆盖国内所有 5G/4G）
sudo iptables -t mangle -A POSTROUTING -o ens3 -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
sudo netfilter-persistent save

# MTU 探测（已并入 99-bbr.conf，见下）
sudo sysctl net.ipv4.tcp_mtu_probing=1
```

**验证**：
```bash
sudo iptables -t mangle -L POSTROUTING -n -v | grep TCPMSS   # 应显示 TCPMSS set 1360
```

> 不要直接硬改网卡 MTU（9000→1500）：有断连风险、收益不明。MSS clamp 是更安全的定向修复。

---

## 3. TCP 缓冲区（配合 BBR 榨满带宽）

**问题**：默认 `rmem_max/wmem_max` 仅 ~208KB。在高延迟（跨境 RTT 大）线路上，带宽时延积（BDP）很大，缓冲区太小 → 数据"在途"量受限 → 即使开了 BBR 也冲不满带宽。

**原理**：BDP = 带宽 × RTT。要填满一条 50Mbps、RTT 60ms 的管道，需要约 375KB 的在途缓冲。缓冲区必须 ≥ BDP 才能跑满。调到 16MB 留足余量。

**命令**（已并入 `/etc/sysctl.d/99-bbr.conf`）：
```bash
sudo tee -a /etc/sysctl.d/99-bbr.conf > /dev/null << 'EOF'

net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_mtu_probing = 1
net.core.netdev_max_backlog = 250000
net.ipv4.tcp_fastopen = 3
EOF
sudo sysctl -p /etc/sysctl.d/99-bbr.conf
```

其中：
- `tcp_fastopen = 3` — TCP Fast Open，重复连接跳过握手往返，降低延迟
- `netdev_max_backlog` — 网卡收包队列，高吞吐下防丢包

---

## 4. Swap（稳定性保险）

**问题**：E2.1.Micro 仅 1GB 内存且默认零 swap。内存吃紧时内核直接 OOM-kill 进程（xray 可能被杀）→ VPN 掉线。

**原理**：swap 是"虚拟内存"，内存不够时把冷数据挪到磁盘。`swappiness=10` 让系统只在真缺内存时才用 swap（不影响正常性能），作为崩溃保险。

**命令**：
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness = 10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl vm.swappiness=10
```

**验证**：`free -h | grep Swap`（应显示 2.0Gi）

---

## 5. 文件描述符上限（高并发连接）

**问题**：每个网络连接占用一个文件描述符。系统默认上限 1024，xray service 未显式设置 → 连接数一多就拒绝新连接 / 卡死。

**原理**：VPN 服务器同时承载大量并发连接，需要把上限调到百万级。

**命令**：
```bash
sudo mkdir -p /etc/systemd/system/x-ui.service.d
sudo tee /etc/systemd/system/x-ui.service.d/limits.conf > /dev/null << 'EOF'
[Service]
LimitNOFILE=1048576
EOF
sudo systemctl daemon-reload
sudo systemctl restart x-ui
```

**验证**：
```bash
XPID=$(pgrep -f xray-linux)
cat /proc/$XPID/limits | grep "Max open files"   # 应为 1048576
```

---

## 全部配置文件位置

| 文件 | 内容 |
|---|---|
| `/etc/sysctl.d/99-bbr.conf` | BBR + fq + TCP 缓冲区 + mtu_probing + fastopen |
| `/etc/sysctl.d/99-swap.conf` | vm.swappiness = 10 |
| `/etc/modules-load.d/bbr.conf` | 开机加载 tcp_bbr 模块 |
| `/etc/systemd/system/x-ui.service.d/limits.conf` | xray 文件描述符上限 |
| iptables mangle POSTROUTING | MSS clamp 1360（`netfilter-persistent save` 持久化） |

## 一键体检脚本

```bash
echo "BBR:        $(sysctl -n net.ipv4.tcp_congestion_control)"
echo "qdisc:      $(sysctl -n net.core.default_qdisc)"
echo "rmem_max:   $(sysctl -n net.core.rmem_max)"
echo "mtu_probe:  $(sysctl -n net.ipv4.tcp_mtu_probing)"
echo "swappiness: $(sysctl -n vm.swappiness)"
free -h | grep Swap
sudo iptables -t mangle -L POSTROUTING -n | grep TCPMSS
XPID=$(pgrep -f xray-linux); cat /proc/$XPID/limits | grep "Max open files"
```
