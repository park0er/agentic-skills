# Agent Sync Doctor v4 整体方案

**日期**：2026-05-13
**版本**：v4（取代 v3；v3 归档在 git 历史）
**关联事件**：[ISSUES-2026-05-13-codex-data-loss.md](../ISSUES-2026-05-13-codex-data-loss.md)
**本次 v4 相对 v3 的变化**：
- 新增 **Req #6**：File-Provider dataless detection（由另一台 Mac 的 agent 通过
  配套 skill `icloud-materialization-doctor` 已实现；v3 漏写了这件事）
- 新增 **第 9 节 "Factory 跨机协作规范"**：明确 Factory 的 source of truth 是
  GitHub origin，iCloud 完全不管 `.git/`；并给出双 Mac 并行修改的标准流程
- Roadmap 阶段 0 补齐：audit 工具共 3 个（session-integrity / scan-conflicts /
  icloud-materialization check）

---

## 1. Executive Summary

2026-05-13 的 Codex 数据丢失事件暴露了 agent-sync-doctor 在 iCloud-backed
跨机同步场景下的 **5 类系统性盲区**（v3 识别了 4 类，v4 补齐第 5 类）：

| 盲区 | 今天的具体症状 | 根本原因 |
|---|---|---|
| A. State ↔ 数据一致性 | session 019dfd1c 的 state_5.updated_at 比 jsonl 内容晚 4h40min | doctor 只检查 symlink topology，不对比内容一致性 |
| B. iCloud 冲突残骸 | 5/7 的 `config.toml.conflict-*` 静默吞 14 条 plugin enable | doctor 不扫 `*.conflict-*` / `* N` / `* copy` 命名模式 |
| C. TOML section 合并语义 | `[plugins.*]` 被 last-writer-wins 合并，unique enable 条目丢失 | merge 策略是全文件覆盖而非 section-aware union |
| D. 机器身份漂移 | 同一 iMac 以 `-11`/`-200`/`-303` 三个 hostname 出现 | state 文件用 `hostname` 当 key，macOS mDNS 冲突会自动换名 |
| E. File Provider dataless state | macOS 12+ 的"下载但 st_blocks=0"文件 `find -name '*.icloud'` 漏判 | doctor 的 iCloud readiness check 停留在 placeholder 后缀语义 |

**已做完**：
- A、B、E 加了只读审计工具（`session-integrity`、`scan-conflicts`、通过配套
  skill `icloud-materialization-doctor` 的 `check`）
- Factory 结构从"只有 ISSUES.md"恢复到完整代码 + plans

**未做**：
- C、D 两类系统性修复
- 把审计工具插进 `leave` / `arrive` 的前置检查
- Session jsonl 的 durability 增强
- Plugin 存储架构的重新设计（移除 `plugins/` 的 iCloud 同步）

---

## 2. Plugin 问题的根因与修复策略

### 2.1 调查结论

Codex 26.506 的 plugin 存储实际上是 **双 layout 并存**，但两者职责完全不同：

| Layout | 路径 | 大小 | 是否需要跨机同步 | 现状 |
|---|---|---|---|---|
| **新** | `~/.codex/.tmp/plugins/plugins/<plugin>/` | 31 MB | ❌ 不用（每台 Mac 自己 git clone） | 干净的 git 仓库 |
| **新** | `~/.codex/.tmp/marketplaces/<mp>/` | 76 MB | ❌ 不用 | 每台 Mac 各自拉 |
| **新** | `~/.codex/.tmp/bundled-marketplaces/openai-bundled/plugins/` | 93 MB | ❌ 不用（Codex app bundle 内置） | 每台 Mac 安装时自带 |
| **旧** | `iCloud/dotcodex/plugins/cache/<mp>/<plugin>/<version>/` | 89 MB | ❓ 看起来是被遗留的 | **深度污染**：30+ `superpowers N`、`warp 2`/`3`、`plugin-install-*` |
| **元数据** | `config.toml` 的 `[plugins."<id>@<mp>"]` 段 | <10 KB | ✅ **需要同步**（enable 状态是跨机共享的意图）| 当前 28 条，5/7 曾被静默吞到 13 条 |

**关键洞察**：plugin 真正跨机共享的只有"enable 列表"这 <10 KB 的声明性信息，
其它（源码、bundle）都是机器本地可再生资源。但 doctor 目前把整个 `plugins/`
目录 symlink 到 iCloud，导致大量本质上是本地缓存的文件被卷进 iCloud 冲突
机制，产生了 30+ 个 ` N` 后缀副本。

### 2.2 修复策略（建议优先级）

**P0 — 立刻（不用动 doctor）**：
- 用户已把 config.toml 从 13 条手工恢复到 28 条。无需再处理。

**P1 — 清理污染（手动一次性）**：
- 清 iCloud `plugins/cache/` 里的 30+ 个 macOS 冲突副本（`superpowers 6/7/8/9/12`、
  `warp 2/3`、`hyperframes 2`、5 个 `plugin-install-*`、3 个 `plugin-backup-*`）。
  这些文件不是数据源，删掉不影响功能；保留只会继续触发 `scan-conflicts` warning。
- **动作**：写一个 `clean-legacy-plugin-cache` 辅助脚本（dry-run 默认），扫冲突
  命名 pattern + 对应 ` \d+` 数字后缀，列出来、用户确认后再删。放在 skill 的
  `scripts/` 下作为独立工具。

**P2 — 根治（doctor v4 的 C、D 两项）**：见第 3 节。

### 2.3 不推荐的路径

- ❌ **不要**把 `.tmp/` 纳入 doctor 同步范围：会把每台 Mac 的 git 本地对象
  （`.git/objects/pack/*.pack`）卷进 iCloud 冲突，**重演** `plugins/cache/` 现在
  的状态。且 plugin 源码是可再生物，不是真源。
- ❌ **不要**继续 symlink `plugins/` 到 iCloud：这正是污染的根源。

---

## 3. 设计需求 → doctor 代码改动映射

### Req #1：`[plugins.*]` 必须 union-by-key 合并

**当前行为**：doctor 的 arrive 对 `.codex-global-state.json` 做 smart merge，但
`config.toml` 作为**整文件单元**处理（走 `LOCAL_FILE_DIFFERS_FROM_CLOUD` 的
"decision: local/cloud"），而 `[plugins.*]` 是 section 级语义。两者粒度不匹配。

**v4 提议**：
- 在 arrive 的 merge 阶段新增 `_merge_toml_plugins_union(local, cloud) -> dict`。
- 合并规则：
  ```
  plugins_keys(local) ∪ plugins_keys(cloud) →
      对每个 key k：
          if k in both: 选 enable=true 的（truthy wins）；其余字段优先 cloud
          if k only in local or only in cloud: 保留
  ```
- 非 `[plugins.*]` 段继续走原先的 file-level diff。
- **关键不变式**：合并后 `len(plugins_keys(merged)) >= max(len(local), len(cloud))`。
- Leave 阶段对称：推云端前同样做 union，不让本机的 "禁用" 操作悄悄删了其他 Mac 的 enable。

**实现位置**：`ProductDoctor.arrive_merge()` 附近加一个 codex-only 的 TOML
处理分支，参考现有的 `smart_merge_json` 骨架。

**测试**：加 fixture 模拟"本机 A enable 1/2/3，云端 B enable 2/4/5"→ 合并后
应 enable 1/2/3/4/5。

### Req #2：`~/.codex/plugins/` 不该 symlink 到 iCloud

**当前行为**：`products.codex.json` 里把 `plugins` 作为 symlink 管辖 entry。
leave 时 relink、arrive 时 verify symlink。这让所有本机 plugin 下载都强制
走 iCloud，触发大量冲突。

**v4 提议**：
- 从 `products.codex.json` 的 entries 里**移除 `plugins` 条目**。
- doctor 只管理 `config.toml` 的同步（`[plugins.*]` 声明），不管 plugin 源码。
- 迁移期（arrive 首次检测）：如果本机 `~/.codex/plugins/` 还是 symlink，给出
  去 symlink 的建议（但不自动做，保守策略）。
- 文档更新：说明"plugins 源码是本地缓存，每台 Mac 自动从 marketplace 拉；
  doctor 只管 enable 列表"。

**关联清理**：完成 Req #2 后，iCloud 里的 `plugins/cache/` 整个目录可以被
清理（或保留做历史档案，但至少从 sync manifest 里移除）。

### Req #3：Session JSONL append 丢失无保护

**今天学到的细节**：5/9 13:02:37 那次 turn 25 标记为 `interrupted`，jsonl
停在 13:02:37，后面 4h40min state_5 的 `updated_at` 被 heartbeat 推到 17:42
但无 jsonl 写入。这次的场景**可能不是**"Codex 崩了没 flush"（ISSUES.md 的
原假设），而是"turn 被服务端 / 网络中断，Codex 正常 close 时把 updated_at 推了"。

但 ISSUES.md #3 的**核心担忧**仍然成立：doctor 对 jsonl durability 毫无保护。
如果某天真的发生 Codex 进程 kill -9 导致内容没落盘，doctor 无法救。

**v4 提议（分层）**：
- **轻量层**：doctor 每次 `check` 时跑 `session-integrity` 作为常规输出的一部分，
  把 phantom activity > 30min 且 tokens>0 的 thread 列为 warning。**不阻塞** leave，
  只通知用户"有可疑 thread，你自己决定是否需要人工检查"。
- **中量层**：在 doctor 的 `check` / `leave` 输出加 **last-jsonl-ts per thread**
  字段，以便事后回查（成本低，大约每 thread 2 个 syscall）。
- **重量层（未定）**：真正的 durability 增强（比如每 N 秒 hard-link jsonl 到
  本地快照目录）需要 Codex 端 hook 或 macOS launchd watcher，超出 doctor 本身
  职责。**建议列为 TODO，不在 v4 范围**。等有第二次真实数据丢失 incident
  再讨论。

**选择性补充**：可以考虑在 leave 前置检查里扫一遍：
"有没有 thread state_5.updated_at < now()-5min AND jsonl 已 hours 未更新，且
tokens_used > 0，且 `latestTurnStatus` 未知"——这种是典型"未完成的 thread 被
带走了"，提示用户"是否要等 Codex 主动退出再 leave？"。这个和 ISSUES.md #3
精神一致，但实现上只是 session-integrity 的自动化调用，不是真 durability。

### Req #4：iCloud conflict file 必须告警

**今天已做**：`scan-conflicts` 子命令上线。在真实数据上验证成功
（找到 Codex 15 个 + Claude 4 个 conflict 残骸，包括 5/7 事件的物证
`config.toml.conflict-ParkerdeiMac-11-20260507-224331`）。

**v4 额外提议**：
- 把 `scan-conflicts` 的结果自动并入 `check` / `leave` 的默认输出。
- 在 `leave` 前置检查里，**有 conflict 残骸就拒绝**（返回 blocked state），强制
  用户先 review 再继续。提供 `--ignore-conflicts` 逃生口用于"我知道了，就是
  想继续"场景。
- `arrive` 侧也同样检查：如果发现新的 conflict 文件（比如 iCloud 刚推下来），
  提示"你离开前这些可能没存在过，建议看一眼再 restore"。

### Req #5：hostname 漂移用 IOPlatformUUID 去重

**今天验证**：这台 iMac 的 IOPlatformUUID = `3AB03F37-F32F-521C-9D18-94B2D5FDB63A`，
但 mDNS 三次冲突导致 doctor state 目录里以 `ParkerdeiMac-11/-200/-303` 三个 key
存在。每次 bump 都丢了"上一身份"的历史信息。

**v4 提议**：
- doctor 内部引入 `machine_id()` helper：优先 IOPlatformUUID（稳定 16-byte hex），
  退化到 hostname。
- state 文件命名从 `<hostname>.local.json` 改为 `<machine_id>.json`（纯 UUID，
  不带 `.local` 后缀）。
- state 文件内容里**增加 `hostnameHistory` 数组**，记录这台机器曾经用过的所有
  hostname，便于审计。每次 check/leave 自动 append（去重）。
- **迁移策略**：首次切到 UUID key 时，自动检测 `<old-hostname>.local.json` →
  如果 UUID 未见过，把旧文件 rename 到 `<uuid>.json`；如果多个旧 hostname 对
  同一台 UUID，做 union merge（按 `updatedAt` 取最新的 entries）。

**副作用防范**：iCloud state 目录是共享的，其它 Mac 看到 UUID 命名的文件不
认识怎么办？→ 需要同时升级所有 Mac 的 doctor 版本，或者兼容两种命名（过渡期
同时写 hostname 和 UUID，逐步切过去）。

### Req #6：File Provider dataless state 检测（v4 新增）

**背景**：macOS 12+ 对 iCloud 文件的 "未下载" 语义做了重大变化：

- **Pre-12 （legacy）**：未下载文件显示为 `<原名>.icloud`，内容是占位符元数据。
  `find -name '*.icloud'` 可以精确定位。
- **12+ File Provider**：同名文件保留原名，但物理上 `st_blocks == 0`（占位），
  打开时自动触发下载。`find` 看不出来，**老检查**在 macOS 12+ **完全失效**。

**doctor 的原检查依赖 `*.icloud` pattern**（见 `arrive` 的 "等 iCloud 下载完成"
步骤），在 macOS 12+ 上会给出假阳性 ready 信号，然后 `arrive` 去 merge 实际上
还没下载完的文件，引发各种非确定性故障。

**今天已做**（由另一台 Mac 的 agent 完成）：
- 新建配套 skill **`icloud-materialization-doctor`**，独立负责 File-Provider
  dataless 检测（`check --json` 返回 dataless count）。
- `agent-sync-doctor` 通过 subprocess 调用它，接入 `icloud-check` 和 arrive 前
  置检查。
- **Fail-open 设计**：配套 skill 未安装时返回 `datalessCount = None`，doctor
  回退到老的 placeholder-only 行为并在输出里提示安装。
- SKILL.md 里 "Handoff 工作流" 现在明确要求 "`dataless = 0` 也要满足"。

**v4 尚未做**：
- 配套 skill 只装在 `.claude/` 和 Factory，**`.agents/` 还没装**。下次
  `release.sh` 跑两个 skill 时要同时 release。
- `leave` 前置没接入 dataless 检查（只有 arrive 接入了）。建议对称处理。

---

## 4. v4 Roadmap（建议执行顺序）

```
阶段 0（已完成，2026-05-13）
  ✅ session-integrity（Req A 的只读审计）                         [本 agent]
  ✅ scan-conflicts（Req #4 的只读审计）                           [本 agent]
  ✅ File Provider dataless 检测（Req #6）通过配套 skill           [另一 agent]
  ✅ Factory 结构恢复                                              [本 agent]
  ✅ ISSUES.md 复盘文档                                            [早期 agent]

阶段 1（小改，1 次 release，优先级高）
  □ 把 session-integrity 并入默认 check 输出
  □ 把 scan-conflicts 并入默认 check 输出
  □ leave 前置接入 File Provider dataless 检查（对称 arrive 已有）
  □ leave 前置：有 phantom activity (tokens>0, gap>30min) 或 conflict 残骸 → warn 但不阻塞
  □ 把配套 skill icloud-materialization-doctor release 到 .agents/ 侧
  □ 文档：更新 SKILL.md 反映默认检查增强

阶段 2（中改，下一次 release，Req #4 强化）
  □ leave 前置：conflict 残骸 → 阻塞（加 --ignore-conflicts 逃生口）
  □ arrive 后置：提示新出现的 conflict 残骸
  □ clean-legacy-plugin-cache 辅助脚本（独立工具，dry-run 默认）

阶段 3（Req #1 + #2，plugin sync 架构重构）
  □ 实现 `_merge_toml_plugins_union`，arrive 和 leave 两侧都用
  □ 从 products.codex.json entries 移除 plugins 条目
  □ 迁移期支持：检测到 plugins/ 还是 symlink 时提示去 symlink（不自动）
  □ 一次性 cleanup：iCloud plugins/cache/ 里 30+ 冲突副本清理
  □ 测试 fixture：模拟多 Mac 并发 enable/disable 场景

阶段 4（Req #5，hostname 漂移修复）
  □ machine_id() helper + state 文件改 UUID 命名
  □ 迁移 script：旧 hostname.local.json → UUID.json (union merge)
  □ state 内容新增 hostnameHistory 数组
  □ 两台 Mac 协同升级测试（避免一台新一台旧导致 state 分裂）

阶段 5（Req #3，jsonl durability，可延期）
  □ 仅在出现第二次真实数据丢失 incident 后启动
  □ 探索 Codex hook / macOS launchd watcher 的可行性
  □ 或放弃 doctor 侧防护，依赖 Time Machine/Backblaze 等外部备份
```

---

## 5. 已知 Open Questions（需要调研或用户决策）

1. **Codex 启动时的 plugin 加载顺序**：Codex 启动时先读 `.tmp/plugins/plugins/`
   还是 `plugins/cache/`？如果先读 `.tmp/` 就没事，如果 fallback 到旧 cache 会
   继续引入冲突副本被读到的风险。→ **需要 Codex 源码验证**，或对 `.tmp/` 清空
   后看 Desktop 行为。

2. **`plugin-restore` 真实动作**：今天 18:39 那次 `config.toml.bak.pre-plugin-restore`
   是用户手工做的（已确认）。但 Codex 自己的"Reload marketplace"点击到底干啥？
   会不会重写 `[plugins.*]` 覆盖某些 enable？→ **需要 UI 操作实测**。

3. **iCloud 冲突清理的安全边界**：iCloud `plugins/cache/<mp>/<plugin> N` 这些
   副本，如果某个 Codex 运行时把 symlink 解到了"副本"而不是正本，清理会不会
   破事？→ **保守：清理脚本 dry-run 默认 + 人工 review**。

4. **machine_id 迁移期的双命名兼容**：如果 Mac A 升级到 v4，Mac B 还是 v2，Mac A
   写 UUID.json 而 Mac B 读不懂；反过来 Mac B 写 hostname.local.json Mac A 读旧
   的。需要 grace period 里同时读写两种命名，或强制两台机器同时升级。→ **决定
   升级策略前暂不动**。

5. **Time Machine / Backblaze 作为 fallback durability**：用户是否已有外部备份
   方案？如果 session jsonl 丢失是灾难场景，外部备份应该是第一防线，doctor
   只是监控层。→ **需问用户是否已有**。

6. **icloud-materialization-doctor 的生命周期**：这个配套 skill 现在是独立的，
   还是应该合并进 agent-sync-doctor 作为内嵌模块？**独立有独立的好处**（单一
   职责、其它工具也能复用），但两个 skill 的版本必须协同演进，release 流程要
   配对。→ **暂保留独立，下一次有相关需求变动时再评估**。

---

## 6. 本次 incident 给 skill 设计的普遍教训

1. **topology check 不是 integrity check**。symlink 正确 ≠ 内容一致。凡是
   "符号链接健康"的系统，必须配一个"数据一致性"审计层。

2. **iCloud 的 last-writer-wins 对 TOML section 是危险的**。任何"列表增量
   修改"类型的文件（enable 列表、pinned 项、项目顺序等），跨机 merge 都应该
   是 union 而非 overwrite。

3. **macOS iCloud 自动加 ` N` 后缀**是冲突发生的**唯一外显信号**，但这个信号
   不会报警、不会日志。任何多 Mac iCloud 工具必须主动扫这个 pattern。

4. **UUIDv7 时间戳是取证金标准**。thread id 的前 48 位是毫秒级 epoch，任何
   时间线重构都应该优先用它而非依赖 file mtime 或 SQLite row 字段。

5. **state 文件以 hostname 作 key 是陷阱**。macOS mDNS 冲突会无感换名，
   每次换名都等于"这台机器在 state 目录变身成了新 Mac"，历史信息分裂。

6. **plugin 源码不需要同步**。只有"用户意图"（enable 列表）是跨机共享的状态；
   其它都是本地缓存。把二者混到一个 symlink 管理层是架构错误。

7. **macOS iCloud 的 "是否就绪" 语义是系统版本敏感的**。`*.icloud` 占位符
   pattern 是 pre-12 世界观，12+ 换成了 File Provider dataless（`st_blocks=0`）。
   任何 iCloud 就绪检查必须同时覆盖两种模式。

---

## 7. 本方案外的相关文档

- `ISSUES-2026-05-13-codex-data-loss.md`：当天事件现场复盘
- `SKILL.md` 的"数据完整性审计"章节：阶段 0 session-integrity + scan-conflicts 文档
- `SKILL.md` 的"Handoff 工作流 / 配套 skill"章节：阶段 0 dataless 检测接入说明
- `~/Documents/Coding/Foundations/Codex-Sync-Design/Codex-Sync-Plan-V3.md`：
  更早的 Codex sync 大设计（预存在，内容与本方案有重叠但颗粒度不同）
- 配套 skill 路径：`Skill_Factory/skills/icloud-materialization-doctor/`

---

## 8. 决策点（需要用户输入）

在开始任何阶段 1+ 的代码改动前，请用户明确：

- [ ] 阶段 1 是否按上述顺序立即开始？（只读审计自动化，风险低）
- [ ] 阶段 2 的 conflict "阻塞" leave 是否过于强硬？是否要先做成"默认 warn、
      加 --strict 才阻塞"？
- [ ] 阶段 3 的 plugins 去 symlink，是否接受用户在两台 Mac 各自重新 "Reload
      marketplace" 一次的代价（一次性）？
- [ ] 阶段 4 的 UUID state 文件迁移，是否准备好同时升级两台 Mac 的 doctor 版本？
- [ ] 阶段 5 的 jsonl durability，是否有外部备份（Time Machine / Backblaze）
      降低紧迫性？
- [ ] Req #6 的配套 skill：`.agents/` 侧什么时候 install 一次，和 doctor 下次
      release 一起？

---

## 9. Factory 跨机协作规范（v4 新增；2026-05-13 晚修正）

> **修正说明**：本节初版（同日早些时候写的 v3 / v4 初稿）基于错误假设
> "`~/Documents` 不是 symlink → iCloud 不管 Factory / `.git/`"。2026-05-13
> 晚实测纠错：`~/Documents` 确有 File Provider xattr
> `com.apple.file-provider-domain-id`，`brctl status` 显式列出
> `Under /Documents/Coding/PLAYGROUND/Skill_Factory/.git`。**整个 Factory
> 包括 `.git/` 都在 iCloud 同步范围内**。下文反映修正后的真相。

### 9.1 现状事实（修正后）

| 项目 | 实际情况 |
|---|---|
| iCloud Drive Documents sync | ✅ **启用**。`defaults read MobileMeAccounts` 显示 `CLOUDDESKTOP status = active`、`MOBILE_DOCUMENTS Enabled = 1` |
| `~/Documents` 目录性质 | 不是 symlink，但是**被 File Provider 接管的真目录**。xattr 含 `com.apple.file-provider-domain-id: com.apple.CloudDocs.iCloudDriveFileProvider/<uuid>` |
| Factory 物理位置 | `/Users/park0er/Documents/Coding/PLAYGROUND/Skill_Factory` — 在 iCloud 同步下 |
| `Mobile Documents/.../Documents/Coding/PLAYGROUND/Skill_Factory` | inode **9073828**，与本地路径**同 inode** —— 同一文件系统对象，两条路径等价 |
| `.git/` 是否同步 | ✅ **是**。`brctl status` 里明确列出 `Under /Documents/Coding/PLAYGROUND/Skill_Factory/.git` |
| GitHub remote | 存在：`https://github.com/park0er/Skill_Factory.git`（`origin`）。和 iCloud 同步**并行**工作 |

### 9.2 为什么 iCloud 同步 `.git/` 是高风险配置

即使当前**没出**明显 corrupt，也不代表安全。理论上的风险点：

1. **`git gc` 的非原子性**：delete 老 pack + create 新 pack + 更新 refs 横跨多
   文件。iCloud 按文件顺序同步到另一台 Mac，中间某个时刻 ref 指向"还没上传
   的 object" → 仓库 corrupt。
2. **`.git/refs/heads/main` 的 last-writer-wins**：两台 Mac 同时 commit →
   各自写自己的 sha → iCloud 保留一个，另一个的 commit 从 ref 视角"丢了"
   （object 在 `.git/objects/` 里还在，但 ref 不指向它了）。
3. **`.git/index` 是 machine-specific**：包含本地文件 stat 的缓存。跨机同步会
   让 git 觉得"所有文件都被动过"，每次操作触发 re-hash，性能下降。
4. **`.git/packed-refs` 与 `.git/refs/` 的一致性**：两者互为 fallback，iCloud
   部分同步会让两者错位，git 看到的 ref 随命令不同而变。

### 9.3 为什么**当前**还没爆炸（基于 2026-05-13 的实测）

- `scan-conflicts` 扫 Factory/.git 内**未**发现 `*.conflict-*` / `* N` / `* copy` 文件
- `.git/objects/` 所有文件 `st_blocks != 0`（没 dataless 状态）
- `git reflog` 干净 5 条，本机 HEAD = origin/main = `b2652c3`

**可能的解释**：
- 运气 —— 两台 Mac 最近没在同一秒并发 commit
- File Provider 对 small-file heavy-write 有 batch 或 defer，降低了冲突概率
- **已经静默出过半 corrupt 但没被察觉**（比如某次看到的 origin/main 是 iCloud
  给的陈旧 sha）—— 无法直接证伪

**这是运气，不是设计**。接下来写的 9.5 "接受现状的监控手段" 就是为了尽早
捕获变坏的迹象。

### 9.4 两套"跨机真源"同时工作的语义

当前 Factory 实际上有**两条跨机同步通路同时存在**：

```
  Mac A 的 Factory                                    Mac B 的 Factory
     │                                                      │
     ├─── iCloud File Provider (~/Documents) ──[并行]──────┤
     │    (文件系统级全量同步，包括 .git/，last-writer-wins)
     │                                                      │
     └─── git remote (GitHub origin) ────────[并行]────────┘
          (git-aware 结构化同步，显式 push/pull，支持冲突解决)
```

这两条通路对"两台 Mac 的 Factory 是否一致"都有发言权，且**语义可能矛盾**：
- iCloud 路径：只要两台 Mac 都在线，文件内容**准实时**同步
- git 路径：只有显式 `git push` / `git pull` 时才同步

当用户在 Mac A `git commit` 但**没 push**：
- git 视角：Mac B 的 `git log` 看不到那个 commit
- iCloud 视角：Mac B 的 `.git/objects/` 和 `.git/refs/` 被 iCloud 同步过去
  （一段时间后）→ Mac B 的 `git log` **也看得到那个 commit**

**后者这个"魔术同步"在小概率场景下非常有用**（省去手动 push/pull 麻烦），
但它不保证一致性：
- 两台 Mac 同时 commit 时 iCloud 随便挑一个
- 网络慢的时候一台看到的状态滞后任意长时间
- 脏写入（如 `.git/packed-refs` 不完整）会让 git 命令行为诡异

### 9.5 接受现状的监控手段（用户决策：不迁移）

既然决定**不把 Factory 搬出 iCloud**，就要主动监控"什么时候真出事"。
建议以下做法：

**每次 release.sh 前置**：
- [ ] `git fsck --full` 验证 repo 完整性，发现 dangling/invalid 就停
- [ ] `scan-conflicts` 扫整个 Factory 目录（含 .git）看有无冲突残骸
- [ ] `git fetch origin && git status -sb` 确认本机和 origin 对齐（没 ahead/behind
      surprise）

**每次"感觉两台 Mac 对不上"时**：
- [ ] 两台 Mac 都先等 2-3 分钟让 iCloud drain（`brctl status | grep pending`）
- [ ] 两边 `git fetch origin && git log --all --decorate --oneline` 对比
- [ ] 若 HEAD 不一致：是 `.git/` iCloud 同步拼接破坏了 refs，建议立刻切到
      feature branch + push + 在 GitHub 合并，绕开 iCloud 的 `.git/` 同步

**周期性"健康体检"（建议每周一次）**：
- [ ] 跑 `git gc --prune=now` 同时关闭 Codex Desktop 和其它 Mac，避免并发
- [ ] 扫 `.git/objects/pack/` 有没有奇怪 ` 2` 后缀的 pack 文件
- [ ] 对比两台 Mac 的 `.git/refs/remotes/origin/main` sha 是否一致（不一致说明
      iCloud 同步出过问题）

### 9.6 Commit 粒度建议（原 9.4 保留）

release.sh 的 workflow 是"archive + rsync + git commit"。如果一次 release
把**多个独立特性**混在一起 commit，回滚单个特性就很难。建议：

- **一个 release = 一个特性**。做完 A 就 release A，再做 B 再 release B。
- **Release label 要具体**。`add-session-integrity-audit` 比 `v2.1` 好。用户
  CLAUDE.md 也要求 label 要"具体描述本次 release 的原因"。
- **WIP 改动不要塞进 release.sh**。用普通 `git commit` 在 feature branch 上累积
  WIP，完整功能做完再 release。

### 9.7 遇到两台 Mac 不一致时的诊断流程

```bash
# 在"可疑那台" Mac 上跑：
cd <Factory path>

# 1. iCloud 对 .git/ 有没有当前 pending
brctl status 2>&1 | grep -A2 -B1 "Skill_Factory/\.git"

# 2. .git/ 有没有 iCloud 冲突残骸 (最早的 corruption 信号)
find .git -name "*.icloud" -o -iname "*conflict*" -o -name "* [0-9]*"

# 3. git 本身的完整性
git fsck --full

# 4. 本机和 origin 的关系
git fetch origin
git log --oneline --all --decorate -20
git log origin/main..HEAD --oneline   # 本机领先 origin 的 commit
git log HEAD..origin/main --oneline   # origin 领先本机的 commit
git status -sb

# 5. 两台机器看到的 origin/main sha 应该一致（如果不一致说明 iCloud 同步坏了 refs/remotes/origin/main）
git rev-parse origin/main
```

### 9.8 未来升级路径（备忘）

当前接受 iCloud 同步 `.git/` 的风险。若**将来决定迁移**（出现首次 corrupt
事件、或觉得不确定性太大），迁移路径：

1. 两台 Mac 都 `git push origin main` 到 GitHub，保证云端有最新
2. 在两台 Mac 上把 `~/Documents/Coding/PLAYGROUND/Skill_Factory` 移到
   `~/Repos/Skill_Factory`（或其它 iCloud 不管辖的位置）
3. 确认 iCloud 不再追同步（`brctl status` 里消失）
4. 后续跨机同步走 GitHub push/pull，不再依赖 iCloud 的"魔术同步"
5. 更新 FACTORY.md 和本 plan，删除 9.2-9.5 的接受现状内容

这条路径**今天不执行**，但本节保留以便将来需要时参考。
