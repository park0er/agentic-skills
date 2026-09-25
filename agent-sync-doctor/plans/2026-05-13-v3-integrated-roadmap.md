# Agent Sync Doctor v3 整体方案

**日期**：2026-05-13
**作者**：复盘 + 规划
**关联事件**：[ISSUES-2026-05-13-codex-data-loss.md](../ISSUES-2026-05-13-codex-data-loss.md)
**关联改动**：已落地 `session-integrity` + `scan-conflicts`（v2.1，见 `SKILL.md`）
**范围**：Plugin 丢失根因 + ISSUES.md 5 条需求 + 今日 session-integrity 经验，整合成 doctor 下一大版本（v3）的完整路线图

---

## 1. Executive Summary

2026-05-13 的 Codex 数据丢失事件暴露了 agent-sync-doctor 在 iCloud-backed
跨机同步场景下的 **4 类系统性盲区**：

| 盲区 | 今天的具体症状 | 根本原因 |
|---|---|---|
| A. State ↔ 数据一致性 | session 019dfd1c 的 state_5.updated_at 比 jsonl 内容晚 4h40min | doctor 只检查 symlink topology，不对比内容一致性 |
| B. iCloud 冲突残骸 | 5/7 的 `config.toml.conflict-*` 静默吞 14 条 plugin enable，从未告警 | doctor 不扫 `*.conflict-*` / `* N` / `* copy` 命名模式 |
| C. TOML section 合并语义 | `[plugins.*]` 被 last-writer-wins 合并，unique enable 条目丢失 | merge 策略是全文件覆盖而非 section-aware union |
| D. 机器身份漂移 | 同一 iMac 以 `-11`/`-200`/`-303` 三个 hostname 出现在 state 目录 | state 文件用 `hostname` 当 key，macOS mDNS 冲突会自动换名 |

**今天已经做完**：A、B 两类盲区加了只读审计工具（`session-integrity`、`scan-conflicts`）。
**未做**：C、D 两类，以及主动防御（把审计插进 leave/arrive 的前置检查）、
session jsonl 的 durability 增强、以及 plugin 存储架构的重新设计。

本 v3 方案把这些都理一遍，排了执行顺序，并点出我现在还不确定、需要进一步调研或让用户决策的开放问题。

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

**P2 — 根治（doctor v3 的 C、D 两项）**：见第 3 节。

### 2.3 不推荐的路径

- ❌ **不要**把 `.tmp/` 纳入 doctor 同步范围：会把每台 Mac 的 git 本地对象
  （`.git/objects/pack/*.pack`）卷进 iCloud 冲突，**重演** `plugins/cache/` 现在
  的状态。且 plugin 源码是可再生物，不是真源。
- ❌ **不要**继续 symlink `plugins/` 到 iCloud：这正是污染的根源。

---

## 3. ISSUES.md 5 条需求 → doctor v3 设计映射

### Req #1：`[plugins.*]` 必须 union-by-key 合并

**当前行为**：doctor 的 arrive 对 `.codex-global-state.json` 做 smart merge，但
`config.toml` 作为**整文件单元**处理（走 `LOCAL_FILE_DIFFERS_FROM_CLOUD` 的
"decision: local/cloud"），而 `[plugins.*]` 是 section 级语义。两者粒度不匹配。

**v3 提议**：
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

**v3 提议**：
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

**v3 提议（分层）**：
- **轻量层**：doctor 每次 `check` 时跑 `session-integrity` 作为常规输出的一部分，
  把 phantom activity > 30min 且 tokens>0 的 thread 列为 warning。**不阻塞** leave，
  只通知用户"有可疑 thread，你自己决定是否需要人工检查"。
- **中量层**：在 doctor 的 `check` / `leave` 输出加 **last-jsonl-ts per thread**
  字段，以便事后回查（成本低，大约每 thread 2 个 syscall）。
- **重量层（未定）**：真正的 durability 增强（比如每 N 秒 hard-link jsonl 到
  本地快照目录）需要 Codex 端 hook 或 macOS launchd watcher，超出 doctor 本身
  职责。**建议列为 TODO，不在 v3 范围**。等有第二次真实数据丢失 incident
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

**v3 额外提议**：
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

**v3 提议**：
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

---

## 4. v3 Roadmap（建议执行顺序）

```
阶段 0（已完成，2026-05-13）
  ✅ session-integrity（Req A 的只读审计）
  ✅ scan-conflicts（Req #4 的只读审计）
  ✅ Factory 结构恢复
  ✅ ISSUES.md 复盘文档

阶段 1（小改，1 次 release，优先级高）
  □ 把 session-integrity 并入默认 check 输出
  □ 把 scan-conflicts 并入默认 check 输出
  □ leave 前置：有 phantom activity (tokens>0, gap>30min) 或 conflict 残骸 → warn 但不阻塞
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

4. **machine_id 迁移期的双命名兼容**：如果 Mac A 升级到 v3，Mac B 还是 v2，Mac A
   写 UUID.json 而 Mac B 读不懂；反过来 Mac B 写 hostname.local.json Mac A 读旧
   的。需要 grace period 里同时读写两种命名，或强制两台机器同时升级。→ **决定
   升级策略前暂不动**。

5. **Time Machine / Backblaze 作为 fallback durability**：用户是否已有外部备份
   方案？如果 session jsonl 丢失是灾难场景，外部备份应该是第一防线，doctor
   只是监控层。→ **需问用户是否已有**。

---

## 6. 本次 incident 给 skill 设计的普遍教训

（记这些是为了**下次**类似问题出现时，agent 能更快定位）

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

---

## 7. 本方案外的相关文档

- `ISSUES-2026-05-13-codex-data-loss.md`：当天事件现场复盘
- `SKILL.md` 的"数据完整性审计"章节：阶段 0 已落地命令的文档
- `~/Documents/Coding/Foundations/Codex-Sync-Design/Codex-Sync-Plan-V3.md`：
  更早的 Codex sync 大设计（预存在，内容与本方案有重叠但颗粒度不同）

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

方案写完，等你 review。
