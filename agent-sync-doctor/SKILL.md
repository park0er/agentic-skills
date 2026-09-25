---
name: agent-sync-doctor
description: Use when handing off Claude Code or Codex state across multiple Macs via iCloud — leave / arrive / 切电脑 / 交接 / 离开电脑 / 到新电脑 / switch Macs scenarios. Also for repairing iCloud symlink drift, recovering Codex `state_5.sqlite` corruption, restoring Codex Desktop sidebar threads, merging `.codex-global-state.json` on first-time Mac B onboarding, fixing Claude Desktop session visibility, or syncing 3P configLibrary. Handles both products via `--products claude,codex` and supersedes the older claude-sync-doctor workflow.
---

# Agent Sync Doctor

统一的 AI 工具同步健康检查与交接助手。一次调用同时处理 **Claude 和 Codex** 的
symlink 检查、SQLite 快照/恢复、JSON 合并和 iCloud 状态验证。

## 使用方式

安装位置通常是 `~/.claude/skills/agent-sync-doctor/` 或
`~/.agents/skills/agent-sync-doctor/`。脚本路径按实际安装位置调整：

```bash
SCRIPT=~/.claude/skills/agent-sync-doctor/scripts/agent_sync_doctor.py

# 只读检查（推荐两个产品都检）
python3 $SCRIPT --products claude,codex check

# 离开当前电脑（交接前一步）
python3 $SCRIPT --products claude,codex leave --yes

# 到达新电脑（自动判断首次/后续接入）
python3 $SCRIPT --products claude,codex arrive --yes

# 单产品用 --products claude 或 --products codex
```

## 规则

- 默认 `--dry-run`；**`--yes` 才真正执行修改**。
- `leave` 时若检测到 Codex/Claude 进程仍在运行，默认报错不执行；加 `--force`
  允许修 symlink 但仍拒绝 SQLite snapshot（WAL 一致性要求）。
- Claude Desktop 1.6259+ 的 3P 主配置以 `Claude-3p/configLibrary/_meta.json`
  和 active `<appliedId>.json` 为准；`claude_desktop_config.json` 仅作为 legacy
  兼容项检查。
- Claude Desktop 可见性修复必须使用当前 `ownerAccountId` +
  `deploymentOrganizationUuid` 作为优先目标 group，并把 legacy default group
  只作为兼容/迁移目标。
- `arrive` 自动判断当前机是"首次接入"还是"后续交接"：
  - **首次**：执行完整 merge（jsonl + SQLite + JSON workspace-roots + symlink + restore）
  - **后续**：仅 restore SQLite/auth/plist + 验证 symlink
- 敏感文件（`auth.json`、plist）只打印 size + sha256 前缀，**永不打印内容**。
- 所有覆盖操作创建 `.pre-icloud-<timestamp>` 回滚点。
- SQLite merge 在 staging 副本上执行，atomic swap 前验证 `orphan=0` + `expected_total`
  精确匹配，失败则丢弃 staging，iCloud snapshot 不受影响。
- iCloud snapshot 的 `.pre-merge-<timestamp>.bak` 保留作为 Mac A 母版的
  byte-for-byte 可信回滚源。

## Handoff 工作流（切机标准流程）

### 离开 Mac A

```bash
python3 $SCRIPT --products claude,codex leave --yes
# 期待输出: AGENT_SYNC_READY (leave)
# 检查点: iCloud current pending = 0 & placeholder = 0 & dataless = 0
```

### 到达 Mac B

```bash
# 1. 等 iCloud 下载完成 —— 两种 "未下载" 都要为 0：
#    (a) 经典 .icloud placeholder（legacy）
find "$HOME/Library/Mobile Documents/com~apple~CloudDocs/ClaudeSync" -name '*.icloud' | wc -l
find "$HOME/Library/Mobile Documents/com~apple~CloudDocs/CodexSync" -name '*.icloud' | wc -l
#    (b) File Provider dataless（macOS 12+，占绝大多数情况）
#    由配套 skill icloud-materialization-doctor 检测
python3 ~/.agents/skills/icloud-materialization-doctor/scripts/icloud_materialization_doctor.py check

# 2. 执行 arrive（首次自动走完整 merge，后续自动仅 restore）
python3 $SCRIPT --products claude,codex arrive --yes
# 期待输出: AGENT_SYNC_READY (arrive)
# 注：arrive 会自动调用 icloud-materialization-doctor check；
# 如发现 dataless>0 会阻止 arrive 并打印修复命令：
#   python3 <script> fix --force-read
```

### 配套 skill：icloud-materialization-doctor

macOS 12+ 的 File Provider 把"未下载"语义从 `.icloud` 后缀迁到了**同名文件但
st_blocks == 0**，本 skill 的经典 `find -name '*.icloud'` 检查会漏判。`arrive`
/ `handoff` / `icloud-check` 会自动通过 subprocess 调用 icloud-materialization-doctor
获取 dataless 计数；如果配套 skill 未安装，agent-sync-doctor 会 **fail-open**
回退到老行为（仅 placeholder 计数），并在输出里提示安装。

### 节奏要求

- 不要同时在两台 Mac 上打开 Claude Desktop / Codex Desktop（串行使用约束）。
- 首次 Mac B 接入前，必须先在 Mac A 上完成 V3 流程的 01-02-05 初始化（见
  `Codex-Sync-Plan-V3.md`）。
- 日常交接不需要再走 V3 完整脚本流程，只需 Doctor 的 `leave` + `arrive`。

## 命令语义

### check

```bash
python3 $SCRIPT --products claude,codex check
```

只读。报告每个 product 的 entry 分类状态、orphan 数、iCloud placeholder 数、
Codex threads 计数、desktop visibility 状态。可加 `--json` 输出机器可读格式。

**v4 阶段 1 增强（2026-05-14 起）**：默认还会跑一份**数据完整性摘要**（session
integrity + iCloud conflicts），在常规输出最后几行显示 top 3 条 warning，其余提示
用 `session-integrity` / `scan-conflicts` 子命令查完整列表。

- `--no-integrity`：跳过这份摘要，回退到纯 topology 检查（跑得更快）。
- `--integrity-gap-minutes N`：自定义 session-integrity 阈值（默认 30 分钟，比独立
  子命令的 5 分钟更宽松，避免在默认输出里太多噪音）。

### leave

```bash
python3 $SCRIPT --products claude,codex leave --yes [--force] [--ignore-conflicts]
```

离开本机前：进程检测 → symlink repair（Claude 风格的 atomic relink） →
**Integrity pre-check**（v4 阶段 1+2） → Codex SQLite WAL checkpoint +
snapshot → auth/plist snapshot → iCloud drain 轮询 → HANDOFF_READY。

**Integrity pre-check 的行为**：在 "Current check" 之后、"Proposed repair"
之前插入一段，和 `check` 命令共享同一摘要逻辑（30min gap 阈值）。

- **phantom activity warnings**：informational，**不阻塞**。
- **iCloud conflict 残骸**（v4 阶段 2 升级）：**阻塞** HANDOFF_READY，除非
  加 `--ignore-conflicts`。动机是 2026-05-07 事件的根因：一个
  `config.toml.conflict-*` 文件静默吞掉 14 条 plugin enable 条目。再让
  conflict 残骸进入下一轮交接是在重复这个事故。
- 建议顺序：看到 BLOCKER 提示 → `scan-conflicts` 看详情 →
  `clean-conflicts --apply` 删掉 → 重新 `leave`。只有在你充分理解某些 conflict
  必须保留时才用 `--ignore-conflicts`。

**真正会阻塞 HANDOFF_READY 的硬门槛**：
- `problem entries > 0`（symlink drift、conflict 决策未定）
- `desktopVisibility.missingVisibleCount > 0`
- `icloud.ready != True`（含 placeholder / current-pending / trash-pending / File
  Provider dataless 任一 > 0）
- **iCloud conflict 残骸 > 0** （除非 `--ignore-conflicts`，v4 阶段 2 新增）

### arrive

```bash
python3 $SCRIPT --products claude,codex arrive --yes
```

到达新机：iCloud placeholder 检查 → File-Provider dataless 检查（若
`icloud-materialization-doctor` 已装）→ 首次检测（`~/.codex/*.pre-icloud-*`
标记）→ 首次则执行 09 JSON merge + 08 SQLite merge → 04 符号链接切换 →
06 SQLite restore → 最终 verify → **post-arrive 冲突扫描**（v4 阶段 2 新增）
→ AGENT_SYNC_READY。

**post-arrive 冲突扫描**：最后一步调 `scan-conflicts` 看 arrive 过程有没有触发
新的 iCloud 冲突（merge / restore 过程可能撞上另一台 Mac 并发写）。发现时
**不阻塞** `AGENT_SYNC_READY(arrive)`——因为本次 arrive 已经完成，数据已落地；
阻塞点放在**下次 leave**（leave 会查到这些 conflict 并 block，除非你先清理）。
意图：让你在下次 leave 前有机会 review，不是在 arrive 时就强拦。

## 旧命令兼容（从 claude-sync-doctor 迁移过来的工作流）

完整保留旧 `claude-sync-doctor` 的所有子命令，用 `--products <single>` 指定产品：

```bash
python3 $SCRIPT --products claude check               # 旧 check
python3 $SCRIPT --products claude deep-check          # 旧 deep-check（本地vs云端 tree diff）
python3 $SCRIPT --products claude repair --safe --apply   # 旧 repair
python3 $SCRIPT --products claude handoff --yes --force   # 旧 handoff
python3 $SCRIPT --products claude state               # 旧 state ledger
python3 $SCRIPT --products claude icloud-check        # 旧 brctl 状态
python3 $SCRIPT --products claude desktop-check       # 旧 Desktop 可见性
python3 $SCRIPT --products claude desktop-repair --apply
python3 $SCRIPT --products claude install-launchagent --apply --load
```

Codex 侧也支持同样的子命令集，仅 `desktop-check` / `desktop-repair` 返回
`available=false`（Codex 没有 ownerAccountId 视角的可见性过滤）。

## 数据完整性审计（v2.1 引入，v4 阶段 1 集成进 check/leave）

常规的 `check` 只看 symlink topology —— 看不到"state 和 jsonl 内容是否一致"、也
看不到"iCloud 冲突解决留下的残骸文件"。2026-05-13 的 Codex 事件复盘
（见 `ISSUES-2026-05-13-codex-data-loss.md`）暴露出这两类盲区，于是加了两个
独立的**只读**子命令专门审这两件事。不会动任何文件。

**2026-05-14 更新（v4 阶段 1）**：这两个子命令的摘要结果现在**默认**并入
`check` 和 `leave`（通过 `run_handoff` 的 "Integrity pre-check" 段）。`check`
下可用 `--no-integrity` 跳过；`leave` 下永远跑但只作为 informational warning
不阻塞。**独立子命令仍然保留**，用于"我看到摘要 warning 了，想看完整列表"
这种深入调查场景（完整列表 + 自定义阈值 + JSON 输出）。

### session-integrity

```bash
python3 $SCRIPT --products codex session-integrity
```

遍历 `state_5.threads`，对每个 thread 交叉核对 `updated_at_ms` 和对应 rollout
jsonl 最后一行的 `timestamp`，差超过阈值就报 **phantom activity** —— 即 state
以为 thread 更新到了 T，但 jsonl 只写到了 T - ΔT。这种错位有三种成因，都需要
人工判断：

1. **UI heartbeat 虚晃**：Codex Desktop 打开 / 关闭 / 刷新 thread 都会 bump
   `updated_at_ms`，不写 jsonl。最常见也最无害。
2. **Codex 崩溃时 in-memory 内容没 flush**：进程 crash / 被 kill 导致本该写入
   jsonl 的内容丢了。→ **真实数据丢失**。
3. **iCloud 同步把晚到的 jsonl 写入冲突掉了**：另一台 Mac 写了内容但上传失败
   或被 last-writer-wins 淘汰。→ 可能在别台 Mac 本地还有残件。

区分三者需要看 Codex Desktop Electron log 里的 `latestTurnStatus`（skill 本身
读不到这个）：`interrupted` 状态对应 (2) 或 (3)，正常 thread 且无挂起 turn
对应 (1)。

输出每条 warning 都带：

- **UUIDv7 created**：thread id 解出的真实创建时间（加密学意义上的时间戳，不可
  伪造）。辨识"thread 到底什么时候开的"。
- **state_5 upd**：state 里的最后更新。
- **jsonl last**：jsonl 文件的最后一条 timestamp。
- **gap (min)**：state 比 jsonl 晚多少分钟。
- **tokens_used**：该 thread 累计 token 数。`tokens_used = 0` 且 unparseable 的
  session 是空 session（UI 打开但从没发消息），自动降到排序末尾。

输出按严重度排序：phantom activity（content > 0 的）→ rollout 文件丢失 →
rollout_path 缺失 → unparseable 空 session。返回值 `0` = 无 warning，`1` = 有。

参数：
- `--gap-minutes N`：自定义阈值（默认 5 分钟）。
- `--include-archived`：包含已归档 thread（默认跳过）。
- `--limit N`：非 JSON 模式下最多打印 N 条（默认 20）。
- `--json`：机器可读输出。

### scan-conflicts

```bash
python3 $SCRIPT --products codex,claude scan-conflicts
```

递归扫描 iCloud root 里所有名字匹配冲突残留 pattern 的文件，每找到一个列一行：

- `*.conflict-<host>-<ts>`：doctor 自己的冲突命名（源自 claude-sync-doctor）。
- `* 2.ext` / `* 3.ext` ...：macOS iCloud 自动加数字后缀的冲突副本。
- `* copy.ext` / `* copy 2.ext`：Finder 风格复制残留。
- `*(conflicted copy)*`：Office 风格冲突标记。

这些文件 `check` 完全看不见，但每一个都是"两台 Mac 同时写同一路径、iCloud 保留
了败者"的物证。2026-05-13 事件里"plugin 从 27 缩水到 13"就是因为
`config.toml.conflict-ParkerdeiMac-11-20260507-224331` 从未被人注意到。

返回值 `0` = 干净，`1` = 有残留。

参数：
- `--limit N`：最多打印 N 条（默认 40）。
- `--json`：机器可读。

### clean-conflicts（v4 阶段 2 新增）

```bash
# 默认 dry-run，先看会删哪些
python3 $SCRIPT --products codex clean-conflicts

# 真删：
python3 $SCRIPT --products codex clean-conflicts --apply

# 限制范围到 iCloud root 下的子路径（例如只清 plugin cache）
python3 $SCRIPT --products codex clean-conflicts --apply --under dotcodex/plugins/cache
```

删除 `scan-conflicts` 能找到的冲突残骸。默认 **dry-run**（只打印 `would-remove`
的动作），`--apply` 才真删。设计意图是让你在实际删除前明确看到每一条，避免
把有价值的数据当 conflict 副本删掉。

**安全闸**（每个文件独立判断）：

1. **必须匹配已知冲突 pattern**（继承 scan-conflicts 的 pattern 集合）：
   `*.conflict-*`、`* N` 数字后缀、`* copy` 后缀、`(conflicted copy)` 标记。
2. **必须能推断出 canonical 版本**（例如 `foo 2.txt` 的 canonical 是 `foo.txt`）。
   推断不出的 pattern 会 `skip`，不删。
3. **canonical 必须在磁盘上真实存在**。不存在就 `skip`——这种情况意味着"这个
   conflict 副本可能是唯一的数据副本"，盲删会丢数据。
4. **单文件 unlink()，失败立刻报错**。一个文件失败不影响其它继续跑。

每条输出：
```
  [would-remove] (doctor-conflict) size=3746  <path>  canonical=config.toml
  [skip]         (macos-finder-copy) size=120  <path>
      reason: canonical 'README.txt' does not exist; refusing to delete possibly-unique copy
  [removed]      (macos-icloud-numbered) size=0  <path>  canonical=state_5.sqlite-wal
  [error]        (doctor-conflict) size=123  <path>  canonical=<...>
      error: [Errno 13] Permission denied
```

末尾 summary：`removed=N  would-remove=M  skipped=S  errors=E`。

参数：
- `--apply`：真删（默认是 dry-run）。
- `--under <prefix>`：限制扫描范围。路径可以是相对（iCloud root 下的子路径）
  或绝对。不加则扫整个 iCloud root。
- `--json`：机器可读。

**iCloud 恢复**：即使真的误删，iCloud 有 30 天 "Recently Deleted" 保留机制。
访问 iCloud.com → Drive → Recently Deleted，或 Finder 侧栏的"最近删除"，可恢复
最近 30 天内删除的任何 iCloud 文件。

## Codex plugin 跨机同步（v4.3，2026-05-14）

leave/arrive 现在自动同步 `~/.codex/config.toml` 里的 `[plugins.*]`（enable 列表）
和 `[marketplaces.*]`（marketplace 来源）两段。**不**同步 plugin 源代码
（`plugins/cache/`、`.tmp/*`）—— Codex Desktop 启动时自己 `git clone openai/plugins`
+ refresh cache 即可。

### 设计依据（基于 openai/codex 源码研究）

详见 `plans/2026-05-14-codex-plugin-architecture-research.md`：

- **`plugins/cache/<mp>/<plugin>/<version>/`** 是性能 cache，Codex 启动时自动重建
- **`config.toml [plugins.*]`** 是用户意图（enable 列表），唯一需要跨机共享的 state
- **`config.toml [marketplaces.*]`** 是 marketplace 来源（git URL / local path），需共享
- **`.tmp/plugins/`、`.tmp/marketplaces/`、`.tmp/bundled-marketplaces/`** 全部本机 cache，Codex
  启动时各自重建

### Leave 行为（自动）

`leave_extra` 阶段调 `codex_plugin_leave_sync`：
1. 从 `~/.codex/config.toml` 提取 `[plugins.*]` 和 `[marketplaces.*]` 段
2. 读 iCloud `snapshots/config-toml/_merged.toml`（如存在）
3. union-merge：`enabled` 字段 any-true wins；marketplace 字段 take-cloud
4. 写回 iCloud snapshot

snapshot 路径：`~/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/snapshots/config-toml/_merged.toml`

### Arrive 行为（自动）

`arrive_extra` 阶段调 `codex_plugin_arrive_sync`：
1. 读 iCloud `_merged.toml`（首次接入时若不存在则跳过）
2. 读本机 `~/.codex/config.toml`，extract `[plugins.*]` + `[marketplaces.*]`
3. union-merge cloud 与 local
4. 备份本机 config.toml 到 `config.toml.pre-arrive-<ts>.bak`
5. 用 surgical 文本编辑替换 `[plugins.*]` 和 `[marketplaces.*]` 两段（其它段保持原文不动）
6. **Sanity check**：扫所有 `source_type = "local"` 的 marketplace，验证 `source` 路径在本机存在；缺失的列 warning（不阻塞）

### 当 sanity check 报告 marketplace 路径缺失

最常见的两种情况：

- **`openai-bundled` 路径不存在**：启动 Codex Desktop，让它从 `Codex.app/Contents/Resources/plugins/` bootstrap 到 `~/.codex/.tmp/bundled-marketplaces/openai-bundled/`
- **`openai-primary-runtime` 路径不存在**：bootstrap 机制未完全确定（见 plan §7.6）。最简方案：启动 Codex Desktop 或运行 `codex` CLI

### plugins/ 目录的处理（迁移期）

`products.codex.json` 已从 entries 移除 `plugins` 条目；doctor v4.3 不再管理它。
但**老用户机器上 `~/.codex/plugins/` 可能还是 symlink → iCloud**。一次性迁移流程见
`plans/2026-05-14-codex-plugin-migration-plan.md` §3：cp iCloud 内容到本地 + rm
symlink + mv 上位。一次性迁移完成后，每台 Mac 的 plugins/ 是独立本地目录。

### Union merge 算法（简版）

- **`[plugins.<id>] enabled`**: any-true wins (true OR true→true; true OR false→true; false OR false→false)
- **`[plugins.<id>]` 其它字段**: cloud 覆盖 local
- **`[marketplaces.<name>]`**: 全字段 take-cloud（含 `source` —— 同用户名场景下两台 Mac 路径字符串本就一致）
- 两边任一独有的 entry: 完整保留

详见 `plans/2026-05-14-codex-plugin-migration-plan.md` §4.3。

### 不再做的事

doctor 永远不碰：

- `~/.codex/plugins/cache/<mp>/<plugin>/<version>/` （Codex 启动 `refresh_curated_plugin_cache` 自愈）
- `~/.codex/plugins/data/<plugin>-<mp>/`（运行时 hook 数据，per-Mac）
- `~/.codex/.tmp/plugins/`（Codex `sync_openai_plugins_repo` 启动时自动 git clone）
- `~/.codex/.tmp/marketplaces/<mp>/`（Codex `upgrade_configured_git_marketplaces` 自动 upgrade）
- `~/.codex/.tmp/bundled-marketplaces/openai-bundled/`（Codex Desktop 启动时从 app bundle 复制）
- `~/.codex/.tmp/app-server-remote-plugin-sync-v1`（startup 一次性 marker）

## 故障恢复

- 误修复 / 误删：每次 repair 的 backup 在 `<backupRoot>/<timestamp>/`（Claude 在
  `~/ClaudeSyncBackups/doctor/`，Codex 在 `~/CodexSyncBackups/doctor/`）。
- 合并失败：iCloud snapshot 的 `state_5.sqlite.pre-merge-<ts>.bak` 和
  `.codex-global-state.json.pre-merge-<ts>.bak` 即可一键回滚 iCloud 母版。
- 本机失败：`~/.codex/*.pre-icloud-<ts>` 可逐路径 `mv` 回原名。

## 相关方案文档

- `/Users/park0er/Documents/Coding/Foundations/Codex-Sync-Design/Codex-Sync-Plan-V3.md`
- `/Users/park0er/Documents/Coding/Foundations/Agent-Sync-Doctor/Sync-Doctor-Upgrade-Plan-V2.md`
- `/Users/park0er/Documents/Coding/Foundations/Codex-Sync-Design/MIGRATION-RESULT-MacA.md`
- `/Users/park0er/Documents/Coding/Foundations/Codex-Sync-Design/MIGRATION-RESULT-MacB.md`

## 环境变量（测试 / 调试用）

| 变量 | 用途 |
|---|---|
| `AGENT_SYNC_DOCTOR_ASSUME_RUNNING` | `1` 强制进程检测返回 running；`0` 返回 not running |
| `CODEX_HOME` | 覆盖 `~/.codex`（fake workspace 测试用） |
| `ICLOUD_ROOT` | 覆盖 iCloud CodexSync 根 |
| `PREFS_DIR` | 覆盖 `~/Library/Preferences` |
