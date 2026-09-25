# oracle-vpn-ops CHANGELOG

## 2026-08-30 — reserved-ip-moved-to-a1

- **修正 IP 归属(文档此前是错的)**:Reserved IP `141.147.189.28` 已于 2026-08-30 从 `parko-vpn-tokyo-arm`(E2.1.Micro)挪到 `parko-vpn-tokyo-a1`(A1.Flex),**A1 成为主力**;老机器改挂临时 IP `168.110.33.78`;A1 原临时 IP `150.230.192.55` 已释放。文档原先写反了(把 141 标成老机器、150 标成 A1)。`references/` 与 `scripts/` 里硬编码的都是 `141.147.189.28`,正好仍指向主力,**无需改动**。
- **为什么判断 150.230.192.55 已释放而非故障**:SSH 上去是「主机密钥变更」警告 + `Permission denied (publickey)`,即那个 IP 上已经不是我们的机器了;再用 `oci compute instance list-vnics` 逐个实例核对,确认两台的公网 IP 分别是 141(A1)和 168(老机器)。以后查 IP 归属一律用这条 CLI,不要靠 ping/SSH 猜。
- **防回收段从「方案」更新为「已落地的事实」**:补上两台机器的真实 ExecStart 参数(A1 `10800 30 1280`、E2 `7200 40 0`)、实际脉冲时长占比与安全余量(12.5% / 8.3%,门槛 5%)、以及验证命令。**关键差异记下**:E2 只有 956M 内存且不考核内存指标,内存参数必须传 `0`,否则 OOM。
- **补两个已踩/待踩的坑**:① 脚本有 `pgrep -x stress-ng` 防重入,手动跑过之后当天定时那次会 log "already running, skip",是设计行为不是故障;② 早期版本参数换行续行写错被拆成两条命令,报 `--cpu: command not found` (exit 127)。
- **如实标注两个未闭合口子**:没有「跑成功了吗」的自动校验与告警(回收判定是静默的);7 天滚动窗口要到约 2026-09-03/04 才被脉冲日填满,此前属过渡期。
- 核实 A1 上已有 self-hosted Multica(dockerd + 2 daemon + postgres),但基线负载仍低(used 1090M/11932M ≈ 9%, load 0.01),**保活脚本目前拆不掉**。

## 2026-08-29 — trim-research-out-add-idle-reclaim

- **回退上一版两类不该进 skill 的内容(用户指出)**:① 整段删除 self-hosted Multica 评估——那是一次性调研结论,不是 VPN 运维知识,且镜像体积 / helm requests 数值很快过期;② share_addr 那段九成是废话,`share_addr`/`subURI`/`subClashURI` 三处原本就写在 IP 历史那句里,只保留真正新的 WAL 陷阱(换 db 前必须删 `x-ui.db-wal`/`-shm`,否则 SQLite 重放 WAL 会把修改覆盖掉)。
- **新增「⚠️ 闲置回收」段(真实运维风险,值得留)**:Oracle 官方政策——7 天窗口内 CPU 95 分位 <20%、网络 <20%、内存 <20%(仅 A1 机型)三者**同时**成立就可能被回收;三者只要有一项过 20% 即安全。记下 95 分位的含义(24h×5%=1.2h,每天只需 1.2 小时脉冲负载)与 stress-ng + systemd timer 保活方案,以及"跑真实常驻服务才是根本解法"。
- **新增「两台机器的能力差异」实测表**:OCI 标称带宽 0.48 vs 2.0 Gbps、单线程 AES-128-GCM 1400 vs 2966 MB/s,以及核心判断——老机器加密能力 11 Gbps vs 实测 42 Mbps,瓶颈是东京→国内跨境链路而非服务器,故换机器不会让单条连接变快,A1 真正改善的是并发(1GB→12GB 内存 + 聚合带宽)。

## 2026-08-29 — a1-vpn-mirrored-and-multica-sizing

- **A1.Flex 已抢到并搭好 VPN**：抢机脚本 2026-08-24 00:02 第 131 轮成功；2026-08-29 在新机器 (`parko-vpn-tokyo-a1`, 150.230.192.55, aarch64/2C12G) 复刻出与老机器完全一致的 VLESS+REALITY 配置(同 UUID、同 REALITY 密钥、同分流规则、同面板路径)。老机器未做任何改动,两台同时在线待验证。
- 新增「第二台机器：A1.Flex」环境段与「A1 上还能跑什么(self-hosted Multica 评估)」段。
- **修正 Current Clients 漏记**：补上 `yidi@vpn`(subId `eikxmj5bzrohbr`, limitIp=4),之前只记了 `parko@vpn`。
- **换 IP 的三处必须同时改**：补上关键坑——`inbounds.share_addr` 才是决定订阅里节点地址的字段,只改 `subURI`/`subClashURI` 订阅仍会吐旧 IP;且换 db 前必须删 `x-ui.db-wal`/`-shm`,否则 WAL 重放会把旧配置覆盖回来(本次踩过)。
- 3x-ui 版本记录:老机器 3.4.2,新机器 3.7.0;ARM 上 xray 二进制是 `xray-linux-arm64`,主网卡 `enp0s6`(x86 是 `ens3`,MSS clamp 别写错)。

## 2026-08-23 — a1-grab-default-2c12g

- **抢机目标默认改为 2 OCPU / 12 GB**(原 4C24G)。实测本账号 A1 免费额度被砍到 2C/12G:按 4C24G 抢会被 `LimitExceeded`(400)硬拒,与库存无关;改 2C12G 后错误变为 `Out of host capacity`(500),证明参数与额度都对、只差库存。用户明确表示 4C24G 配置不再抢,故 2C12G 成为唯一 canonical 配置。
- 成功通知文案改为动态 `${OCPUS}C${MEM_GB}G`(不再硬编码 4C24G)。
- **修 a1-status.sh 误报**:pgrep 模式改为 `oracle-a1-grab[^ ]*\.sh`,可匹配任意后缀的抢机脚本名,不再因脚本改名而误报"🔴 未运行"。
- 如日后 Oracle 提额回 4C24G,只需改脚本 `OCPUS`/`MEM_GB` 两行。

## 2026-07-06 — grab-script-error-handling

- **修脚本错误分类**:之前 `head -3` 截断报错,把网络超时(RequestException: connection timed out)误归为"其他响应"且信息不全,误导以为异常
- 新增分类:网络超时单独识别(无害,短等待)、429 指数退避(60→300s,减轻限流)、提取 message 字段替代截断
- 基础重试间隔 60→90s(实测 60s 触发大量 429)
- 澄清:RequestException 只是本地→Oracle 网络超时,非"抢到但失败";Always Free A1 不产生费用,信用卡小额验证(授权+撤销)是 Oracle 正常行为

## 2026-07-04 — a1-status-progress-watch

- **新增 scripts/a1-status.sh**：抢机进度一览（进程状态/运行时长/轮次统计/最近日志/是否抢到）
- **SKILL.md 新增触发词**："抢机进度/a1进度/看抢机/抢到了吗" + "A1.Flex 抢机进度"专段（常驻进程原理、查进度命令、重启方法）
- 配套技术方案图解 HTML 在用户机 `~/Downloads/a1-grab-explained.html`

## 2026-07-04 — routing-rules-and-a1-grab

- **新增 references/routing-rules.md**：三种订阅格式(base64/Clash/SR .conf)能否带规则、服务器端烤规则(subClashRules + subClashEnableRouting 机制)、Clash Verge 本地覆盖、Shadowrocket .conf 方案、标准规则集(照搬奈云 hardcoded)
- **服务器已烤规则**：3x-ui subClashRules 注入 105 条规则，Clash 订阅原生自带分流(CN 直连/海外代理/去广告)
- **新增 scripts/oracle-a1-grab.sh**：A1.Flex 抢机脚本(已填 OCID，实测参数正确，后台运行中)
- **新增 scripts/clash-rules-prepend.yaml**：Clash 分流规则(prepend 格式)
- **新增 scripts/parko-shadowrocket.conf**：Shadowrocket 手动导入配置(节点+规则)
- **采集全部抢机 OCID**：compartment/AD/subnet/aarch64 镜像/SSH 公钥(见 oracle-cloud.md)
- SKILL.md 新增 Scripts、Subscription Links 段；TODO 更新(抢机脚本+路由规则打勾)
- 修掉 client-management.md / daily-ops.md 的旧 IP 残留(→141.147.189.28)

## 2026-07-04 — perf-tuning-and-oci-cli

- **新增 references/performance-tuning.md**：BBR、MSS clamp、TCP 缓冲区、swap、文件描述符五项调优，含"问题/原理/命令/验证"和诊断决策树
- **BBR 实测生效**：下载 1Mbps→42Mbps（cubic 在跨境有损线路误判假丢包 → 换 BBR）
- **MSS clamp**：解决"WiFi 能连、5G 连不上"（蜂窝 MTU 小 + PMTUD 被墙 → 大包黑洞）
- **IP 轮换**：`161.33.130.183` → `141.147.189.28`（全 skill 同步更新）
- **OCI CLI 配置完成**：`~/.oci/config`，记录 API Key 位置、tenancy OCID、CLI 换 IP 完整流程（oracle-cloud.md）
- troubleshooting.md 新增两条高频症状条目，IP 被墙条目加"先排除 BBR/MSS"警告
- SKILL.md 新增 OCI CLI section、IP 历史、TODO 更新

## 2026-07-04 — initial-setup

- 初始版本：Oracle Cloud Free Tier (Tokyo) 自建 VPN 运维 skill
- 环境信息：E2.1.Micro 实例、161.33.130.183、3x-ui v3.4.2
- 日常运维：SSH/面板/服务管理/日志/更新
- 客户端管理：添加/删除 client、订阅链接生成、分享方式（Clash/Shadowrocket/v2rayN）
- 排障指南：443 不通、面板 403、IP 被墙、OOM
- Oracle Cloud 操作：控制台路径、Security List、换 IP、Free Tier 限额
- A1.Flex 抢机脚本草案（TODO：待 OCI CLI 配置后实测）
- 便捷脚本：ssh-panel.sh 一键隧道
