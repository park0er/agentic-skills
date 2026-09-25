# Codex Plugin 跨机同步：一次性迁移 + 长期 doctor 方案

> 日期：2026-05-14
> 关联文档：
> - 上游研究：[2026-05-14-codex-plugin-architecture-research.md](2026-05-14-codex-plugin-architecture-research.md)
> - 总体路线：[2026-05-13-v4-integrated-roadmap.md](2026-05-13-v4-integrated-roadmap.md)（本方案**取代**原 v4 阶段 3 的 plugin 部分）
> - 历史事件：[../ISSUES-2026-05-13-codex-data-loss.md](../ISSUES-2026-05-13-codex-data-loss.md)
> 范围：iMac (ParkerdeiMac-303 / IOPlatformUUID `3AB03F37-F32F-521C-9D18-94B2D5FDB63A`) 和 MBP (MIdeMacBook-Pro-551) 两台 Mac

---

## 1. Executive Summary

研究 openai/codex 源码后，**plugin 跨机同步的正确架构跟此前 v4 plan 的设计相反**：不应该让 doctor 管 plugin 内容，而应该让 doctor **只管同步 `config.toml`**，把所有 plugin 实体的重建工作交还给 Codex 自己（它启动时本来就会跑 `refresh_curated_plugin_cache` 和 `refresh_non_curated_plugin_cache`）。

三个核心结论：

1. **`config.toml` 的 `[plugins.*]` 和 `[marketplaces.*]` 是**唯一**需要跨机同步的 plugin 状态**。enabled 列表、marketplace 来源 URL、git ref —— 这些代表用户意图，必须共享。
2. **当两台 Mac 用户名相同（本案例 `park0er`），`source_type = "local"` 的 marketplace 的 source 字段跨机直接安全**——字符串值在两台机器上都解析到本机各自的真实目录。原 v4 plan 担忧的"绝对路径毒丸"在同用户名情境下**不存在**。真正需要担心的是 **target 目录在另一台 Mac 是否被 bootstrap**（这是个本机 bootstrap 问题，不是 sync 问题）。
3. **`~/.codex/plugins/cache/`、`~/.codex/.tmp/*` 全部是本机 cache**，每台 Mac 启动 Codex Desktop 时自动重建。doctor 不要 sync、不要 symlink、不要预填。

### 1.1 Plugin 自愈源 vs 跨机同步矩阵（实测 iMac 数据，用户名 `park0er` 两台一致）

每个 marketplace 的"自愈源"（另一台 Mac 启动 Codex 时如何重建）和"跨机干净度"：

| Marketplace | enable 数 | source_type | 自愈源 | source 字段跨机 |
|---|---|---|---|---|
| **openai-curated** | 13 | (hardcoded) | 启动时 `git clone https://github.com/openai/plugins.git` | ✅ 不在 user config，无需同步 |
| **claude-plugins-official** | 8 | git | `https://github.com/anthropics/claude-plugins-official.git` | ✅ 公开 URL |
| **claude-code-warp** | 1 | git | `https://github.com/warpdotdev/claude-code-warp.git` | ✅ 公开 URL |
| **claude-hud** | 0 | git | `https://github.com/jarrodwatts/claude-hud.git` | ✅ 公开 URL |
| **openai-bundled** | 3 | **local** | Codex Desktop 从 `Codex.app/Contents/Resources/plugins/` 复制到 `~/.codex/.tmp/bundled-marketplaces/openai-bundled/` | ✅ **同用户名安全**；source 字符串两台 Mac 完全相同；前提是另一台 Mac 启动过 Codex Desktop 让它 bootstrap |
| **openai-primary-runtime** | 3 | **local** | `~/.cache/codex-runtimes/codex-primary-runtime/plugins/openai-primary-runtime`（bootstrap 机制待 P0 调查） | ✅ **同用户名安全**；同上前提 + bootstrap 机制需验证 |

**全部 28 enabled plugin 都能自愈**——前提是 config.toml 的 `[plugins.*]` 准确传到另一台 Mac，且每台 Mac 都已运行过 Codex Desktop 完成本机 bootstrap。

### 1.2 跨用户名场景的隐患（防御性记录）

如果将来情境变化（例如换 Mac 时用了新用户名、协作给同事），上述 `source_type = "local"` 的 marketplace **会重新变成毒丸**。doctor 实现 union merge 时不需要特殊处理 source 字段（只读字符串透传），但**应该在 arrive 时加 sanity check**：

- 检查所有 `source_type = "local"` 的 marketplace，验证 `source` 路径在本机存在
- 不存在时打印 warning，提示用户启动 Codex Desktop 让它 bootstrap，或手工创建

这个 check 在同用户名场景下永远通过，但能在跨用户名场景下提前发现问题，零成本加防御性。

迁移分两层：

- **A. 一次性迁移**（两台 Mac 各做一次）：把当前已经 symlink 到 iCloud 的 `plugins/` 解开本地化，清掉 iCloud 端 plugins/cache/ 的 30+ 冲突副本，把两台 Mac 的 `[plugins.*]` 联合到一致状态，并修复每台机器的 `[marketplaces.openai-bundled].source` 路径。
- **B. 长期 doctor 化**：v4 阶段 3 重新定位为"only sync config.toml + 让 Codex 自愈"。doctor 不再处理 plugins/ 目录，只 union-merge config.toml 的两个段，且**显式过滤 openai-bundled**。

---

## 2. 当前两台 Mac 的状态盘点

### 2.1 已知事实（基于今天的调查）

| 维度 | iMac (ParkerdeiMac-303) | MBP (MIdeMacBook-Pro-551) |
|---|---|---|
| `~/.codex/plugins/` | ✅ symlink → iCloud `CodexSync/dotcodex/plugins/`（坏的设计，待解开）| 假定同上（待 MBP 确认）|
| `~/.codex/.tmp/plugins/plugins/` | ✅ 完整 git clone（123 个 plugin）| 假定有（每台 Mac 启动时自建）|
| `~/.codex/.tmp/marketplaces/` | ✅ 76MB（claude-code-warp、claude-hud、claude-plugins-official）| 假定有 |
| `~/.codex/.tmp/bundled-marketplaces/` | ✅ 93MB | 假定有 |
| `~/.codex/config.toml` 的 `[plugins.*]` 数量 | 28 条（用户今天从 13 手工恢复）| 待 MBP 实测 |
| `~/.codex/config.toml` 是否同步到 iCloud | 是 symlink（在 doctor entries 里） | 同上 |
| `[marketplaces.openai-bundled].source` 当前值 | 待 grep 实测 | 待 MBP 实测 |
| iCloud `plugins/cache/` 冲突副本 | 之前 30+，今天意外删了 9 条，还剩 ~21 条 | 待 MBP 实测 |
| Codex Desktop 是否在跑 | 待时段确认 | 待时段确认 |

### 2.2 已知问题清单

1. **iCloud `plugins/cache/` 里 30+ 冲突副本**（如 `superpowers 6/7/8/9/12`、`warp 2/3`、`hyperframes 2`）
2. **iCloud `plugins/cache/claude-plugins-official/` 里 5 个 `plugin-install-*` staging + 3 个 `plugin-backup-*` 目录**（Codex 期望的 staging 是临时 `tempfile::TempDir`，crash 时未清理留下来的）
3. **`~/.codex/plugins/` symlink 让 plugins/cache/ 上 iCloud**，违反 Codex 设计原则（plugins/cache/ 是性能 cache、应本地）
4. **`[marketplaces.openai-bundled].source` 跨机不兼容**（如果两台 Mac 的 username 不同则路径不同）
5. **`.codex-global-state.json.pre-bluegold-*` / `pre-clone-*` / `pre-pin-*` / `pre-merge-*` 历史 .bak 文件**（doctor 自己早期版本的产物，已无用，可清理）

---

## 3. 一次性迁移（A 方案）

> **目标**：把两台 Mac 从"plugins/ symlink to iCloud + 互相分叉的 [plugins.*]"恢复到"plugins/ 本地 + config.toml 一致"的健康状态。
> **执行频率**：每台 Mac 只跑一次。完成后切换到长期 B 方案。
> **预计耗时**：每台 Mac 30~60 分钟（含 Codex Desktop 重启验证）。

### 3.1 通用前置（每台 Mac）

```
[ ] 退出 Codex Desktop（Cmd+Q），用 pgrep 确认进程归零
[ ] 退出 Claude Desktop（避免它的 doctor 干扰）
[ ] 备份当前 ~/.codex/config.toml 到 ~/.codex/config.toml.pre-migration-20260514.bak
[ ] 备份当前 ~/.codex/.codex-global-state.json 到 .pre-migration-20260514.bak
[ ] 等 iCloud drain：brctl status | grep -i pending 应为 0
[ ] 跑 doctor scan-conflicts，存当前 conflict 清单做基线
```

### 3.2 双 Mac 协调（必须先做）

```
[ ] 选定一台"主 Mac" 做 plugin enable 列表的真源
    （建议：当前 28 plugin 都 enable 的 iMac-303）
[ ] 主 Mac 上 grep "^\[plugins\." config.toml > /tmp/plugins-truth.txt
    把这个清单作为两台 Mac 的目标状态
[ ] 在另一台（次 Mac）上同样 grep 自己的 [plugins.*]，做 diff
    标出"主 Mac 有但次 Mac 没有"的 plugin —— 这些后面要在次 Mac 重新 install
```

### 3.3 主 Mac (iMac-303) 步骤

```
A1. [本地化 plugins/——从 iCloud 复制现有内容到本地]
    cd ~/.codex
    
    # 当前 plugins 是 symlink → iCloud。我们要做的是：
    # (a) 解析 symlink 指向的 iCloud 真实位置
    # (b) 完整复制 iCloud 现有内容到本地（让本地立即拥有完整状态，无需 Codex 重建）
    # (c) 删 symlink（只删本地这条，不动 iCloud 内容）
    # (d) 把本地副本移到原 plugins 位置
    # 这样的好处：本地立刻可用、Codex 启动不需要 git clone 13 个 plugin、避免重建失败风险
    LIVE_PLUGINS=$(readlink -f plugins)
    test -d "$LIVE_PLUGINS" || { echo "FAIL: symlink target missing"; exit 1; }
    
    # 完整复制（保留属性、xattr、隐藏文件）
    cp -Rp "$LIVE_PLUGINS"/. plugins.localized-20260514/
    
    # 校验完整性
    ls plugins.localized-20260514/cache/  # 应有 5 个 marketplace 子目录
    diff -rq "$LIVE_PLUGINS" plugins.localized-20260514 | head -10  # 期望空
    
    # 解开 symlink（只删 link 本身，不影响 iCloud 内容）
    rm plugins
    
    # 让本地副本上位
    mv plugins.localized-20260514 plugins
    ls -la plugins  # 应显示 directory（drwx），不再是 lrwx
    
A2. [验证 plugins 立即可用]
    ls plugins/cache/  # 5 个 marketplace 子目录
    ls plugins/cache/claude-plugins-official/superpowers/  # 抽样
    ls plugins/cache/openai-curated/  # 13 个 enabled plugin 应都在
    
A3. [清理 plugins/cache/ 内的冲突副本（本地版本）]
    # iCloud 同步留下的 'superpowers 2/3/.../12'、'warp 2/3'、'hyperframes 2' 等
    find plugins -name "* [0-9]*" -type d
    # 列表给 user 确认后批量 rm -rf
    # 同样清掉 plugin-install-* / plugin-backup-* 历史 staging 残留
    find plugins/cache -name "plugin-install-*" -o -name "plugin-backup-*"
    
    # 注意：这一步只清本地副本里的冲突；iCloud 那边的副本暂时保留（见 A4）
    
A4. [iCloud plugins/ 暂保留，**不删**]
    # 决策：用户选择保守策略，保留 iCloud 副本作为冷备份。
    # 此刻 iCloud CodexSync/dotcodex/plugins/ 状态：
    #   - 不再被任何 Mac 通过 symlink active 使用
    #   - 内容相当于 iMac 在解开 symlink 那一刻的"冻结快照"
    #   - 之后 Codex Desktop 写本地 plugins/ 时不会触达 iCloud
    # 长期：等观察一周确认本地 plugin 跑得稳，可以安全 rm -rf 这个 iCloud 目录
    #       清理时机由用户决定，迁移流程不强制
    
    echo "iCloud plugins/ 保留为冷备份（不动）"
    ls -la "$HOME/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/plugins" 2>&1 | head -3
    
A5. [清 doctor 的 manifest]
    # 改 references/products.codex.json，从 entries 移除 'plugins' 这条
    # 见 §3.7 详细 patch
    
A6. [清 .codex-global-state.json 老 .bak]
    cd ~/.codex
    rm -f .codex-global-state.json.pre-bluegold-*.bak
    rm -f .codex-global-state.json.pre-clone-*.bak
    rm -f .codex-global-state.json.pre-pin-*.bak
    rm -f .codex-global-state.json.pre-merge-*.bak
    # 同步删 iCloud 端的对应文件
    
A7. [验证所有 source_type=local 的 marketplace 的 target 目录存在]
    # 同用户名场景下（两台 Mac 都是 park0er），source 字段是字符串透传 OK；
    # 但要确认这些字符串指向的目录在本机真的存在。
    # 列出所有 local marketplace：
    awk '/^\[marketplaces\./ {name=$0} /source_type = "local"/ {print name}' ~/.codex/config.toml
    
    # 验证每条对应的本地目录
    for src in $(grep -A1 'source_type = "local"' ~/.codex/config.toml | grep '^source =' | sed 's/source = "//' | sed 's/"$//'); do
        if [ -d "$src" ]; then
            echo "  ✓ $src"
        else
            echo "  ✗✗ MISSING: $src"
        fi
    done
    
    # 任何 MISSING 都需要先解决再继续：
    # - openai-bundled 目录缺失 → 启动 Codex Desktop 让它从 Codex.app/Contents/Resources/plugins/ 重建
    # - openai-primary-runtime 目录缺失 → bootstrap 机制需 P0 调查（见 §7.6）
    
A8. [重启 Codex Desktop 验证]
    open /Applications/Codex.app
    # 等 5-10 秒让 startup_sync 完成
    # 看 plugins/cache/ 是否被自动重建（refresh_curated_plugin_cache 应该跑）
    # 看 plugin sidebar 里所有 28 个 plugin 是否都正常加载
    # 任何缺失就在 Codex UI 里点 Install 一次
    
A9. [验证 doctor 不再 flag 'plugins' entry]
    python3 ~/.claude/skills/agent-sync-doctor/scripts/agent_sync_doctor.py \
      --products codex check
    # 不应再有 'plugins' 这一行
```

### 3.4 次 Mac (MBP) 步骤

```
B1. [拉最新 iCloud 同步]
    # 等待 iCloud drain，确保 dotcodex 的 config.toml 已经是 iMac 那侧的最新
    brctl status | grep pending
    
    # 注意：iMac 完成 A1-A2 后，iCloud plugins/ 不再被 active 使用，但内容还在。
    # MBP 此时 plugins symlink 仍然指向这个 iCloud 目录，跟 iMac 看到的一样。
    # MBP 接下来的 B2 步从这个 iCloud 副本本地化即可——不需要从网络重新拉 plugin。
    
B2. [本地化 plugins/]（同 A1：cp 到本地 + rm symlink + mv 上位）
B3. [验证内容]（同 A2）
B4. [清理冲突副本]（同 A3）
B5. [iCloud plugins/ 保留](同 A4)
    # iMac 已经决定保留 iCloud 副本作冷备份。MBP 这边也不动它。
    # 现在两台 Mac 都有各自的本地 plugins/，iCloud 端是冻结的备份。
B6. [跳过 doctor manifest 改] —— 等 doctor v4.3 发布后通过 release 应用
B7. [清老 .bak]（同 A6）
B8. [验证 MBP 上 source_type=local marketplace 的目录都已 bootstrap]
    # 同用户名场景下 source 字符串和 iMac 一样有效，但 MBP 必须本地有这些目录。
    # 同 A7 的验证脚本：
    for src in $(grep -A1 'source_type = "local"' ~/.codex/config.toml | grep '^source =' | sed 's/source = "//' | sed 's/"$//'); do
        if [ -d "$src" ]; then
            echo "  ✓ $src"
        else
            echo "  ✗✗ MISSING: $src — 必须先 bootstrap 再继续"
        fi
    done
    
    # 修复手段（按 marketplace 分别处理）：
    # - openai-bundled 缺失 → 启动 MBP 的 Codex Desktop，让它从 Codex.app/Contents/Resources/plugins/ 重建
    # - openai-primary-runtime 缺失 → 本机机制待查；最简方案：MBP 上跑一次 `codex` CLI 看会不会自动拉，
    #   或安装最新 Codex Desktop 让它在启动时初始化 codex-runtimes 目录
    
B9. [对齐 [plugins.*] 列表]
    # 如果次 Mac 缺哪些 plugin，在 Codex UI 里逐个 Install
    # 或者，更激进：直接把 iMac 的 [plugins.*] 段（28 条）整段复制过来
    # 然后启动 Codex Desktop 让 refresh_non_curated_plugin_cache 自动 install 缺的
    
B10. [重启 Codex Desktop 验证]（同 A8）
B11. [doctor check 验证]（同 A9）
```

### 3.5 双 Mac 一致性验证

```
[ ] 两台 Mac 的 grep "^\[plugins\." config.toml 计数应一致
[ ] 两台 Mac 都能在 Codex UI sidebar 看到所有 enabled plugin
[ ] doctor scan-conflicts 在两台 Mac 都返回 0 个 (snapshots/ 里 6 条历史 conflict 可在 §3.6 单独清)
[ ] doctor session-integrity 不再列出 plugin 相关的 phantom activity
[ ] doctor check 不再 flag plugins entry 为 problem
```

### 3.6 残留 conflict（单独清）

iCloud `CodexSync/snapshots/state_5/` 和 `snapshots/preferences/` 里有 6 条历史 macos-icloud-numbered conflict（state_5 2.sqlite、com.openai.codex 2.plist 等）。这些是 doctor snapshot 操作的产物，**和 plugin 无关**。

```
python3 ~/.claude/skills/agent-sync-doctor/scripts/agent_sync_doctor.py \
  --products codex clean-conflicts --apply --under snapshots
```

执行后 doctor `scan-conflicts` 应返回 0。

### 3.7 doctor manifest patch (`references/products.codex.json`)

把 `plugins` entry 从 `entries` 数组里移除：

```diff
 {
   "entries": [
     ...
-    {
-      "name": "plugins",
-      "type": "directory",
-      "local": "~/.codex/plugins",
-      "cloud": "dotcodex/plugins"
-    },
     ...
   ]
 }
```

这个 patch 配合 v4.3 doctor release 应用。**注意**：用户已有的 `plugins` symlink 不会被自动解开，需要在 §3.3 / §3.4 的 A1/B2 步手工处理。这个手工步骤就是"一次性迁移"的全部价值。

---

## 4. 长期 doctor 化（B 方案）

> **目标**：迁移完成后，未来切机靠 doctor 自动化处理 config.toml，再也不用手工同步 plugin。
> **触发时机**：每次 leave / arrive。
> **不做的事**：永远不动 `plugins/`、`plugins.cache/`、`.tmp/*`、`plugins/data/` —— 让 Codex 启动时自愈。

### 4.1 doctor leave 时新增的 plugin 处理

伪代码：

```python
def codex_leave_plugin_handling(doctor):
    # 1. 读本机 config.toml 的 [plugins.*] 和 [marketplaces.*] 段
    local_config = read_toml(~/.codex/config.toml)
    
    # 2. 提取要共享的部分（过滤 openai-bundled 的 source 字段）
    shareable = extract_shareable_plugin_config(local_config)
    # shareable['plugins'] = 全部 [plugins.*] 段（无过滤）
    # shareable['marketplaces'] = [marketplaces.*]，但 openai-bundled 仅保留
    #     last_revision/last_updated，去掉 source/source_type 字段
    
    # 3. 读 iCloud snapshot 里的 last-merged 版本
    cloud_snap = read_toml(iCloud/CodexSync/snapshots/config-toml/_merged.toml)
    
    # 4. union merge 本机 vs cloud
    merged = union_merge_plugin_config(local=shareable, cloud=cloud_snap)
    
    # 5. 写回 iCloud snapshot
    write_toml(iCloud/CodexSync/snapshots/config-toml/_merged.toml, merged)
    
    # 6. 同时落一份 per-host snapshot（用于审计）
    write_toml(iCloud/CodexSync/snapshots/config-toml/<machine_id>-<ts>.toml, shareable)
```

### 4.2 doctor arrive 时新增的 plugin 处理

```python
def codex_arrive_plugin_handling(doctor):
    # 1. 读 iCloud 的 _merged 版本（如果不存在，跳过 = 首次 arrive）
    cloud_snap = read_toml(iCloud/.../snapshots/config-toml/_merged.toml)
    if not cloud_snap:
        log("first-time arrive: no merged plugin config in iCloud, skipping")
        return
    
    # 2. 读本机 config.toml
    local_config = read_toml(~/.codex/config.toml)
    
    # 3. union merge 本机 vs cloud_snap，本机的 openai-bundled.source 保留
    merged = union_merge_plugin_config(local=local_config, cloud=cloud_snap,
                                        preserve_local_keys=['marketplaces.openai-bundled.source',
                                                              'marketplaces.openai-bundled.source_type'])
    
    # 4. 备份本机 config.toml
    cp ~/.codex/config.toml ~/.codex/config.toml.pre-arrive-<ts>.bak
    
    # 5. 写回本机 config.toml
    write_toml(~/.codex/config.toml, merged)
    
    # 6. 不动 plugins/cache/、不动 .tmp/*
    # 让 Codex 在下一次启动时自己 refresh_curated_plugin_cache + refresh_non_curated_plugin_cache
    log("plugin config merged into ~/.codex/config.toml. Restart Codex Desktop to materialize cache.")
```

### 4.3 union_merge_plugin_config 算法规格

输入：两份 TOML 表（local, cloud）。输出：合并后的 TOML 表。

规则：

1. **`[plugins."<id>"]` 段**：以 plugin id 为 key 做 union。同 id 时按以下子规则：
   - `enabled` 字段：**any-true wins**（true OR true → true; true OR false → true; false OR false → false）。理由：用户可能在某台 Mac 关掉了某个 plugin，但 v4 阶段 3 保守起见以"恢复 enable"为默认 —— 关掉是显式动作要更高优先级，留待后续 v4.4 加 `disabled_at_<ts>` 字段细化。
   - `mcp_servers.*`：递归 union。同字段冲突时 take-newer（按 mtime 没法判断这台和那台谁 newer，只能就近取 cloud）。
   - 不在 schema 里的字段：**保留两边**（用 `[plugins.<id>.local]` 和 `[plugins.<id>.cloud]` 双副本？还是 take-cloud？）—— **决策推迟，先 take-cloud**。
2. **`[marketplaces."<name>"]` 段**：以 marketplace name 为 key 做 union。同名时：
   - **统一规则**：所有字段 take-cloud（包括 source / source_type）。同用户名场景下，local source 字符串两台 Mac 解析到等价的本地路径。
   - 单纯字段 take-newer（如 last_revision、last_updated）按 last_updated timestamp 比较——time-aware merge。
   - **新 marketplace（cloud 有但本机没有）**：完整 take-cloud。
   - **arrive 后置 sanity check**：merge 完后扫所有 `source_type = "local"` 的 marketplace，验证 source 路径在本机存在；不存在的列入 warning，提示用户 bootstrap（启动 Codex Desktop 自动重建，或手工创建）。这个 check 在同用户名 + 两台 Mac 都启动过 Codex Desktop 的场景下永远通过；不通过时是真的 bootstrap 缺失，需要人工处理。

> **设计决定**：原方案设计了"local marketplace 的 source 字段必须 per-Mac 保留"特殊规则。重新审视后**简化为"全部 take-cloud + 后置 sanity check"**。理由：(a) 同用户名场景下两边路径字符串本来就一样，特殊规则是 no-op；(b) 异用户名场景下，路径不兼容会被 sanity check 立刻发现，用户能针对性处理（改一行 source 字段或 bootstrap 目录）；(c) 简化版逻辑代码量减半，更容易测试和审计。
3. **其它顶层段**（`[history]`、`[shell]` 等）：**不动**，保持本机原样。

### 4.4 doctor manifest 变化

`references/products.codex.json` 的 entries 数组：

```diff
- 移除：plugins 条目（plugins/ 不再 symlink）
+ 新增：snapshots/config-toml/ 条目（doctor leave 写入这里的 _merged.toml，arrive 读取）
+ 新增：plugins/.marketplace-plugin-source-staging/ 标记为"orphan-acceptable"
        （Codex crash 后留下的 staging 目录，doctor 应当忽略）
```

### 4.5 不再管理的事项

doctor 永远不碰这些路径，每台 Mac 启动 Codex Desktop 时自愈：

| 路径 | Codex 自愈机制 |
|---|---|
| `~/.codex/.tmp/plugins/` | startup `sync_openai_plugins_repo` |
| `~/.codex/.tmp/plugins.sha` | 同上 |
| `~/.codex/.tmp/marketplaces/` | startup `upgrade_configured_git_marketplaces` |
| `~/.codex/.tmp/bundled-marketplaces/` | Codex Desktop（Electron 端）启动时从 app bundle 复制 |
| `~/.codex/.tmp/app-server-remote-plugin-sync-v1` | startup `start_startup_remote_plugin_sync_once` |
| `~/.codex/plugins/cache/` | startup `refresh_curated_plugin_cache` + `refresh_non_curated_plugin_cache` |
| `~/.codex/plugins/data/` | hook 运行时 |
| `~/.codex/plugins/.marketplace-plugin-source-staging/` | Codex install 流程的 tempdir |
| `~/.codex/plugins/.remote-plugin-install-staging/` | 同上 |

---

## 5. 风险与回滚

### 5.1 一次性迁移阶段的风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 解 plugin symlink 后 Codex 找不到某些 plugin | 中 | plugin 临时不可用，重启 Codex Desktop 可自愈 | A1 步用 `cp -R` 保留所有内容；最坏情况 Codex 重新 install 一遍 |
| 删 iCloud `plugins/cache/` 后另一台 Mac 启动崩溃 | 低 | 另一台 Mac 启动时 plugin 加载失败 | 另一台 Mac 启动后 Codex 会自动 refresh cache；用户被迫等几分钟 |
| 修 `[marketplaces.openai-bundled].source` 改错 | 低 | bundled marketplace 加载失败，built-in plugin（computer-use 等）不可用 | 改前备份 config.toml；改后 `ls $REAL_PATH/marketplace.json` 验证 |
| 两台 Mac config.toml 同时写 | 极低 | 后写者覆盖前者 | 严格按 §3.2 顺序操作；先做主 Mac 再做次 Mac |

### 5.2 回滚路径

每个步骤都有备份：

- `~/.codex/config.toml.pre-migration-20260514.bak` ← A1 / B2 之前
- `~/.codex/.codex-global-state.json.pre-migration-20260514.bak` ← 同
- `~/.codex/plugins.localized-20260514` ← A1 步把原 symlink 内容备份的目录（迁移成功后可以 rm -rf）
- iCloud `CodexSync/dotcodex/plugins/.pre-migration-20260514/` ← A4 删之前可以先 mv 到这里做最后一道保险

如果整个迁移失败要 rollback：
```bash
cd ~/.codex
mv config.toml config.toml.failed-migration
mv config.toml.pre-migration-20260514.bak config.toml
# 把 plugins symlink 重新建立（如果删过）
ln -s "$HOME/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/plugins" plugins
# 把 iCloud 备份恢复
mv "$HOME/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/plugins.pre-migration-20260514" \
   "$HOME/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/plugins"
# 重启 Codex Desktop
```

### 5.3 长期 doctor 化阶段的风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| union merge 把不该合的 mcp_servers 字段合了 | 中 | 某个 plugin 的 MCP server 配置错乱 | §4.3 take-cloud 策略保守；arrive 之前备份 config.toml |
| Codex 启动时 cache 重建失败（网络问题、SSH key 缺失）| 中 | plugin 短期不可用 | doctor arrive 输出明确警告："plugin cache will rebuild on next Codex start; ensure SSH key for private marketplaces" |
| 两台 Mac 真实**并发** leave/arrive | 低 | iCloud `_merged.toml` 被覆盖 | doctor leave 时检查 `_merged.toml.lock`；arrive 时同 |

---

## 6. 与 v4 阶段 3 的合并

**v4 plan 阶段 3 的原内容**（[2026-05-13-v4-integrated-roadmap.md](2026-05-13-v4-integrated-roadmap.md)）：

```
阶段 3（Req #1 + #2，plugin sync 架构重构）
  □ 实现 _merge_toml_plugins_union，arrive 和 leave 两侧都用
  □ 从 products.codex.json entries 移除 plugins 条目
  □ 迁移期支持：检测到 plugins/ 还是 symlink 时提示去 symlink（不自动）
  □ 一次性 cleanup：iCloud plugins/cache/ 里 30+ 冲突副本清理
  □ 测试 fixture：模拟多 Mac 并发 enable/disable 场景
```

**用本方案重写后的阶段 3**：

```
阶段 3（基于 codex 源码研究重设计）
  □ doctor 新增 codex_plugin_config_extractor：从 ~/.codex/config.toml 抽取
    可同步的 [plugins.*] 和 [marketplaces.*]，过滤 openai-bundled.source 等
    机器本地字段
  □ doctor 新增 union_merge_plugin_config：按 §4.3 算法
  □ doctor leave 写 iCloud/CodexSync/snapshots/config-toml/_merged.toml
  □ doctor arrive 读 iCloud/.../_merged.toml 并 merge 进本机 config.toml
  □ 从 products.codex.json entries 移除 plugins 条目
  □ 新增 products.codex.json entries：snapshots/config-toml/ (file 类，特殊处理)
  □ 测试 fixture：simulate 两台 Mac 各 enable 不同 plugin → merge 后两边 union
  □ 测试 fixture：simulate openai-bundled.source 字段不被同步污染
  □ 文档化：迁移指引（§3 内容）作为单独的 release notes
```

阶段 4（hostname → IOPlatformUUID）和阶段 5（jsonl durability）不受影响。

---

## 7. Open Questions

1. **MBP 的当前状态实际如何？** 本方案是基于 iMac 的观察推断 MBP 应该相似。在执行 §3.4 前必须先在 MBP 上跑一遍 §3.1 + §3.2 验证。

2. **Codex Desktop 重启后 cache 重建到底要多久？** 全新一次 startup 可能要 1-3 分钟（curated plugins clone + N 个 marketplace upgrade + cache refresh）。需要在 §3.3 A8 步实测，给用户一个合理的等待提示。

3. **§4.3 union_merge 的 enable 字段语义**："any-true wins" 有个 corner case：用户故意 disable 某个 plugin 后切机，merge 后又被 enable。后续 v4.4 应当加 `last_disabled_at_<ts>` 字段记录显式 disable 动作，让 disable 比 enable 更"粘"。

4. **`[marketplaces.openai-bundled]` 为什么会在 user config.toml？** 按研究第 4.3 节，curated 这种隐式 root **不会** 出现在 user config 里。但 bundled 可能因为 Codex Desktop 启动时主动写入。**已实测**：iMac 上确实有 `[marketplaces.openai-bundled]` 和 `[marketplaces.openai-primary-runtime]` 两条 local source 段，由 Codex Desktop 启动时写入。同用户名场景下不构成毒丸（见 §1.2），但仍是迁移时需要 sanity check 的对象。

5. **`plugins/.marketplace-plugin-source-staging/` 长期残留**：研究指出 Codex 自己没清理这个目录的逻辑。doctor 阶段 4+ 可以加一个低风险的 GC（只删 24 小时前的 staging dir）。

6. **`openai-primary-runtime` 的 bootstrap 机制**：实测 source 是 `~/.cache/codex-runtimes/codex-primary-runtime/plugins/openai-primary-runtime`，这是 macOS 的 user cache directory（**不在 iCloud**，是本机 cache）。但**谁负责创建它**？三种可能：(a) Codex Desktop 启动时检测、不在就从某处下载；(b) 一次性运行 codex CLI 时安装；(c) 由独立的 codex-runtimes 服务/包提供。需要 P0 调查清楚。如果是 (a)，那么另一台 Mac 启动 Codex Desktop 后会自愈；如果是 (b)，需要让用户手工 trigger；如果是 (c)，需要查包 manager。**对迁移影响**：B8 步若发现 `~/.cache/codex-runtimes/...` 不存在，要根据机制选合适的恢复方式（最简单：跑一次完整的 Codex Desktop 启动看会不会自动 bootstrap）。

---

## 8. 决策点（2026-05-14 已 resolved）

- [x] **§3.2 主 Mac**：iMac（28 plugin 完整集作为真源）
- [x] **§3.3 A4**：**不删** iCloud plugins/。改为"本地从 iCloud 复制后解 symlink"的 bootstrap 方式（A1 步已重写）。iCloud 副本保留作冷备份，长期清理时机由用户后续决定
- [x] **§3.5 后续**：完成一次性迁移后**立即**进入 §4 长期方案的 doctor v4.3 代码实现
- [x] **§4.3 union enable 语义**：选 **"any-true wins"**（保守恢复 enable，简单实现）。"take-newer" 推迟到将来如果出现"显式 disable 被复活"的真实抱怨再加 timestamp 字段

---

## 9. 与今天事件的因果链

回顾 [ISSUES-2026-05-13](../ISSUES-2026-05-13-codex-data-loss.md)：

- 5/7 22:43 iCloud sync 冲突 → `config.toml.conflict-ParkerdeiMac-11-20260507-224331` 静默吞掉 14 条 plugin enable
- 5/13 用户用 28 plugin 手工恢复（pre-plugin-restore 备份）
- 5/13 晚 doctor 调研发现 plugins/ symlink 是冲突温床
- 5/14 codex 源码研究：**plugins/ symlink 本就不该存在**

这条因果链表明：**5/7 的事故根因不是 doctor 没拦截 conflict 文件，而是架构上不该让 plugins/ 上 iCloud**。doctor scan-conflicts 是好工具但治标；§4 的"只 sync config.toml"是治本。

完成本方案后，5/7 类似事故的复发概率应当趋近于 0：

1. plugins/ 不再 iCloud sync → 不会再产生 30+ 冲突副本
2. doctor 只 sync config.toml + union merge → enable 列表的多机操作合并到一起，不会被 last-writer-wins 吞
3. doctor scan-conflicts + clean-conflicts 仍保留，作为系统级冲突的最后兜底
