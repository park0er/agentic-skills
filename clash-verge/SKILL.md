---
name: clash-verge
description: Manage Clash Verge parko profile — extend script (DNS + chained proxy), rules override, connectivity testing, and bitable-driven decision table. Triggers when the user asks to view/edit clash rules, test domain connectivity, sync the PROXY/DIRECT decision table, or troubleshoot clash routing.
---

# Clash Verge parko Profile Manager

This skill manages the local parko profile override files in Clash Verge Rev: the **extend script** (`saDMY9wRANlr.js`) and the **rules override** (`rJDbf1hBTouK.yaml`). The remote subscription (parko service → `R6IdJowV5G47.yaml`) is read-only; all custom logic lives in these two local override files.

## Triggering Cases

- 查看/编辑/测试 clash 规则
- 连通性测试：某个域名能不能直连
- 同步/生成 PROXY vs DIRECT 决策表（与飞书多维表格联动）
- 修改 DNS nameserver-policy 或 fake-ip-filter
- 调整链式代理参数
- clash 分流配置、override 规则管理
- **新机器从零搭建** clash verge（触发词：新机器配置 clash / 从零搭建 clash verge / bootstrap clash）

## Home VPN boundary

When the user is at home with Xiaomi corporate VPN and Clash running together,
do not fold that persistent tunnel-recovery setup into this general skill.
Use `xiaomi-vpn-clash-refresh` for its confirmed domain boundary, VPN-interface
drift watcher, local recovery backups, and LaunchAgent management. This skill
continues to own general parko subscription and rule work.

## 新机器全自动搭建（零 GUI 操作）

新办公机从 0 到 100 的搭建流程，全部由 skill 代劳，**用户唯一需要手动做的只有装 Clash Verge Rev 应用本身**（skill 不能代劳 app 安装）。

### 前置条件

1. 已下载安装 Clash Verge Rev：https://github.com/clash-verge-rev/clash-verge-rev/releases
2. **启动一次 Clash Verge GUI** 让它初始化数据目录（生成 `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/`）
3. 当前办公网络可达 parko 订阅服务器（默认 http://141.147.189.28:2096）

### 一键搭建

```bash
python3 ~/.claude/skills/clash-verge/scripts/bootstrap.py
# 或自定义订阅 URL：
python3 ~/.claude/skills/clash-verge/scripts/bootstrap.py http://your-parko-url
```

脚本自动完成：
1. 下载 parko 订阅 → 注册为 remote profile
2. 从 `templates/` 拷贝 extend script + rules override，生成 uid 写入 `profiles/`
3. 修改 `profiles.yaml`：注册 3 个条目 + 绑定到 parko 的 `option.script` / `option.rules` + 设 `current: parko`
4. 修改 `verge.yaml`：`enable_tun_mode: true` + `enable_system_proxy: true`

### 脚本执行后

```bash
# 1. 启动（或重启）Clash Verge GUI 让它重新读 profiles.yaml 和 verge.yaml
# 2. 跑 /clash-verge 让 skill 做连通性验证
```

GUI 启动后会把 `profiles.yaml` 的注册关系加载到内存，把 `verge.yaml` 的 TUN/系统代理开关应用上。无需任何 GUI 点击操作。

### 为什么不需要 GUI 操作

Clash Verge 的 profile 绑定关系存在 `profiles.yaml`（普通 YAML 文件），每个 override 通过 `uid` + `file` 字段引用 `profiles/<uid>.js|yaml` 文件，remote profile 的 `option.script` / `option.rules` 字段挂 override 的 uid。skill 直接写文件 + 改 YAML 即可完成绑定，等价于 GUI 里的"编辑脚本/规则"按钮。

## Architecture

详见 [reference/architecture.md](file:///Users/park0er/.claude/skills/clash-verge/reference/architecture.md)。

```
远程订阅 (parko 服务端)     override 文件（本地可改）
─────────────────────────   ─────────────────────────
R6IdJowV5G47.yaml           saDMY9wRANlr.js       ← extend script
    │                       rJDbf1hBTouK.yaml     ← rules override
    ▼                               │
   合并 ─────────────────────────────┘
    │
    ▼
clash-verge.yaml (运行时最终配置)
```

## Core Operations

### 1. 查看当前配置

读取两个 override 文件 + 最终合并配置，展示当前状态。

```bash
# extend script
cat "~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/saDMY9wRANlr.js"
# rules override
cat "~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/rJDbf1hBTouK.yaml"
# 最终合并配置（含所有规则的完整视图）
cat "~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml"
```

### 2. 测试域名连通性

用 `curl` 直连（不走代理）批量测试域名，输出 HTTP 状态码、耗时、远端 IP。

```bash
curl -o /dev/null -s -w "HTTP:%{http_code} time:%{time_total}s remote:%{remote_ip}" \
  --connect-timeout 10 --max-time 15 "https://目标域名"
```

**判断标准**：
- `HTTP 2xx/3xx/4xx` → 可达
- `HTTP 000` 或 `exit!=0` → 被墙

测试结果用于决策每个域名走 DIRECT 还是 PROXY。

### 3. 生成/同步决策表

将连通性测试结果写入飞书多维表格，供用户逐一勾选 DIRECT 或 代理。

多维表格字段：
- 规则 (Text) — 域名规则原文
- 直连测试结果 (Text) — 测试结论
- DIRECT (Checkbox) — 勾选表示走直连
- 代理 (Checkbox) — 勾选表示走代理
- 分类 (Single Select: 域名规则 / IP段规则)

### 4. 应用规则（从决策表到 rules override）

1. 读取飞书多维表格中用户的 DIRECT/代理 checkbox 决策
2. 将勾选 DIRECT 的规则写入 `prepend`，将对应的旧 PROXY 条目写入 `delete`
3. 保持 PROXY 的规则不动（维持原远程订阅行为）
4. 写入 `rJDbf1hBTouK.yaml`
5. 提示用户在 Clash Verge GUI 中刷新 parko profile

**Rules override 模板**：[templates/rules-override.yaml](file:///Users/park0er/.claude/skills/clash-verge/templates/rules-override.yaml)

### 5. 编辑 extend script

修改 `saDMY9wRANlr.js`：

- DNS `nameserver-policy` — 哪些域名走内网 DNS（多接口并发：`dhcp://en0` + `dhcp://en1` + `system`）
- `fake-ip-filter` — 哪些域名不做 fake-ip 缓存（内网域名 + CNAME 终点）
- `fake-ip-range` — 避开小米 198.18.0.0/16 冲突
- 链式代理 — 入口节点 / 出口节点 / 保活参数
- TCP 保活 — `keep-alive-interval` / `keep-alive-idle`

**Extend script 模板**：[templates/extend-script.js](file:///Users/park0er/.claude/skills/clash-verge/templates/extend-script.js)

### 6. 生效

修改后，在 Clash Verge GUI → Profiles → 右键 parko → 刷新。无需重启。

⚠️ **注意**：GUI 刷新才会重新执行 override 合并。直接改运行时 `clash-verge.yaml` + 调 mihomo reload API 只对当前进程生效，下次订阅更新会被覆盖。持久化改动必须落在 override 文件里。

## 关键设计决策

- **DNS 源策略（2026-07-06 修正）**：
  - `officeDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1", "system"]` — 裸 IP 优先（最快最稳）+ dhcp fallback + system 兜底
  - `blockedDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1"]` — 裸 IP 优先 + dhcp fallback，保守不加 system
  - `default-nameserver = ["10.234.253.8", "10.234.254.8"]` — mihomo 启动 bootstrap DNS
- **裸 IP 是 TUN 模式下最可靠的 DNS 源（2026-07-06 实测恢复）**：
  - 2026-06-03 原始结论"裸 IP 是唯一可靠格式"是对的
  - 2026-07-05 误判"裸 IP 无效"是没实测就推翻，引入 dhcp:// 不稳定
  - 2026-07-06 实测裸 IP 5/5 成功：内网域名拿真实 IP `10.16.64.145`，被墙域名 youtube 拿 Google 真实 IP `142.250.204.46`
  - **真相**：mihomo 内部 DNS 查询不被自己的 TUN dns-hijack 拦截，裸 IP 直连小米 DNS 成功。外部进程（dig/nslookup）的 UDP:53 才会被 TUN 拦截返回 fake-ip——这是诊断时容易误判的坑：dig @10.234.253.8 拿到 fake-ip 不代表裸 IP 无效。
  - **小米办公网透明代理拦截所有 UDP:53 查询**（无论目标是小米 DNS 还是公网 DNS），mihomo 内部 DNS 发到 `10.234.253.8:53` 也被拦截拿到真实 IP。不存在"查询离开办公网被 GFW 污染"。
- **fake-ip-range 改为 28.0.0.1/16**：避开小米内网默认的 198.18.0.0/16 冲突。
- **CNAME 终点必须覆盖**：内网域名（如 `llm.mioffice.cn`）常 CNAME 到 `*.mi-dun.srv`。必须把 CNAME 终点域名同时加入 `nameserver-policy`、`fake-ip-filter`、rules `DIRECT`，否则：
  1. CNAME 链最终 A 记录走 fallback 公网 DNS → 解析失败
  2. mihomo 从 TLS SNI 嗅探到 CNAME 终点域名 → 重新匹配规则 → 落到 `MATCH,PROXY` → 内网域名走代理失败
- **链式代理**：parko-tokyo（入口）→ 圣何塞静态ip2（出口），套 url-test 保活组。节点找不到不会瘫痪——脚本静默跳过。
- **规则优先**：rules override 的 `prepend` 在远程规则前匹配，配合 `delete` 删除冲突的远程规则实现覆盖。
- **DIRECT 决策原则**：
  - **小米办公网有透明代理**：拦截所有 UDP:53 DNS 查询返回真实 IP（不污染），TCP 443 直连真实 IP 可达。被墙域名（youtube/x.com/telegram/github全家桶/kiro.dev）在办公网下走 DIRECT 比走代理快 3-4 倍。
  - **mihomo 内部 DNS 配合**：被墙域名在 extend script 加 `nameserver-policy` 指向裸 IP `10.234.253.8`（+ dhcp fallback），mihomo 内部 DNS 发到 `10.234.253.8:53` 被办公网透明代理拦截，拿到真实 IP。
  - **部分域名虽可达但用户选择走 PROXY**：google（gemini 时好时坏）、anthropic.com/claude.ai（AI 用途统一走代理）、wikipedia.org。这些不需要加 nameserver-policy。
  - 内网 CNAME 终点（`*.mi-dun.srv`）必须显式 DIRECT（见上条）。
  - **决策真源**：飞书多维表格 `app_token=XfzGbZm9fawyg6sRxitcn6gTnnh` `table_id=tblPc0MkdOGUhigm`。改动先改表格，再同步 rules override。

## 排错速查

| 症状 | 可能原因 | 诊断方法 |
|------|----------|----------|
| 内网域名解析失败 | DNS 源失效（dhcp://en1 抖动 / 裸 IP 未配） | `curl --unix-socket /tmp/verge/verge-mihomo.sock "http://localhost/dns/query?name=XXX&type=A"` 看返回的 Status 和 Answer |
| 内网域名拿到 fake-ip | CNAME 终点不在 fake-ip-filter / DNS 源全部失败 fallback 到 fake-ip | 同上，看 Answer 里 A 记录是 `10.x.x.x` 还是 `28.0.0.x` |
| 内网域名走 PROXY | TLS SNI 嗅探到 CNAME 终点，落到 MATCH | 看 service 日志 `grep 域名 service_latest.log` |
| DIRECT 域名超时 | DNS 拿到 fake-ip 但 mihomo 没正确 NAT | 用 mihomo API 查 DNS 是否拿真实 IP |
| mihomo reload 不生效 | reload 不重新执行 override / default-nameserver 等 bootstrap 字段 | GUI 里右键 parko → 刷新 |
| dig @10.234.253.8 拿到 fake-ip | dig 是外部进程，UDP:53 被 TUN dns-hijack 拦截（不是裸 IP 无效） | 改用 mihomo API 查，不要用 dig/nslookup 诊断 mihomo 内部 DNS |
| 浏览器时好时坏 | Chrome 缓存了配置错误时的 fake-ip | `chrome://net-internals/#dns` Clear host cache + `chrome://net-internals/#sockets` Flush socket pools |

## Bitable 决策表

- 当前决策表：`app_token=XfzGbZm9fawyg6sRxitcn6gTnnh`, `table_id=tblPc0MkdOGUhigm`
- 每次连通性测试可覆盖更新记录
- 用户勾选后运行 "应用规则" 写入 `rJDbf1hBTouK.yaml`
