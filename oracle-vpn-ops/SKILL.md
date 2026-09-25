---
name: oracle-vpn-ops
description: Operate and maintain a self-hosted VPN on Oracle Cloud Free Tier (Tokyo). Covers SSH access, 3x-ui panel management, VLESS+REALITY client CRUD, subscription link generation, sharing (Clash/Shadowrocket/v2rayN), server health checks, iptables/Security List troubleshooting, Reserved IP rotation, Oracle console navigation, and A1.Flex capacity-grab scripting. Trigger on "登录面板", "SSH连服务器", "加个新用户", "加client", "给别人分享节点", "订阅链接", "VPN挂了", "443不通", "换IP", "抢机器", "抢机进度", "a1进度", "看抢机", "抢到了吗", "oracle vpn", "3x-ui", "面板", "重启xray", "查日志", "新建订阅", "二维码分享", "更新3x-ui", "oracle cloud vpn status", "check vpn", "vpn 运维".
---

# Oracle VPN Ops

Self-hosted VLESS + REALITY + Vision VPN on Oracle Cloud Free Tier (Tokyo).

## Environment — 老机器 `parko-vpn-tokyo-arm`（**2026-08-30 起退为备机**）

> ⚠️ **IP 已对调（2026-08-30 核实）**：Reserved IP `141.147.189.28` 已从这台机器挪到 A1，老机器改挂临时 IP `168.110.33.78`。
> 后果：**本 skill 里所有默认目标（SSH、面板、订阅链接、各 references 脚本）现在都指向 A1**，不是这台。要连老机器必须显式用 `168.110.33.78`。
> 且 `168.110.33.78` 是 **Ephemeral IP，重启/停机就会变**，重新查用 `oci compute instance list-vnics --instance-id <OCID>`。

| Key | Value |
|---|---|
| Oracle tenancy | `zhaoxisheng2` |
| Region | `ap-tokyo-1` (Japan East Tokyo) |
| AD | `xhDy:AP-TOKYO-1-AD-1` |
| Instance | `parko-vpn-tokyo-arm` |
| Shape | VM.Standard.E2.1.Micro (1/8 OCPU / 1 GB) |
| OS | Ubuntu 22.04 Minimal x86_64 (kernel 6.8.0-oracle) |
| Public IP | `168.110.33.78` (**临时 Ephemeral**，2026-08-30 起) |
| Private IP | `10.0.0.129` |
| VCN | `vcn-20260704-1457` |
| Subnet | `subnet-20260704-1457` (public, `10.0.0.0/24`) |
| SSH user | `ubuntu` |
| SSH key | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key` |

> **IP 历史**：`161.33.130.183`（初始，已释放）→ `141.147.189.28`（**Reserved，2026-08-30 起挂在 A1 上**，现用主力）→ `150.230.192.55`（A1 初始临时 IP，换走后**已释放**，SSH 上去报主机密钥变更 + 认证失败就是它）→ `168.110.33.78`（老机器现用临时 IP）。
> 换 IP 后必须同步更新 3x-ui 的 `share_addr` / `subURI` / `subClashURI`，否则已分发的订阅拉不到（见 troubleshooting.md）。
>
> **换 db 文件的坑**：停服务后必须先删 `x-ui.db-wal` / `x-ui.db-shm` 再覆盖 `x-ui.db`，否则 SQLite 重放 WAL 会把旧配置覆盖回来，改的设置全部失效。

## 主力机器：A1.Flex（2026-08-24 抢到 / 2026-08-29 搭好 / 2026-08-30 接过 Reserved IP）

抢机脚本于 **2026-08-24 00:02（第 131 轮）** 抢到 A1.Flex，2026-08-29 完成与老机器**完全一致**的 VPN 搭建。**2026-08-30 把 Reserved IP `141.147.189.28` 从老机器挪到这台，A1 自此成为主力**（切换对客户端零改动：已分发的订阅链接继续可用）。两台机器**同时在线**、配置完全相同（同一 UUID / 同一 REALITY 密钥 / 同一分流规则），只有 IP 不同。

| Key | Value |
|---|---|
| Instance | `parko-vpn-tokyo-a1` |
| OCID | `ocid1.instance.oc1.ap-tokyo-1.anxhiljrys4a4eacxeen2hohf3xz3ka6lratunu4l4qfb3dscz6bjw4ztzqa` |
| Shape | VM.Standard.A1.Flex（**2 OCPU / 12 GB**，Ampere Altra 3.0 GHz） |
| Arch | `aarch64`（ARM64 — 3x-ui 用 `xray-linux-arm64`） |
| AD | `xhDy:AP-TOKYO-1-AD-1`（FAULT-DOMAIN-3） |
| Public IP | `141.147.189.28`（**Reserved**，2026-08-30 从老机器挪过来） |
| Private IP | `10.0.0.244` |
| 主网卡 | `enp0s6`（x86 老机器是 `ens3`，配 MSS clamp 时注意别写错） |
| OS | Ubuntu 22.04.5 LTS |
| VCN / Subnet / Security List | 与老机器**完全相同**（同一个 subnet） |
| 3x-ui | **3.7.0**（老机器是 3.4.2） |

新机器已按 [performance-tuning.md](references/performance-tuning.md) 全套调优：BBR / fq / TCP 缓冲区 / mtu_probing / fastopen / MSS clamp 1360 / 2G swap / xray `LimitNOFILE=1048576`。

迁移备份与调优脚本：`a1-migration-backup/`（本次 Work 目录内）。

## ⚠️ 闲置回收：Always Free 实例会被 Oracle 回收

**这是 Oracle 官方政策，不是都市传说。** 官方文档 [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) 的 "Reclamation of Idle Compute Instances" 一节写明：

> Oracle will deem VM and bare metal compute instances as idle if, during a **7-day period**, the following are true:
> - **CPU** utilization for the 95th percentile is less than **20%**
> - **Network** utilization is less than **20%**
> - **Memory** utilization is less than **20%**（*仅 A1 机型*）

三个**同时**低于阈值才会被回收 —— 所以只要任意一项稳定过 20% 就安全。A1 比 E2.1.Micro 多一条内存约束，风险更高。

**关键细节**：判定用的是 **95 分位而不是平均值**。一天 24h × 5% = **1.2 小时**，只要每天有 1.2 小时的脉冲负载，95 分位就在阈值以上，其余时间随便闲。

**VPN 服务器天然危险**：只跑 xray + 3x-ui，实测 RAM 419Mi/11Gi ≈ 3.7%，CPU 95 分位估测 1-3%，三项全在阈值下。

**保活方案**（社区成熟做法，`closeblog/oci-cloud-anti-reclaim`）：`stress-ng` 造真实负载 + systemd 定时器每天跑一次。**2026-08-28 已在两台机器上装好，2026-08-30 核实确实在跑**（最近两次均 `status=0/SUCCESS`）。

脚本 `/usr/local/bin/oci-anti-reclaim.sh <时长秒> <每核CPU负载%> <每worker内存MB>`；内存参数传 `0` = 只压 CPU（给 E2 用）。

| | A1（2C/12G，主力） | 老 E2.1.Micro（备机） |
|---|---|---|
| ExecStart 参数 | `10800 30 1280` | `7200 40 0` |
| 每天脉冲时长 | 3h = 全天 **12.5%** | 2h = 全天 **8.3%** |
| 内存占用 | 2×1280M / 11932M = **21.5%** | 不压：E2 不看内存指标，且只有 956M，压了会 OOM |
| 安全余量（需 >5%） | 2.5× | 1.7× |

```ini
# /etc/systemd/system/oci-anti-reclaim.service（A1；E2 同构，只改 ExecStart 参数）
[Service]
Type=oneshot
ExecStart=/usr/local/bin/oci-anti-reclaim.sh 10800 30 1280
Nice=10
CPUSchedulingPolicy=idle       # 有真实 VPN 流量时自动让路，不影响使用
IOSchedulingClass=idle
```
```ini
# /etc/systemd/system/oci-anti-reclaim.timer（两台相同）
[Timer]
OnCalendar=*-*-* 21:00:00     # 机器时区是 UTC，= 北京时间每天 05:00
RandomizedDelaySec=300        # 错开 5 分钟内
Persistent=true               # 重启错过的时间点会补跑
```

**验证是否真在跑**（唯一权威依据，别靠猜）：

```bash
systemctl list-timers --all | grep anti-reclaim   # 下次 / 上次触发时间
systemctl status oci-anti-reclaim.service         # 上次结果，看 status=0/SUCCESS
journalctl -u oci-anti-reclaim.service --no-pager | tail -20
```

**两个已知坑**：① 脚本用 `pgrep -x stress-ng` 防重入，所以**手动跑过之后当天定时那次会 log "already running, skip"，那是设计行为不是故障**；② 早期版本 `stress-ng` 参数换行续行写错，被拆成两条命令报 `--cpu: command not found`（exit 127），当天已修。

**两个未闭合的口子**：
- **没有「跑成功了吗」的自动校验与告警**。timer 被 disable、`stress-ng` 被误删、补跑失败都不会有通知，而 Oracle 的回收判定本身是静默的。
- **7 天滚动窗口还没填满**。保活 8-28 才装上，此前老机器从 7-04、A1 从 8-23 一直闲置，要到**约 2026-09-03/04** 之后窗口才全部是「有脉冲」的天。回收前 Oracle 会发邮件警告，不会静默删机。

**更根本的解法**：让 A1 上跑真实常驻服务，负载自然达标后拆掉保活脚本。2026-08-30 核实 A1 上已有 self-hosted Multica（`dockerd` + 2 个 multica daemon + postgres），但基线仍很低（used 1090M/11932M ≈ 9%，load average 0.01），**目前还拆不掉**。

## OCI CLI（云资源管理 / 已配置）

用于**程序化操作云资源**（换 IP、创建/终止实例、抢 A1.Flex）。注意这套 API Key 跟登录服务器用的 SSH Key 是**两回事**：SSH Key 进操作系统，API Key 认证 Oracle Cloud 身份。

| Key | Value |
|---|---|
| CLI 版本 | oci-cli 3.89.0 (brew) |
| Config 文件 | `~/.oci/config` (权限 600) |
| API Key (.pem) | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/zhaoxisheng@xiaomi.com-*.pem` |
| Region | `ap-tokyo-1` |
| 验证命令 | `oci iam region list --output table` |

```bash
# 常用：列出运行中的实例
oci compute instance list --compartment-id <TENANCY_OCID> --lifecycle-state RUNNING \
  --output table --query 'data[*].{Name:"display-name",ID:id,Shape:shape}'
```

Tenancy OCID: `ocid1.tenancy.oc1..aaaaaaaamt2d6izfyb6znem55sbkdk7dzan4mvnrwdk2yumq2zpddfsd2poa`（root compartment 同此值）。换 IP / 抢机的完整 CLI 流程见 oracle-cloud.md。

## Multica Automation

操作 Multica autopilot / issue 时**默认使用**：

| Key | Value |
|---|---|
| Profile | `desktop-api.multica.ai` |
| Workspace | `park0er`（ID `7f97e6b9-2db3-489c-a270-4e4c6d354469`） |
| 默认 Agent | `CC-ds纯文本`（ID `44dcf79d-2379-4ef8-99f4-30e1fc2e8f6b`） |
| 当前 Autopilot | `A1 抢机进度每日提醒`（ID `d6adb5e0-698b-45b3-bd85-16a74b26a272`，cron 每天 10:00 CST） |

## 3x-ui Panel

| Key | Value |
|---|---|
| Version | 3.4.2 (Xray 26.6.27) |
| Panel port | 2053 (localhost only, SSH tunnel) |
| Web path | `/parko-3xui-dashboard/` |
| Username | `park0er` |
| Password | *(ask user at runtime)* |
| Sub port | 2096 (public) |
| Sub path (base64) | `/parko-sub/<subId>` |
| Sub path (Clash) | `/parko-clash/<subId>` |

## VLESS Inbound

| Key | Value |
|---|---|
| Port | 443 |
| Protocol | VLESS |
| Security | REALITY |
| Flow | `xtls-rprx-vision` |
| SNI / dest | `www.apple.com:443` |
| Fingerprint | `chrome` |
| Public Key | `55z4z7iJ1vAp9UsqJSoulJbYskQ3iSfysSmRfiqzEQs` |
| Short ID | `83510ba7` |

## Current Clients

两台机器上的 client 完全相同（A1 是从老机器 db 复制过去的）。

| Email | Sub ID | UUID | limitIp |
|---|---|---|---|
| `parko@vpn` | `parko` | `26f619d6-3ef7-4c2c-abe0-0ee0215e5356` | 0（不限） |
| `yidi@vpn` | `eikxmj5bzrohbr` | `53e289a7-59fe-479b-84d8-88248d89137c` | 4 |

## Open Ports (iptables + Security List)

- 22/tcp — SSH
- 443/tcp+udp — VLESS REALITY
- 2096/tcp — Subscription service

## Quick Commands

```bash
# SSH into server
ssh -i "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key" ubuntu@141.147.189.28

# SSH tunnel for panel access (then open http://localhost:2053/parko-3xui-dashboard/)
ssh -L 2053:localhost:2053 -i "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key" ubuntu@141.147.189.28

# Or use the bundled script:
bash scripts/ssh-panel.sh
```

## Reference Files

- **[daily-ops.md](references/daily-ops.md)** — SSH, panel access, restart, logs, update 3x-ui
- **[client-management.md](references/client-management.md)** — Add/remove clients, generate share links, subscription vs vless:// link, QR codes
- **[routing-rules.md](references/routing-rules.md)** — 分流规则：三种订阅格式能否带规则、服务器烤规则(subClashRules)、Clash Verge 本地覆盖、Shadowrocket .conf、标准规则集
- **[performance-tuning.md](references/performance-tuning.md)** — BBR、MSS clamp、TCP 缓冲区、swap、文件描述符等网络性能调优（含原理）
- **[troubleshooting.md](references/troubleshooting.md)** — 443 not reachable, panel login fails, IP blocked, 下载慢上传快 (BBR), WiFi 能连蜂窝连不上 (MSS)
- **[oracle-cloud.md](references/oracle-cloud.md)** — Console navigation, Security List, Reserved IP rotation (CLI + console), A1.Flex grab script (实测)

## Scripts

- **scripts/ssh-panel.sh** — 一键 SSH 隧道到面板
- **scripts/oracle-a1-grab.sh** — A1.Flex 容量抢占（已填好 OCID，nohup 后台跑；目标 2 OCPU/12 GB，见下）
- **scripts/a1-status.sh** — 抢机进度一览（进程状态/轮次/最近日志/是否抢到）
- **scripts/clash-rules-prepend.yaml** — Clash 分流规则（prepend 格式，可作 Clash Verge override 或烤进服务器 subClashRules）
- **scripts/parko-shadowrocket.conf** — Shadowrocket 手动导入配置（节点 + 规则）

## A1.Flex 抢机进度（触发 "抢机进度/a1进度/看抢机/抢到了吗"）

抢机脚本以 **常驻后台进程**(非 cron)运行,每轮约 2.5 分钟(API~99s + sleep 60s),遇 `Out of host capacity` 继续重试,抢到后弹 macOS 通知 + 存 `~/oracle-a1-launch-success.json`。

> **额度现实(2026-08-23 实测)**：本账号 A1 免费额度被砍到 **2 OCPU / 12 GB**(非标准 4C/24G)。脚本默认已设为 2C12G。按 4C24G 抢会被 `LimitExceeded`(400)硬拒——**这不是库存问题,循环重试无用**;只有请求 Oracle 提额后才能改回 4C24G。改配置改脚本 `OCPUS`/`MEM_GB` 两行即可。查进度:

```bash
bash scripts/a1-status.sh          # 一眼看懂的汇总(推荐)
# 或直接:
pgrep -fl oracle-a1-grab.sh        # 是否在跑
tail -f ~/oracle-a1-grab.log       # 实时日志(Ctrl+C 退出)
```

若进程不在了,重启:`nohup bash <脚本路径>/oracle-a1-grab.sh > ~/oracle-a1-grab.out 2>&1 &`
（脚本在用户机器 `~/coding/Foundations/AgentSetups/oracle-vpn/oracle-a1-grab.sh`，或从 skill `scripts/` 复制）。技术方案图解见 `~/coding/Foundations/AgentSetups/oracle-vpn/a1-grab-explained.html`。

## Subscription Links

两台机器都活着，路径相同、只有 IP 不同。`<subId>` 见 Current Clients。

**主力：A1 `141.147.189.28`**（Reserved IP，2026-08-30 从老机器挪过来 —— 客户端零改动）
- Clash（自带规则）：`http://141.147.189.28:2096/parko-clash/<subId>`
- base64（仅节点）：`http://141.147.189.28:2096/parko-sub/<subId>`

**备机：老 x86 `168.110.33.78`**（**临时 Ephemeral IP，重启就变**）
- Clash（自带规则）：`http://168.110.33.78:2096/parko-clash/<subId>`
- base64（仅节点）：`http://168.110.33.78:2096/parko-sub/<subId>`

> ❌ `150.230.192.55` 已失效（A1 的初始临时 IP，换 Reserved IP 时释放）。任何指向它的链接都要改。

- Shadowrocket：导入 `scripts/parko-shadowrocket.conf`（把里面的 IP 换成要用的那台）

## 两台机器的能力差异（2026-08-29 实测）

迁移前评估「换 A1 会不会更快」时测的，结论是**单连接速度不会变、并发会显著变好**：

| | 老 E2.1.Micro | 新 A1.Flex | 倍数 |
|---|---|---|---|
| OCPU | 1/8 | 2 | ~16x |
| 内存 | 1 GB | 12 GB | 12x |
| 网卡带宽（OCI 标称） | 0.48 Gbps | 2.0 Gbps | 4.2x |
| 单线程 AES-128-GCM | 1400 MB/s | 2966 MB/s | 2.1x |
| max VNIC | 1 | 2 | 2x |

**判断依据**：实测老机器单线程加密能力 1400 MB/s ≈ **11 Gbps**，而用户实测 VPN 速度只有 **42 Mbps**（0.4%）。即使按 1/8 OCPU 折算也有 1.4 Gbps，仍是 33 倍余量。**老机器的 CPU / 网卡都不是瓶颈，瓶颈是东京→国内的跨境链路**——两台机器在同一个 AD、同一个 subnet、同一条出口路由，所以换机器不会让单条连接变快。

**A1 真正会变好的是并发**：1 GB 内存才是老机器的真瓶颈（我们把 `rmem_max/wmem_max` 调到了 16 MB，多并发时 1 GB 很容易吃紧），12 GB 后几十台设备无压力；聚合带宽 0.48→2 Gbps。

## TODO

- [x] OCI CLI 配置完成（`~/.oci/config`，可程序化换 IP / 抢机）
- [x] A1.Flex capacity-grab script（scripts/oracle-a1-grab.sh，2026-08-24 第 131 轮抢到）
- [x] 路由分流规则（服务器已烤 subClashRules；见 routing-rules.md）
- [x] A1 机器 VPN 搭建完成（2026-08-29，配置与老机器一致）
- [x] **Reserved IP 挪到 A1**（2026-08-30，A1 成为主力，客户端零改动；老机器改挂临时 IP `168.110.33.78`）
- [x] A1 防回收保活：systemd timer + stress-ng（2026-08-28 装上，2026-08-30 核实连续两天成功执行）
- [x] A1 上部署 self-hosted Multica（2026-08-30 核实已在跑：`dockerd` + 2 个 multica daemon + postgres；但基线负载仍低，保活脚本暂不能拆）
- [ ] **加保活自检 + 告警**：跑完/失败都推通知（当前最大的结构性缺口 —— 回收判定是静默的）
- [ ] 等 7 天滚动窗口填满（**约 2026-09-03/04**）后再复核一次保活效果
- [ ] **待用户实测 A1**：连 `141.147.189.28` 的订阅（现在就是 A1），测速 + 蜂窝/WiFi 都试
- [ ] 给老机器绑一个 Reserved IP：它现在是临时 IP，重启就变，当备机不可靠
- [ ] 决定老机器去留：保留做互备 / 还是终止释放额度
