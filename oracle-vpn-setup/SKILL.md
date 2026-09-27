---
name: oracle-vpn-setup
description: 从 0 到 1 在 Oracle Cloud Always Free 上搭建自用 VPN（VLESS + REALITY + Vision，3x-ui 面板，Clash Verge / Shadowrocket 客户端），可复用于任意区域（东京、美国等）。覆盖：选 Home Region 与账号约束、选机型（A1.Flex vs E2.1.Micro）与抢机脚本、VCN/公网 IP/两层防火墙、3x-ui 非交互安装与个性化、REALITY 入站与订阅、BBR/MSS 等必做调优、分流规则、防闲置回收、验收清单，以及上一次东京搭建踩过的全部坑。Trigger on "再搭一套 VPN", "新建一台 Oracle VPN", "美国 Oracle 搭 VPN", "从零搭 VPN", "oracle vpn setup", "新区域部署 VPN", "复刻东京那套", "申请 Oracle 免费机", "选什么机器". 已搭好之后的日常运维（加用户、换 IP、看抢机进度、排障）用 oracle-vpn-ops。
---

# Oracle VPN 从 0 到 1 搭建

来源：2026-07-03 到 08-30 在东京（`ap-tokyo-1`）实际完成的一次搭建，包括 E2.1.Micro 首发、调优、A1.Flex 抢机和迁移。这个 skill 把那次经验整理成**不绑定区域**的流程，下一次目标是**美国区域**。

搭完以后的运维归 `oracle-vpn-ops` 管。本 skill 最后一步是把新机器登记进 `oracle-vpn-ops`。

## 先讲清三个关键约束（开始前必须跟用户确认）

1. **Always Free 资源只在账号的 Home Region 免费，而 Home Region 注册后不能改。** 用户现有的 Oracle 账号（tenancy `zhaoxisheng2`）Home Region 是东京，所以在这个账号里**不可能免费**开美国机器。要免费开美国机器只有两条路：
   - **A. 新注册一个 Oracle 账号，Home Region 选美国。** 免费。Oracle 会做信用卡验证，同一张卡或同一身份重复注册可能被拒，这一点让用户自己判断，不要替用户承诺能通过。
   - **B. 现有账号升级为 Pay As You Go 并订阅美国区域。** 美国区的机器**按量收费**（Always Free 额度不适用于非 Home Region）。只有用户明确接受付费才走这条。
2. **A1.Flex 容量长期紧张**，大概率要挂抢机脚本等几小时到几周（东京那次等了 7 周、第 131 轮才抢到）。E2.1.Micro 通常能直接开出来，适合先上线过渡。
3. **Always Free 实例闲置会被回收**（7 天内 CPU、网络、内存 95 分位都低于 20%）。VPN 负载天然很低，上线当天就要装保活。

## 流程总览

| 阶段 | 做什么 | 参考 |
|---|---|---|
| 0 采集输入 | 确认下面「需要用户提供的信息」 | 本页 |
| 1 账号与区域 | Home Region 选择、美国区域对比、信用卡验证 | [01-account-region-machine.md](references/01-account-region-machine.md) |
| 2 选机型与开机 | A1 vs E2、镜像、配额、控制台开机、OCI CLI、抢机 | 同上 + `scripts/oracle-grab.sh` |
| 3 网络 | Internet Gateway、路由、Reserved IP、Security List | [02-network.md](references/02-network.md) |
| 4 服务器初始化 | SSH、iptables、BBR/MSS/缓冲区/swap/fd 一次到位 | [03-server-install.md](references/03-server-install.md) + `scripts/server-bootstrap.sh` |
| 5 3x-ui 与 REALITY | 非交互安装、个性化、入站、订阅地址 | 同上 + `scripts/install-3xui.sh` |
| 6 客户端与分流 | Clash 订阅（服务器内置规则）、Shadowrocket `.conf` | [04-clients-rules.md](references/04-clients-rules.md) |
| 7 防回收 | stress-ng + systemd timer | [05-anti-reclaim.md](references/05-anti-reclaim.md) + `scripts/anti-reclaim/` |
| 8 验收 | 两个网络、两种客户端、上下行都测 | `scripts/verify-server.sh` + 本页验收清单 |
| 9 登记 | 把新机器写进 `oracle-vpn-ops` | 本页 |

**踩坑清单一定要读**：[06-pitfalls.md](references/06-pitfalls.md)。东京那次大部分时间都花在这些坑上。

## 需要用户提供的信息

一次问完，缺什么问什么，密码只在运行时要，**不要写进任何文件**：

| 项 | 说明 | 东京那次的值（参考） |
|---|---|---|
| 目标区域 | 例如 `us-sanjose-1`，选法见 01 | `ap-tokyo-1` |
| 走账号 A 还是 B | 新账号免费，或旧账号付费 | 新账号 |
| 实例名 | 建议 `parko-vpn-<region>-<shape>` | `parko-vpn-tokyo-a1` |
| 面板用户名 / 密码 | 密码运行时输入 | `park0er` / 运行时 |
| 面板 web path | 不要用默认随机串以外的好猜路径 | `/parko-3xui-dashboard/` |
| 订阅路径 | base64 和 Clash 两个 | `/parko-sub/`、`/parko-clash/` |
| 第一个 client | email 和 subId | `parko@vpn` / `parko` |
| REALITY SNI | 客户端和服务端必须一致 | `www.apple.com` |
| 客户端节点名 | Clash 里显示的名字 | `parko-tokyo-unlimited` |
| 密钥存放目录 | SSH key、API key 放哪 | iCloud Obsidian `KEY/OracleCloud/` |

用户希望个性化配置由 agent 主动提问（东京那次的做法）。每一项先给默认值，再问要不要改。

## 需要用户手动做的步骤（agent 做不了）

- 注册账号、信用卡验证、登录控制台
- 第一次在控制台生成 **API Key**（Profile → API keys → Add API key → Generate → 下载私钥 → 把 Configuration File Preview 文本发给 agent）。之后开机、换 IP、抢机都可以交给 agent 用 OCI CLI 来做。
- 控制台创建实例时下载 **SSH 私钥**（只能下载一次）
- 手机上导入配置、实地测速

别的都尽量让 agent 通过 OCI CLI 和 SSH 完成。用户不熟悉终端：需要他本人执行的命令，agent 要先把路径和参数填好，给出能直接复制的完整命令。

## 两套密钥别混

| | SSH Key | API Key |
|---|---|---|
| 作用 | 登录服务器系统（`ssh ubuntu@IP`） | 以用户身份调 Oracle API（`oci` CLI） |
| 生成位置 | 创建实例时 | Profile → API keys |
| 本地配置 | `ssh -i <key>` | `~/.oci/config` |

一个 Oracle 账号对应 `~/.oci/config` 里的一个 profile。**新开美国账号时，在 `~/.oci/config` 里加一个新的 profile（例如 `[US]`），不要覆盖 `[DEFAULT]`**：东京的抢机脚本和换 IP 流程都在用 `[DEFAULT]`。之后 CLI 命令统一带 `--profile US`。

## 验收清单（全部通过才算搭好）

- [ ] `bash scripts/verify-server.sh` 全绿（BBR、fq、MSS、swap、fd、x-ui active、443/2096 监听）
- [ ] 公网拉取 Clash 订阅返回 HTTP 200，内容包含 `rules:` 和 `MATCH,PROXY`
- [ ] Clash Verge 导入订阅，切到节点，能打开 Google，出口 IP 是目标区域
- [ ] Shadowrocket 导入 `.conf` 能连
- [ ] **手机 WiFi 和 5G 都能连**（5G 连不上一般是 MSS 问题）
- [ ] **上行、下行都测**，不能只看一个方向（下行远低于上行一般是 BBR 没开）
- [ ] 保活 timer 已 enable，`systemctl list-timers | grep anti-reclaim` 能看到下次触发时间
- [ ] 面板 2053 端口**在公网不可达**（只能走 SSH 隧道访问）

## 最后一步：登记进 oracle-vpn-ops

在 Skill Factory 里更新 `oracle-vpn-ops`：在 SKILL.md 里为新机器加一节 Environment（区域、OCID、IP、shape、网卡名、3x-ui 版本），加上新的订阅链接和 OCI CLI profile 名；更新 CHANGELOG，再用 `release.sh` 发布。**不要直接改安装目录。**

## 文件

- `references/01-account-region-machine.md` — 账号、区域、机型、镜像、抢机
- `references/02-network.md` — VCN、公网 IP、Security List（控制台和 CLI 两种做法）
- `references/03-server-install.md` — 初始化、调优、3x-ui、REALITY、订阅
- `references/04-clients-rules.md` — 客户端接入、分流规则、分享方式
- `references/05-anti-reclaim.md` — 防闲置回收
- `references/06-pitfalls.md` — 东京那次踩过的坑，按阶段排
- `scripts/collect-ocids.sh` — 新区域一键采集 AD、subnet、镜像 OCID
- `scripts/oracle-grab.sh` — 参数化抢机脚本（任意区域、任意 shape）
- `scripts/server-bootstrap.sh` — 服务器端：放行端口 + 五项调优，可重复执行
- `scripts/install-3xui.sh` — 服务器端：3x-ui 非交互安装
- `scripts/verify-server.sh` — 服务器端：只读体检
- `scripts/anti-reclaim/` — 保活脚本、service 和 timer
- `assets/oracle-vpn-setup-plan.html` — 最初的搭建方案（2026-07-03，东京版）。机型、面板选型和风险表至今有效；其中「伪装域名先用 apple.com」「订阅不必开」两条后来有修正，以 06 为准。
