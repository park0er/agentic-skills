# clash-verge CHANGELOG

## 2026-08-02 — separate-home-vpn-boundary

- Routed home Xiaomi VPN plus Clash persistent recovery work to the dedicated skill.
- Kept this skill focused on general parko profile and rule management.

## 2026-07-14 — fake-ip-filter-wildcard-syntax-fix

**彻底解决内网网站"时好时坏"的根因。**

- **故障现象**:`ds.ad.xiaomi.com` 等多级子域内网网站,flush fakeip 缓存后必挂(HTTP 000),浏览器拿到 fake-ip `28.0.0.x` 但 mihomo 反查映射丢失直接拒绝连接。之前 `llm.mioffice.cn`(单级子域)能 work,`ds.ad.xiaomi.com`(多级子域)时好时坏。
- **根因**:mihomo fake-ip-filter 的 `*.` 和 `+.` 语法语义不同:
  - `*.xiaomi.com` → 只匹配 `foo.xiaomi.com`(单级子域),**不匹配** `ds.ad.xiaomi.com`(多级子域)
  - `+.xiaomi.com` → 匹配 `xiaomi.com` + 所有子域(包括多级)
  - 之前所有内网域名用 `*.` 语法,导致多级子域(`ds.ad.xiaomi.com` / `ai-native.kb.mi.srv` / `staging-multica.ad.xiaomi.srv`)没被 filter 命中,走 fake-ip 模式。浏览器拿 fake-ip → mihomo 拦截连接 → 反查 fake-ip→域名映射 → flush 后映射丢失 → 连接被拒 → "时好时坏"。
- **修复**:fake-ip-filter 所有 `*.` 改成 `+.`。
- **验证**:flush fakeip 后,6 个代表域名(ds.ad.xiaomi.com / llm.mioffice.cn / ai-native.kb.mi.srv / staging-multica.ad.xiaomi.srv / youtube.com / x.com)全部 HTTP 2xx/3xx 成功,内网域名 remote IP 全部是真实 `10.x.x.x`(不是 fake-ip `28.0.0.x`)。
- **教训**:
  1. mihomo fake-ip-filter 必须用 `+.` 语法,不能用 `*.`,`*.` 不匹配多级子域。
  2. "时好时坏"的根因是 fake-ip 映射缓存生命周期——首次解析成功缓存映射,flush/过期后重新解析偶发失败导致连接被拒。让域名绕开 fake-ip(走真实 IP)是彻底解决方案。
  3. 单级子域(`foo.mioffice.cn`)用 `*.` 能 work 是巧合,多级子域(`ds.ad.xiaomi.com`)必须用 `+.`。
- **诊断技巧**:flush fakeip 后立刻 curl,如果必挂 → fake-ip-filter 没生效,检查 `*.` vs `+.` 语法。

## 2026-07-13 — add-alb-xiaomi-srv-cname-endpoint

- **故障**:`staging-multica.ad.xiaomi.srv` 内网网站打不开,mihomo DNS 查 A 记录返回 NXDOMAIN,但查 CNAME 类型能拿到 `intranet-staging-4798-cn-north.alb.xiaomi.srv.`,单独查这个 CNAME 终点能拿到真实 IP `10.38.165.121`。
- **根因**:mihomo 在 fake-ip-filter 域名 + CNAME 链场景下,追查 CNAME 终点时 nameserver-policy 匹配比 rules 匹配更严格。`+.xiaomi.srv` 理论上匹配 `*.alb.xiaomi.srv`,但 mihomo 在 CNAME 追查时没正确匹配,导致 CNAME 链断裂返回 NXDOMAIN。
- **修复**:三处都显式加 `+.alb.xiaomi.srv`:
  - extend script `nameserver-policy["+.alb.xiaomi.srv"] = officeDNS`
  - extend script `fake-ip-filter` 加 `*.alb.xiaomi.srv`
  - rules override prepend 加 `DOMAIN-SUFFIX,alb.xiaomi.srv,DIRECT`
- **教训**:`alb.xiaomi.srv` 是小米内网 ALB(应用负载均衡)的通用域名,所有 staging/生产 ALB 服务都会 CNAME 到这里。跟 `+.mi-dun.srv` 一样,**CNAME 终点必须显式加 policy,不能依赖父域 `+.xiaomi.srv` 通配**——mihomo 的 nameserver-policy 在 CNAME 追查时匹配行为跟 rules 不同,子域通配不可靠。
- **诊断技巧**:mihomo DNS 查 A 记录返回 NXDOMAIN 但能查到 CNAME 时,用 mihomo API 单独查 CNAME 终点能否拿到真实 IP。能拿到 → mihomo CNAME 追查 bug,显式加 policy 修复。

## 2026-07-07 — add-mi-srv-suffix

- **故障**:`ai-native.kb.mi.srv` 内网网站打不开,mihomo DNS 返回 NXDOMAIN,curl HTTP:000。
- **根因**:域名后缀是 `.mi.srv`,但 nameserver-policy / fake-ip-filter / rules 只覆盖了 `+.xiaomi.srv`(`*.xiaomi.srv`),不匹配 `*.mi.srv`。
- **修复**:三处都加 `+.mi.srv`:
  - extend script `nameserver-policy["+.mi.srv"] = officeDNS`
  - extend script `fake-ip-filter` 加 `*.mi.srv`
  - rules override prepend 加 `DOMAIN-SUFFIX,mi.srv,DIRECT`
- **教训**:小米内网域名后缀分散(`mioffice.cn` / `mi.srv` / `xiaomi.srv` / `mi-dun.srv` / `mi-dun.com` / `xiaomi.com` / `mi.com` 等),新增内网网站时要确认域名后缀是否在覆盖范围。`+.mi.srv` 是个泛后缀,应该早点加上。

## 2026-07-06 — bare-ip-validated-and-restored

**根因复盘 + 实测验证,推翻 2026-07-05 两个错误结论。**

- **故障现象**:llm.mioffice.cn 等内网网站浏览器时好时坏,最终完全挂掉。mihomo 查询返回 `Status:3 NXDOMAIN` 或 fake-ip。
- **诊断过程**:
  1. 用 mihomo API 反复查询,发现 `dhcp://en1` 机制不稳定(5/5 全失败)。
  2. 验证裸 IP `10.234.253.8` 替代 `dhcp://en1` → 内网域名 5/5 拿到真实 IP `10.16.64.145`。
  3. 发现 `dig @10.234.253.8` 被 TUN dns-hijack 拦截返回 fake-ip,这是之前误判"裸 IP 无效"的根源——dig 是外部进程,UDP:53 被 mihomo 拦截,不代表裸 IP 真无效。
  4. 进一步验证被墙域名 youtube 走裸 IP → 5/5 拿到 Google 真实 IP `142.250.204.46`(非 GFW 污染 IP)。
- **关键认知更新**:
  - ❌ 推翻 2026-07-05 "裸 IP 无效已回滚" → ✅ 裸 IP 对内网域名 5/5 成功
  - ❌ 推翻 2026-07-05 "被墙域名不能用裸 IP 会 GFW 污染" → ✅ 被墙域名用裸 IP 拿到真实 IP
  - ✅ 恢复 2026-06-03 "裸 IP 是 TUN 模式下唯一可靠格式" 的原始结论
  - ✅ 新认知:小米办公网透明代理拦截**所有** UDP:53 查询(无论目标是小米 DNS 还是公网 DNS),mihomo 内部 DNS 发到 `10.234.253.8:53` 也被拦截拿到真实 IP。不存在"查询离开办公网被污染"。
- **修复方案**:
  - `officeDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1", "system"]` — 裸 IP 优先 + dhcp fallback + system 兜底
  - `blockedDNS = ["10.234.253.8", "10.234.254.8", "dhcp://en0", "dhcp://en1"]` — 裸 IP 优先 + dhcp fallback,保守不加 system
  - 新增 `default-nameserver = ["10.234.253.8", "10.234.254.8"]` — mihomo 启动 bootstrap DNS
- **验证结果**:7 个代表域名(llm.mioffice.cn / ds.ad.xiaomi.com / youtube.com / x.com / t.me / raw.githubusercontent.com / kiro.dev)DNS 全部拿到真实 IP,curl 全部 HTTP 2xx/3xx 成功。
- **教训**:
  1. **CHANGELOG 打架时要实测,不能假设新条目一定对**。2026-07-05 那条"纠正裸 IP"本身就是错的纠正,纠正纠正反而引入了 bug。
  2. **基于推理的结论必须实测验证**。"被墙域名不能用裸 IP 会 GFW 污染"是纯推理,没实测。
  3. **dig/nslookup 是外部进程,UDP:53 会被 TUN hijack 拦截**,用它们诊断 mihomo 内部 DNS 行为会误判。应该用 mihomo API `curl --unix-socket /tmp/verge/verge-mihomo.sock "http://localhost/dns/query?name=xxx&type=A"`。

## 2026-07-05 — bootstrap-auto-setup

- **新机器全自动搭建能力**：新增 `scripts/bootstrap.py`，让 `/clash-verge` 在新办公机上从 0 到 100 配置完成，零 GUI 操作。用户只需装好 Clash Verge Rev app 并启动一次初始化数据目录，其余全由脚本代劳。
- **能力范围**：脚本下载 parko 订阅注册为 remote profile → 从 `templates/` 拷贝 extend script + rules override 写入 `profiles/<uid>.js|yaml` → 修改 `profiles.yaml` 注册条目并绑定到 parko 的 `option.script` / `option.rules` → 修改 `verge.yaml` 开 TUN + 系统代理 → 设 parko 为 current profile。
- **设计依据**：Clash Verge 的 profile 绑定关系存在 `profiles.yaml`（普通 YAML 文件），override 通过 `uid` + `file` 引用文件，remote profile 的 `option.script` / `option.rules` 字段挂 override 的 uid。skill 直接写文件 + 改 YAML 等价于 GUI 的"编辑脚本/规则"按钮。uid 用 12 位 base62 随机生成（与 GUI 生成的格式一致）。
- **幂等性**：检测到 `profiles.yaml` 已含 `name: parko` 即拒绝重复导入，提示用户先在 GUI 删除。
- **SKILL.md 新增章节**："新机器全自动搭建（零 GUI 操作）"，触发词：新机器配置 clash / 从零搭建 clash verge / bootstrap clash。
- **流程对比**：旧流程 6 步（装 app → 导入订阅 → 创建 override → GUI 绑定 → 开 TUN/系统代理 → 验证）→ 新流程 3 步（装 app → 跑 bootstrap.py → 跑 /clash-verge 验证）。

## 2026-07-05 — fix-tun-sysproxy-coexistence

TUN + system proxy 双开模式下的根因定位与修复（在前一个 agent 留下的"开了 TUN 内网就挂"的雷上做实测验证）：

- **DNS 接口名错误**：extend script 只挂 `dhcp://en0`，但当前办公机主网卡是 `en1`（`ipconfig getpacket en0 failed: not found`）。改为 `["dhcp://en0", "dhcp://en1", "system"]` 多接口并发查询。mihomo 并发向所有源查询，无租约接口静默失败。
- **CNAME 终点未覆盖**：`llm.mioffice.cn` CNAME 链 `→ llm.mioffice.cn.v.mi-dun.com → cname-app-com.n.mi-dun.srv → 10.16.64.145`。CNAME 终点 `*.mi-dun.srv` 不在 nameserver-policy / fake-ip-filter / rules 里，导致：(1) A 记录走 fallback 公网 DNS 解析失败；(2) mihomo 从 TLS SNI 嗅探到该域名后重新匹配规则，落到 `MATCH,PROXY`。修复：`+.mi-dun.srv` 加入 nameserver-policy + fake-ip-filter + `DOMAIN-SUFFIX,mi-dun.srv,DIRECT`。
- **被墙域名改 DIRECT（关键突破）**：用户指出办公网天然能直连 youtube/x.com/telegram。实测确认：小米办公网有透明代理，拦截所有 UDP:53 DNS 查询返回真实 IP（不污染），TCP 443 直连真实 IP 可达。youtube/google/x.com/telegram/anthropic 改 DIRECT 后比走代理快 3-4 倍。
- **mihomo 内部 DNS 绕过透明拦截的解决**：mihomo 内部 DNS 查询绕过办公网透明拦截，默认拿 GFW 污染的假 IP。`system` 和裸 IP（10.234.253.8）都无效（已实测证伪 2026-06-03 那条错误经验）。解决：被墙域名在 extend script 加 `nameserver-policy` 指向 `dhcp://en1`，mihomo 直连小米 DNS 仍能被透明代理拦截，拿到真实 IP。
- **githubusercontent.com 改 DIRECT（订正）**：初判为 GFW 阻断需走 PROXY，但实测办公网透明代理可达，按飞书 Bitable 决策表改 DIRECT。`github.com` / `githubusercontent.com` / `github.io` 三个域名全部 DIRECT。
- **DNS 源分裂（officeDNS vs blockedDNS 不能统一）**：曾试图让被墙域名也加 `system` 与内网域名保持一致，结果 youtube 解析到 `104.244.42.197`（Twitter 的 IP，GFW 污染）。根因：mihomo 并发向所有 DNS 源查询，`system` 走 mihomo 内部查询绕过办公网透明拦截，拿到 GFW 污染的假 IP，且污染结果可能抢在 `dhcp://en1` 的真实 IP 之前返回。最终方案：内网域名 `officeDNS=[dhcp://en0, dhcp://en1, system]`（system 兜底无害，内网域名不被 GFW 污染）；被墙域名 `blockedDNS=[dhcp://en0, dhcp://en1]`（绝不加 system）。两条数组在 extend-script.js 模板里有详细注释解释为何不能合并。
- **SKILL.md 新增排错速查表**：5 个常见症状 → 原因 → 诊断方法。
- **纠正裸 IP DNS 错误经验**：CHANGELOG 2026-06-03 `restore-bare-dns-ips` 那条记录的"裸 IP 是 TUN 模式下唯一可靠格式"结论是错的——裸 IP 实测无效已回滚。mihomo 内部 DNS 查询绕过小米办公网透明 DNS 拦截，只有系统 DNS client 发出的查询才被拦截，所以必须用 `dhcp://enN` 或 `system`，不能填裸 IP。本次在 SKILL.md 和 extend-script 模板注释里明确标注"裸 IP 无效"防止再踩坑。

## 2026-07-05 — v2-rewrite-rules-override-driven

- **完全推翻旧架构**：删除 `scripts/setup_clash.py` 和 xiaomi/custom/personal-macmini profile 概念。旧脚本功能已被 parko extend script 内置。
- **新定位**：管理 parko profile 的两个本地 override 文件 —— extend script (`saDMY9wRANlr.js`) 和 rules override (`rJDbf1hBTouK.yaml`)。
- **新增能力**：连通性测试、飞书多维表格决策表、从决策表一键生成 rules override。
- **新增文件**：`templates/extend-script.js`、`templates/rules-override.yaml`、`reference/architecture.md`。
- **固化首次决策**：根据 2026-07-04 WiFi 直连测试结果 + 用户 checkbox 确认，7 条规则改 DIRECT（youtube/twitter/telegram/github/githubusercontent/t.me/telegram.org）。
- **删除文件**：`scripts/setup_clash.py`。

## 2026-06-03 — restore-bare-dns-ips

- Restored `nameserver-policy` to bare Xiaomi internal DNS IPs: `["10.234.253.8", "10.234.254.8", "system"]` (same as original v1). Deep-research confirmed: bare IPs are the only reliable format for corporate intranet DNS under TUN mode — Mihomo sends them as UDP:53, routed DIRECT via cncidr, reaching Xiaomi DNS servers directly. `system`, `dhcp://en1`, and `udp://` prefixes all failed because Mihomo's internal DNS queries bypass the OS-level transparent DNS interception that Xiaomi network provides. If these IPs ever change, run `ipconfig getpacket en1` to discover new ones and update the script.

## 2026-06-03 — explicit-dns-for-tun (REVERTED)

- **REVERTED**: Attempted `["udp://114.114.114.114", "udp://223.5.5.5"]`. Despite `udp://` being a valid Mihomo DNS format (bare IPs are internally converted to `udp://`), it caused total DNS failure because Mihomo's internal UDP queries bypass Xiaomi's transparent DNS interception — only queries from the system DNS client get intercepted. Reverted to `["dhcp://en1", "system"]`, then to bare IPs.

## 2026-06-03 — fix-fakeip-range-conflict

- Fixed fake-ip range collision with Xiaomi intranet: Clash's default `198.18.0.1/16` fake-ip range overlaps with Xiaomi's real DNS response `198.18.0.61` for `mioffice.cn`. Switched fake-ip-range to `28.0.0.1/16` to avoid conflict.
- Added `IP-CIDR,198.18.0.0/16,DIRECT,no-resolve` as fallback rule in case any Xiaomi service uses this IP segment.
- Both `dns_block` and `full_script_template` updated in setup script.

## 2026-06-02 — sync-live-config

- Synced live Clash Verge config back to skill: added `apple-cloudkit.com`, `icloud.com`, `icloud-content.com` (iCloud DIRECT routing to save VPN traffic), `multica.ai`, and `typeless-static.com` to default Xiaomi domains.
- Fixed chain proxy entry node from `"美国C01"` to `"香港02"` to match current live config.
- Fixed SKILL.md script path from `.gemini/config` to `.claude` (correct Claude Code skill path).

## 2026-06-01 — add-mitvos-com

- Added `mitvos.com` (Xiaomi intranet hosting/domain) to the default domains list to fix access to internal services like Protofly.

## 2026-06-01 — add-mi-dun-com

- Added `mi-dun.com` (Xiaomi's Zero-Trust / Mi-Dun security gateway) to the default domains list to fix authentication redirect issues when logging into intranet sites.

## 2026-06-01 — add-xiaomi-net-olap-srv

- Added `xiaomi.net` and `olap.srv` to the default domains list for the Xiaomi profile to ensure complete intranet coverage and resolve OLAP/ad platform access issues.

## 2026-06-01 — dynamic-dns-and-profiles

- Switched from hardcoded DNS IP addresses to Mihomo's `dhcp://[interface]` scheme to dynamically adapt to DHCP network changes.
- Added support for `--profile` argument (`xiaomi` default and `custom` for external corporate environments).
- Integrated automatic active network interface detection via default route scanning.
- Maintained backward compatibility and smart merge behaviors.

## 2026-06-01 — add-full-template

- Upgraded setup script to write the complete optimized template (TCP settings + St. Jose Chain Proxy + DNS Policy) when configuring a clean environment.
- Preserved smart-injection logic to merge only DNS configurations if St. Jose Chain Proxy is already configured.
- Cleaned up domestic domain/IP rules.
