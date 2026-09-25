# 2026-05-13 Codex 数据丢失事件复盘

> 这是一次真实 incident 的根因分析，记给将来 agent-sync-doctor（特别是 Codex 侧）大改时参考。

## 症状

用户在 Mac B (ParkerdeiMac-303) 上报告两个症状：

1. **Session `019dfd1c-1e58-7053-abe7-860bb302a1f5` 回退了**：对话一直持续到北京 5/9 16:xx，但 Codex app 打开后显示只到 5/9 13 点多。
2. **大量 plugin 消失**：Codex app 里 13 个 enable 的 plugin 全部显示"未安装"，用户记忆中应该有 27 个 plugin。

## 诊断证据

### Session 019dfd1c

| 副本位置 | 行数 | 最后 timestamp | 结尾事件 |
|---|---|---|---|
| iCloud live（Codex 读的） | 1424 | 2026-05-09T05:02:37Z = BJT 13:02 | `event_msg/token_count` 紧跟 `function_call_output` |
| Mac B pre-icloud 5/7 snapshot | 558 | 2026-05-06T15:48 | —— |
| Trash rollback 5/7 15:21 | 558 | 2026-05-06T15:48 | —— |

- 5/9 session 目录**空**，无新 session 文件生成
- 无 `.tmp` / `.part` / `.swp` 碎片
- 无 Codex crash report
- 无 iCloud `.icloud` 未下载占位符
- iCloud brctl 报告 caught-up
- 结尾事件形态（function_call_output → token_count 之后直接断掉）**不是自然结束**，像是进程被 kill 或 crash

**结论**：5/9 13:02 → 16:xx 这 ~3 小时没有任何副本存在。最可能是 Codex 进程 13:02:37 后崩了 / 被 kill，in-memory 的后续 turn 从未 flush 到 iCloud 文件。真正恢复只能靠 Time Machine / Backblaze 类本地备份。

### Plugin 消失

- **config.toml 当前**: 13 个 `[plugins."id@mp"] enabled = true`
- **pre-icloud 5/7 snapshot**: 同样 13 个（只和当前差一个 github ↔ warp 互换）
- **pre-yolo 5/8 backup**: 同样 13 个
- **无一份备份含 27 个 plugin**
- **但 `~/.codex/plugins/cache/`（= iCloud symlinked 目录）里有完整 27 个 plugin 源代码**，包括 openai-curated 13 个、openai-bundled 2 个、openai-primary-runtime 3 个、claude-code-warp 1 个、claude-plugins-official 8 个
- iCloud plugins cache 目录里发现大量 macOS 冲突副本：`superpowers 2` 至 `superpowers 12`、多个 `plugin-install-XXX` / `plugin-backup-XXX`，说明**多 Mac 同时写入这个目录造成了严重的 iCloud 冲突历史**

**最可能解释**：在过去某次（可能远早于 5/7）merge 中，config.toml 的 `[plugins.*]` 段从 27 条被静默缩减到 13 条。14 个 enable 条目被吞了但对应 source 保留在 cache。

### iCloud 端冲突化石

关键的 iCloud 文件 `config.toml.conflict-ParkerdeiMac-11-20260507-224331` 证明 5/7 22:43:31 那次 merge **真的撞上了 iCloud 冲突**，不是 clean merge。conflict file size 3746B，和 pre-icloud 5/7 snapshot 一致 —— 说明保存下来的是 Mac B 原版，而"胜出"的是另一个（iCloud 母版 / Mac A 推上的）版本。

## 恢复措施已执行

**Plugin**: 编辑 iCloud live config.toml，追加 15 个 `[plugins."id@mp"] enabled = true` 条目，使总数从 13 → 28（多的 1 个是原来就 enable 的 browser-use）。Codex tui log 5/13 08:28 已证实 Codex 会主动扫 `plugins/cache/openai-curated/`，不需要显式 `[marketplaces.openai-curated]` 声明就能识别。备份 `~/.codex/config.toml.bak.pre-plugin-restore-20260513-183955`（本地，不通过 iCloud，避免再触发同步冲突）。

**Session**: 未执行任何操作。建议用户查 Time Machine 看 5/9 16 点之后的 `rollout-*-019dfd1c*.jsonl`。

## 给"大改 Codex 同步"的设计输入

以下是这次事故暴露的具体失效模式，重写 agent-sync-doctor（或替换方案）时要**显式地**解决：

### 1. config.toml 的 `[plugins.*]` 段不能被纯 JSON/TOML 合并策略覆盖

表现：静默丢失 14 个 enable 条目。

要求：**plugin enable 条目必须是 "union by key" 合并**（只增不删，除非显式 user delete 动作），不能依赖"最新 mtime wins"。最好在 doctor 里实现一个 `MergePluginsUnion` 算子，单独处理这一个 section。

### 2. `~/.codex/plugins/` 不应该被 symlink 到 iCloud

观察：iCloud `plugins/cache/` 里充斥 `superpowers 2`/`3`/.../`12` 类 macOS 冲突副本，说明多 Mac 同时写入该目录常态性触发 iCloud 冲突。

要求：plugins 这种"大量随机二进制/随机命名 staging"目录**本质不适合 iCloud 的最后写者胜出语义**。应该：
- 要么完全本地化（不 sync），每 Mac 独立维护 cache，config.toml 作为"声明性列表"让每 Mac 自行补下载
- 要么改用 per-host 的 cache 子目录（`plugins/cache/<host-id>/...`），然后在 doctor 里做"以当前 host 视角解析"

### 3. Session JSONL append 丢失没有任何保护

这次 5/9 13:02 之后的 3 小时丢了，因为 Codex 进程崩溃时没有 flush。agent-sync-doctor 目前**完全不管 session JSONL 的 durability**，但这是用户最在意的数据。

要求考虑：
- 定期（比如每 turn 结束）由 doctor 做 `ln` 到本地 snapshot 目录
- 监听 Codex crash report / launchd exit status，crash 时立刻尝试从任何 in-memory log / temp dir 搶救

### 4. iCloud conflict file 不应被忽略

观察：`config.toml.conflict-ParkerdeiMac-11-20260507-224331` 躺在 iCloud 里但 doctor 从未告警。如果 doctor 曾看到这个 conflict file，本应该停下来让用户决策。

要求：每次 `check` / `leave` / `arrive`，都必须主动扫 iCloud 里 `*.conflict-*` / `* [0-9]` / `* copy*` 命名的文件，存在即阻塞。

### 5. 两台 Mac 的 hostname 漂移（`ParkerdeiMac-11` → `-200` → `-303`）

观察：同一个 Mac 因为 mDNS 冲突不停地被 bump 后缀，doctor state 里看起来像 4 台 Mac，实际是 2 台。这可能让 doctor 的"per-host state"逻辑 confused。

要求：用 IOPlatformUUID 或其他硬件 ID 代替 hostname 作为 `.doctor/state/*.json` 的 key。

## 附：本次事件时间线

- 5/7 22:10: Mac B 最后一次干净状态（pre-icloud snapshot）
- 5/7 22:43:31: 5/7 merge 期间触发 iCloud 冲突（ParkerdeiMac-11 版本被打 conflict 标签）
- 5/7 22:44: doctor merge 完成，config.toml 变成 13 plugin 版（带 warp、去 github）
- 5/8 15:53: Mac B (ParkerdeiMac-200) 又跑了一次 doctor
- 5/8 16:05: Mac A (MIdeMacBook-Pro-551) 跑了一次 doctor
- 5/9 13:02:37 BJT: session 019dfd1c 最后一条成功写入 iCloud；之后 3 小时内容未 flush
- 5/13 16:38: Mac B 今天连跑两次 doctor（间隔 1 秒），仅动 `.codex-global-state.json`，未触发本次事故
- 5/13 17:34: iCloud `pre-merge-20260513-173406.bak` 生成
- 5/13 18:40: 本次事故诊断 + plugin 手工恢复完成

## Stale data cleanup 候选（**未执行**，等决策）

- iCloud `plugins/cache/<mp>/<id> [0-9]+` 冲突副本（`superpowers 2`…`superpowers 12`、`warp 2`/`3`、`hyperframes 2` 等）
- iCloud `plugins/cache/claude-plugins-official/plugin-install-XXX/` 共 5 个未完成安装 staging
- iCloud `plugins/cache/claude-plugins-official/plugin-backup-XXX/` 共 3 个遗留 backup
