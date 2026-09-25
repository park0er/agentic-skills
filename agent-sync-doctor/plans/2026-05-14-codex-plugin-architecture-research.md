# Codex Plugin 架构研究报告（基于 openai/codex@main）

> 调研日期：2026-05-14
> 信息源：openai/codex GitHub `main` 分支（截止本日 HEAD）
> 调研范围：`codex-rs/core-plugins/`、`codex-rs/config/`、`codex-rs/app-server/src/request_processors/plugins.rs`、protocol schema (`codex-rs/app-server-protocol/`)
> 本机产品版本：Codex Desktop 26.506.31421（macOS）
> 本报告由 Explore agent 阅读 openai/codex 源码产出，所有论点都附带 `<file>:<line>` 引用，便于复核

---

## 1. Executive Summary

**三句话回答最关键的问题：**

1. **Plugin 真实源码存储 = `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`**。这是 `PluginStore` 唯一的"权威 active 路径"——`load_plugin` 启动每个 plugin 时只读这里（`codex-rs/core-plugins/src/loader.rs:512`：`store.active_plugin_root(plugin_id)`，找不到就报 `plugin is not installed`）。`.tmp/plugins/`、`.tmp/marketplaces/`、`.tmp/bundled-marketplaces/` 都是**源（source）**，不是运行时根；它们的内容会在每次 install / cache refresh 时被复制（不是 symlink，是 `fs::rename` 原子替换，见 `store.rs::replace_plugin_root_atomically`）到 `plugins/cache/`。

2. **完整生命周期 = "marketplace add → plugin install → config.toml enabled = true → cache refresh on start"**。用户点 Install → JSON-RPC 调 `plugin/install`（`PluginInstallParams { marketplacePath, pluginName }`）→ `PluginsManager::install_plugin` → `materialize_marketplace_plugin_source`（如果是 Git source 则 clone 到 `plugins/.marketplace-plugin-source-staging/`）→ `PluginStore::install` 复制源到 `plugins/cache/<mp>/<plugin>/<version>/` → `set_user_plugin_enabled` 写 `[plugins."plugin@mp"] enabled = true`。

3. **跨机同步策略 = "config.toml + plugins/cache 应共享；.tmp/* 各机独立可重建"**。`config.toml` 的 `[plugins.*]` 和 `[marketplaces.*]` 段是用户意图（必须共享），`plugins/cache/` 是 install 后的可执行 plugin（共享性能更好，但理论上可重建）；`.tmp/plugins/`、`.tmp/marketplaces/`、`.tmp/bundled-marketplaces/` 是 git clone 缓存或 bundled bootstrap 数据，**两台 Mac 各自重建零冲突**——它们都是确定性的（curated 由 `.tmp/plugins.sha` 决定，user marketplace 由 `[marketplaces.*]` 的 `source` + `last_revision` 决定）。

---

## 2. 三套 Layout 的职责对比表

| 路径 | 在源码中的常量 | 数据来源 | 谁写 | 谁读 | 跨机同步建议 |
|------|----------------|----------|------|------|--------------|
| `plugins/cache/<mp>/<plugin>/<version>/` | `PLUGINS_CACHE_DIR = "plugins/cache"` (`store.rs:14`) | 从下面三类 source 复制（`copy_dir_recursive`） | `PluginStore::install` / `install_with_version`（`store.rs:99-145`） | `load_plugin` 启动时（`loader.rs:512`），**唯一权威 active 根** | **必须共享**；缺失则配置中 `enabled=true` 的 plugin 会报 "plugin is not installed" |
| `plugins/data/<plugin-name>-<mp-name>/` | `PLUGINS_DATA_DIR = "plugins/data"` (`store.rs:15`) | hooks 运行时数据 | hook handler（`load_plugin_hooks` 传 `store.plugin_data_root`） | hooks 执行时 | **各机独立**（运行时状态） |
| `.tmp/plugins/` | `CURATED_PLUGINS_RELATIVE_DIR = ".tmp/plugins"` (`startup_sync.rs:27`) | `git clone --depth 1 https://github.com/openai/plugins.git`（`startup_sync.rs:140-148`），失败回退 GitHub HTTP zipball、再回退 ChatGPT export archive | `sync_openai_plugins_repo`（启动时一次性、有 SHA 短路） | `refresh_curated_plugin_cache` 把里面的 plugin 拷到 `plugins/cache/openai-curated/` | **可不共享**：每台 Mac 启动会自动 clone；但共享能省 89MB 流量+磁盘 |
| `.tmp/plugins.sha` | `CURATED_PLUGINS_SHA_FILE = ".tmp/plugins.sha"` (`startup_sync.rs:28`) | `git ls-remote` 拿到的 HEAD SHA | `write_curated_plugins_sha` | `read_curated_plugins_sha` 决定要不要重新 clone | 可共享（与 `.tmp/plugins` 配套）；但若 `.tmp/plugins` 不共享则**绝不要**单独共享这个文件 |
| `.tmp/marketplaces/<mp>/` | `INSTALLED_MARKETPLACES_DIR = ".tmp/marketplaces"` (`installed_marketplaces.rs:13` 和 `marketplace_upgrade.rs:25`) | `git clone <user-add 的 URL>` 到 `.tmp/marketplaces/.staging/marketplace-add-XXX/` 然后 rename 到 `.tmp/marketplaces/<name>/`（`marketplace_add/install.rs:6-37`） | `add_marketplace_sync` | `installed_marketplace_roots_from_layer_stack` 读 `[marketplaces.*]` 配置后从这里拉 plugin source | **可不共享**（每台 Mac 由 `[marketplaces.*]` 的 `source_type=git` + `source` URL 自动重建，由 `marketplace upgrade` 维护） |
| `.tmp/bundled-marketplaces/openai-bundled/` | **未出现在 codex-rs 源码任何位置** | 从 `Codex.app/Contents/Resources/plugins/`（Electron 端） bootstrap | Codex Desktop（Electron 主进程）写入；codex-rs 服务端不写 | 通过 `[marketplaces.openai-bundled]` 的 `source_type=local` + `source=<本机绝对路径>` 被 `installed_marketplace_roots_from_layer_stack` 当作"本地 marketplace"读取 | **必须各机独立**（路径写死本机绝对路径，**强烈不可共享**——这是迁移最大的坑） |
| `.tmp/app-server-remote-plugin-sync-v1` | `STARTUP_REMOTE_PLUGIN_SYNC_MARKER_FILE` (`startup_remote_sync.rs:13`) | 启动时把后端的"installed remote plugins"补回本地 cache 后写入"已完成"标记 | `start_startup_remote_plugin_sync_once` (`startup_remote_sync.rs:16`) | 同上函数：marker 存在则跳过 | **各机独立**（本机一次性 bootstrap 标记） |
| `plugins/.marketplace-plugin-source-staging/marketplace-plugin-source-XXXXXX/` | hardcoded (`loader.rs:1103`) | install 期间 `git clone` 出来的临时副本 | `materialize_marketplace_plugin_source`（`loader.rs:1088-1146`） | install 期间一次性使用，TempDir drop 时自动清理 | 不会持久化；理论可见瞬态目录 |
| `plugins/.remote-plugin-install-staging/` | `REMOTE_PLUGIN_INSTALL_STAGING_DIR` (`remote_bundle.rs:30`) | 远端 plugin tar.gz 下载解压 | `remote_bundle.rs` | 一次性 install | 不持久化 |

**关键澄清（针对原问题 1）**：本机看到的 `.tmp/plugins/plugins/<123 个 plugin 目录带 .git 子目录>` 这一层不是"123 个独立 git clone"，而是**一个**对 `openai/plugins` repo 的浅克隆，repo 本身的目录结构就是 `plugins/<plugin-name>/`。本机看到的 `.git` 是这一个 clone 的 `.git`。

---

## 3. Plugin 生命周期流程图

### 3.1 Install（用户点 "Install"）

```
[User clicks Install in Composer/TUI]
        ↓
JSON-RPC: plugin/install
  PluginInstallParams { marketplacePath, pluginName }
  (codex-rs/app-server-protocol/schema/typescript/v2/PluginInstallParams.ts)
        ↓
PluginRequestProcessor::plugin_install_response
  (app-server/src/request_processors/plugins.rs)
        ↓
PluginsManager::install_plugin
  (core-plugins/src/manager.rs:install_plugin → install_resolved_plugin)
        ↓
1. find_installable_marketplace_plugin(marketplace_path, plugin_name)
   读 marketplace.json，得到 ResolvedMarketplacePlugin
   ├── source = Local { path }    → path 已经是本地 absolute
   └── source = Git { url, ref, sha, sub-path }  → 进入 step 2
        ↓
2. materialize_marketplace_plugin_source(codex_home, source)
   (core-plugins/src/loader.rs:1088)
   - Local : 直接返回 path，无副作用
   - Git   : 在 plugins/.marketplace-plugin-source-staging/ 下创 tempdir
             git clone --filter=blob:none [--sparse] <url> <tempdir>
             git checkout <sha or ref>
             返回 tempdir+sub-path 作 source_path
        ↓
3. PluginStore::install(source_path, plugin_id)
   (core-plugins/src/store.rs:99)
   - 读 source_path/.codex-plugin/plugin.json 拿 plugin_version (默认 "local")
   - tempdir 下 staged 副本，再 fs::rename(staged, plugins/cache/<mp>/<plugin>/<version>)
   - 失败时 atomic rollback
   curated marketplace 用 .tmp/plugins.sha 的前 8 位作为 version （loader.rs:280）
        ↓
4. set_user_plugin_enabled(codex_home, "<plugin>@<mp>", true)
   (config/src/plugin_edit.rs:set_plugin_enabled → write_atomically)
   写 [plugins."<plugin>@<mp>"] enabled = true
        ↓
5. analytics_events_client.track_plugin_installed(...)
   (manager.rs:install_resolved_plugin tail)
        ↓
返回 PluginInstallResponse { authPolicy, appsNeedingAuth }
```

### 3.2 Uninstall

```
plugin/uninstall { pluginId }
  → PluginsManager::uninstall_plugin → uninstall_plugin_id
     - PluginStore::uninstall  → fs::remove_dir_all(plugins/cache/<mp>/<plugin>/)
     - clear_user_plugin       → 删 [plugins."<plugin>@<mp>"]
```

### 3.3 Marketplace Add

```
marketplace/add { source, refName?, sparsePaths? }
  → add_marketplace_sync (core-plugins/src/marketplace_add.rs)
     - parse_marketplace_source: github-shorthand / git-url / local-path
     - if Local: 不复制，直接把 absolute path 记到 [marketplaces.<name>] source_type="local"
     - if Git : 在 .tmp/marketplaces/.staging/marketplace-add-XXX/ 下 git clone
                rename 到 .tmp/marketplaces/<safe_name>/
                写 [marketplaces.<name>] last_updated/source_type="git"/source/ref/sparse_paths
```

### 3.4 Marketplace Upgrade

```
marketplace/upgrade { marketplaceName? }
  → upgrade_configured_git_marketplaces (core-plugins/src/marketplace_upgrade.rs)
     - 只处理 source_type=git 的
     - git_remote_revision(source, ref) 拿当前 SHA
     - 如果 [marketplaces.<n>].last_revision == 远端 SHA 且本地 marketplace.json 存在：跳过
     - 否则在 .tmp/marketplaces/.staging/ clone，rename 替换 .tmp/marketplaces/<n>/，写回 last_revision
```

### 3.5 启动时三层自动同步

App-server 启动时自动跑（一次性，幂等）：

```
1. sync_openai_plugins_repo (CURATED_REPO_SYNC_STARTED 防并发，startup_sync.rs:62)
   - 比较 .tmp/plugins.sha vs git ls-remote HEAD
   - 不一致：clone 到 tempdir，校验 SHA，rename 替换 .tmp/plugins/，写新 sha
   - 失败路径：git → GitHub HTTP zipball → ChatGPT export-archive

2. refresh_curated_plugin_cache (loader.rs:185)
   遍历 config 中 marketplace_name == "openai-curated" 的 plugin id
   - active_plugin_version != cache_plugin_version(SHA[..8])：从 .tmp/plugins/plugins/<n>/ install 到 plugins/cache/openai-curated/<n>/<sha8>/

3. refresh_non_curated_plugin_cache (loader.rs:312)
   对 [marketplaces.*] 已添加的非 curated marketplace：
   - 通过 list_marketplaces 在 .tmp/marketplaces/<mp>/ 找 plugin
   - 同 plugin_version 比较，不一致就 install_with_version

4. start_startup_remote_plugin_sync_once (startup_remote_sync.rs:16)
   - 若 .tmp/app-server-remote-plugin-sync-v1 存在：跳过
   - 否则等 has_local_curated_plugins_snapshot，调 sync_plugins_from_remote(additive_only=true)
   - 把 ChatGPT 后端登记为 "installed" 的 plugin 在本地 plugins/cache 也补出来，写 marker
```

### 3.6 "plugin-restore" 真相

`gh search code --repo openai/codex 'plugin-restore'` 返回 **空结果**（同样 `pre-bluegold` / `pre-pin` / `pre-clone` / `pre-merge` 全部 0 命中）。

**结论**：本机 `config.toml.bak.pre-plugin-restore-20260513-183955` **不是 Codex 内置功能产生的**。这是某段外部脚本（极可能是 agent-sync-doctor / claude-sync-doctor 或用户/IT 的 LaunchAgent）在做 "plugin restore" 操作前做的备份。Codex 自己的备份/临时文件命名只用过 `plugin-install-` / `plugin-backup-` (`store.rs:202`、`store.rs:218`：`tempfile::Builder::prefix(...)`)，不会留 `pre-XXX` 后缀的备份。

**这与 ISSUES-2026-05-13 里的"今天 18:39 的 pre-plugin-restore"是用户手工恢复 28 plugins 时另一个 agent 留的备份"的判断完全一致**。

---

## 4. config.toml 字段手册

### 4.1 `[plugins."<id>"]` 段

`<id>` 格式 = `"<plugin-name>@<marketplace-name>"`（`PluginId::as_key`），**必须带引号**（含 `@`）。

| 字段 | 类型 | 来源（源码） | 含义 | 跨机同步 |
|------|------|--------------|------|----------|
| `enabled` | bool | `PluginConfig::enabled` (`config/src/types.rs`)，默认 `true` | 是否在 thread 启动时加载这个 plugin | **共享** —— 这是用户意图 |
| `mcp_servers.<name>` | table | `PluginMcpServerConfig` | 对该 plugin 提供的 MCP server 的 enable/approval/tool 白名单覆盖 | **共享** |
| `mcp_servers.<name>.enabled` | bool | 默认 `true` | 单个 MCP server 是否启用 | 共享 |
| `mcp_servers.<name>.default_tools_approval_mode` | enum | `AppToolApproval` | 该 MCP server 的默认审批模式 | 共享 |
| `mcp_servers.<name>.enabled_tools` | `Vec<String>` | 白名单 | 共享 |
| `mcp_servers.<name>.disabled_tools` | `Vec<String>` | 黑名单 | 共享 |
| `mcp_servers.<name>.tools.<tool>.approval_mode` | enum | 单 tool 审批 | 共享 |

测试中出现过 `source = "/tmp/plugin"` 字段（`plugin_edit.rs::set_user_plugin_enabled_preserves_existing_plugin_fields`），但这只是 schema 容忍未知字段、不在 PluginConfig 里**定义**。结论：`source` 不是 stable schema，最多视为忽略。

> **注意**：`PluginConfig` 用 `#[schemars(deny_unknown_fields)]`，但实际 `set_plugin_enabled` 是 `toml_edit` 直写——会保留任何额外字段。这意味着第三方工具往 `[plugins.x]` 加 metadata 是可行的，但 Codex 不读它。

### 4.2 `[marketplaces."<name>"]` 段

| 字段 | 类型 | 含义 | 跨机同步 |
|------|------|------|----------|
| `last_updated` | string ISO timestamp | 上次 add/refresh 时间 | 共享，但不重要 |
| `last_revision` | string git SHA | 上次成功激活的 git 版本 | **必须共享**（控制 upgrade 短路） |
| `source_type` | `"git"` 或 `"local"` | 源类型 | **共享** |
| `source` | string | git URL 或 local 绝对路径 | git 类**共享**；local 类**必须各机独立**（绝对路径！） |
| `ref` | string? | git ref（branch/tag） | 共享 |
| `sparse_paths` | `Vec<String>?` | git sparse-checkout | 共享 |

**关键陷阱**：`[marketplaces.openai-bundled]` 在本机大概率是 `source_type = "local"`、`source = "/Users/park0er/.codex/.tmp/bundled-marketplaces/openai-bundled"`（或类似绝对路径，由 Codex Desktop 写入）。这条**绝不能跨机同步**——另一台 Mac 的 `~/Users/<otheruser>/...` 路径不一样。

### 4.3 `[plugins.*]` vs `[marketplaces.*]` 关系

- 一个 plugin 必须先通过它所在 marketplace 被 listed 才能被 install，install 时用 marketplace_path 定位 marketplace.json
- 一个 plugin 可以同名但来自不同 marketplace（`<plugin>@<mp1>` 和 `<plugin>@<mp2>` 是不同 PluginId）；本机看到 `github@claude-plugins-official` 和 `github@openai-curated` 就是这样
- `[marketplaces.openai-curated]` **不会**出现在用户 config（curated 是隐式 root，由 curated_plugins_repo_path 自动作为额外 marketplace 注入，见 `manager.rs::marketplace_roots`）

---

## 5. Marketplace 的 git clone 机制

### 5.1 三个 git clone 入口

| clone 入口 | 谁触发 | 目标 | 模式 |
|------------|--------|------|------|
| `sync_openai_plugins_repo_via_git` (`startup_sync.rs:140`) | App-server 启动 | `.tmp/plugins/` | `git clone --depth 1 https://github.com/openai/plugins.git`，**hardcoded URL** |
| `clone_git_source` (`marketplace_add/install.rs:9`) | `marketplace/add` RPC | `.tmp/marketplaces/.staging/marketplace-add-XXX/`，rename 到 `.tmp/marketplaces/<n>/` | `git clone <url>`，可选 `--filter=blob:none --no-checkout` + `sparse-checkout` |
| `clone_git_plugin_source` (`loader.rs:1148`) | `plugin/install`（Git source） | `plugins/.marketplace-plugin-source-staging/marketplace-plugin-source-XXX/` | 单 plugin clone，可 sparse |
| `git_remote_revision` (`marketplace_upgrade/git.rs`) + `clone_git_source` | `marketplace/upgrade` RPC | 同 add 流程 | 同 |

### 5.2 URL 来源

- Curated：**hardcoded** `https://github.com/openai/plugins.git`（`startup_sync.rs::sync_openai_plugins_repo_via_git` line ~141-148）
- 用户 marketplace：`[marketplaces.<n>].source` 字段，由用户当初 `marketplace/add` 时输入（GitHub shorthand `owner/repo` 会自动变成 `https://github.com/owner/repo.git`）
- 单 plugin Git source：`marketplace.json` 里 `plugins[].source` 字段

### 5.3 认证

`run_git` 设 `GIT_TERMINAL_PROMPT=0`（`marketplace_add/install.rs:124`）—— **禁止交互式认证**，只支持系统 git credential helper / SSH key。所以私有 repo marketplace 在本机能 clone 是因为本机 SSH key/keychain；**跨机同步时另一台 Mac 必须独立配置 SSH key**，否则 `marketplace upgrade` 会失败。

### 5.4 两台 Mac 的 clone 冲突？

不会。`fs::rename(.staging/marketplace-add-XXX, <name>)` 是原子的，并且写 `[marketplaces.<n>] last_revision = <sha>` 后两边只是 SHA 比较 → 一致就 short-circuit。即使两台 Mac 同时 add 同 URL，结果也收敛。

但 **`plugins/cache/`** 是按 `<mp>/<plugin>/<version>` 分层，复制源是文件系统拷贝（非 git）。如果两台 Mac 同时 install 同一 plugin 到一个共享 iCloud `plugins/cache/`，`replace_plugin_root_atomically` 的 staged tempdir 是 process-local 的，但目标 rename 不是分布式锁——iCloud 跨机并发 install 同一 plugin 理论上能竞态。**实践上**：用户极少两台 Mac 同时点一个 plugin 的 Install；保守起见 doctor 在 leave/arrive 时用 advisory lock + checkpoint 即可。

---

## 6. PluginsMigration 机制

### 6.1 真相：和原假设不一样

`PluginsMigration` 不是 v1 → v2 schema 升级，**也不是 layout 迁移**。

源码定义在 `codex-rs/app-server-protocol/src/protocol/v2/config.rs`：

```rust
pub struct PluginsMigration {
    pub marketplace_name: String,
    pub plugin_names: Vec<String>,
}

pub struct MigrationDetails {
    pub plugins: Vec<PluginsMigration>,
    pub sessions: Vec<SessionMigration>,
    pub mcp_servers: Vec<McpServerMigration>,
    pub hooks: Vec<HookMigration>,
    pub subagents: Vec<SubagentMigration>,
    pub commands: Vec<CommandMigration>,
}
```

它在两个 RPC 中出现：

- `external_agent_config/detect`：返回一个 `ExternalAgentConfigDetectResponse { items }`，每个 `item.details` 是 `MigrationDetails`
- `external_agent_config/import`：用户选好后 import

实际逻辑在 `codex-rs/app-server/src/config/external_agent_config.rs`，handler `import_plugins` 把外部 agent（**Claude Code、Cursor 等**）的 marketplace + plugin 列表导入 Codex 自己的 marketplaces/plugins 配置（`partition_plugin_migration_details` 把 local vs remote 分开导入）。

### 6.2 对照本机 `.codex-global-state.json.pre-bluegold-*` / `pre-clone-*` / `pre-pin-*` / `pre-merge-*` 备份

`gh search code` 全部 0 命中。这些备份文件**不是 Codex 自己生成的**。最可能的解释（按概率排序）：

1. **agent-sync-doctor / claude-sync-doctor 之前版本生成的**：这个 sync doctor 工具的早期实现。`bluegold` 显然是某个内部代号（项目代号 / 阶段名），`pre-pin` 看起来像"pin 某个 sessionId 之前的备份"，`pre-clone` 像"clone session 之前"，`pre-merge` 像"merge global state 之前"，`pre-icloud` 像"切到 iCloud symlink 之前"。
2. **手工运维**或某个 LaunchAgent 跑过迁移脚本时留下的。

**重要含义**：v4 doctor plan 的"阶段 3 plugin union merge" **没有** Codex 内置 schema migration 可借鉴；要自己设计 union 算法。值得借鉴的反而是：
- `set_user_plugin_enabled` 的 `write_atomically` + `resolve_symlink_write_paths`（穿透 symlink 到真实目标写）
- `PluginStore::replace_plugin_root_atomically` 的 staging-then-rename 模式

---

## 7. 对 agent-sync-doctor 的设计启示（10 条）

1. **`plugins/cache/` 是性能关键，不是正确性关键**。理论上"删了 cache 重启 Codex 会自动从 `[plugins.*]` enabled 列表 + `.tmp/plugins/` 重建"，但只有 curated plugin 能自动重建（`refresh_curated_plugin_cache`）；非 curated plugin 需要 `[marketplaces.*]` 还在。所以 doctor 阶段 3 的 "去 symlink 化 plugins/" 完全可行——丢失最坏情况是下次启动多花一次 install 时间。

2. **`[plugins.*]` 是 union merge 的天然字段**。两台 Mac 各自 enable 不同 plugin，merge 时 take-newer-by-key 就行；没有顺序依赖（不像 MCP server 的 transport 配置可能冲突）。

3. **`[marketplaces.openai-bundled]` 的 `source` 字段是绝对路径毒丸**。doctor 阶段 3 必须**显式跳过** `openai-bundled` 这条 marketplace 配置，或者只同步 `last_revision`/`last_updated` 等无路径字段。Mac A 的 `/Users/parker/...bundled.../openai-bundled` 在 Mac B 上是死路径。

4. **`.tmp/bundled-marketplaces/`、`.tmp/plugins/`、`.tmp/marketplaces/`、`.tmp/app-server-remote-plugin-sync-v1` 全部应该排除在 sync 之外**。它们都是 codex_home 的本机 cache，每台 Mac 启动时独立重建。同步它们只会带来跨机不一致（特别是 bundled 的绝对路径）。

5. **`.tmp/plugins.sha` 也别同步**。它是 `.tmp/plugins/` 的指纹；分开同步会导致"sha 已变但目录还旧 → Codex 以为已最新但实际旧"，比不同步更糟。Codex 启动时 `read_local_git_or_sha_file` 会两边读（git HEAD 或 sha 文件），最终都会做 SHA 校验。

6. **Marketplace clone 凭据是本机的**。doctor 在 arrive 时如果发现 `[marketplaces.<n>] source_type = "git"` 是**私有 URL**而本机 git credential 不全，要给用户一个明确的"先配 SSH key"提示，而不是默默让 startup upgrade 失败。

7. **plugin install 的副作用 = `plugins/cache/<mp>/<plugin>/<v>/` + `[plugins.<id>] enabled=true` + `plugins/data/<plugin>-<mp>/` 三个**。`plugins/data/` 没有列入跨机同步典范（运行时 hook 数据），但要注意若同步它会把 hook 状态混在一起。建议：**`plugins/cache/` 同步、`plugins/data/` 不同步**。

8. **migration 模式参考**：Codex 的 `external_agent_config/import` 是 import-then-install 模式（不是 schema-bump），doctor 完全可以 borrow：先合 config.toml 的 `[plugins.*]` / `[marketplaces.*]`，然后**让 Codex 自己**通过 `refresh_curated_plugin_cache` / `refresh_non_curated_plugin_cache` 在下次启动时把 `plugins/cache/` 补齐。这意味着 doctor v4 阶段 3 的最简方案是**只同步 config.toml + 让 Codex 自愈 cache**。

9. **PluginStore 的 atomic rename 友好**：doctor 写 `plugins/cache/` 时如果用 `fs::rename` 而不是 `cp -r`，会和 Codex 自己的 install 流程兼容；如果用 rsync 拷贝过程中 Codex 正好启动 install，可能产生半成品目录。建议 doctor 在改 `plugins/cache/` 前 advisory-lock。

10. **`.codex-global-state.json` 的 `pre-*.bak` 备份是 doctor 工具早期产物**——这是个发现而非问题。但说明以前做过类似 union merge 工作；v4 plan 应当**梳理历史 .bak 文件清理策略**（保留 N 份、按日期 GC 等），免得 iCloud 容量被吃满。

---

## 8. Open Questions（仍未完全确定的点）

1. **`.tmp/bundled-marketplaces/` 谁写入？** codex-rs 不写这个路径。最可能的写者：Codex Desktop（Electron 主进程）在首次启动时把 `Codex.app/Contents/Resources/plugins/` 解压/复制过来。需要从 Codex Desktop 的 JS 端代码（不在 openai/codex 这个开源 repo 里？需要确认）求证。**对 doctor 设计影响**：把它当作"本机 read-only bootstrap"，doctor 不应触碰；如果消失，重启 Codex Desktop 会重建。

2. **`Codex Helper (Plugin).app` 的角色**：很可能是 Electron 的 utility process（plugin 用来跑 sandbox 内的浏览器/UI），但它怎么和 codex-rs app-server 通信、是否每个 plugin 一个进程，源码层面没有明确证据（codex-rs 是 Rust，跑 plugin 时 hook subprocess 用的是 `Command::new`）。**对 doctor 影响**：可能无关，跨机同步不涉及它。

3. **`PluginStore::active_plugin_version` 的版本仲裁**：当 `plugins/cache/<mp>/<plugin>/` 下有多个版本目录时，存在 `local` 就用 `local`，否则取**字典序最大**的一个。**doctor 影响**：跨机 merge 后如果两边各有一个不同版本目录都保留，Codex 会选字母序大的；最好 doctor merge 时只保留一个 active version（与 config 中 enabled 状态匹配的那一个）。

4. **`plugins/.remote-plugin-install-staging/` 和 `plugins/.marketplace-plugin-source-staging/` 这两个 staging dir 是否会留垃圾？** 两个都用 `tempfile::TempDir`，正常 drop 时清理；但如果进程 crash，会留垃圾。`.tmp/plugins/` 那边有 `remove_stale_curated_repo_temp_dirs` 清理 `plugins-clone-*`（10 分钟超时），但 `plugins/.*-staging/` 没看到清理逻辑。**doctor 加一个清理 step 是低风险的加分项**。

5. **`PluginsMigration` 在 ChatGPT remote sync 中是否复用？** 仅看到它在 `external_agent_config` (Claude/Cursor → Codex) 中使用。`startup_remote_sync` 走 `sync_plugins_from_remote` 是另一条 ChatGPT 后端 path，不复用 `PluginsMigration` 类型。

---

## 9. 文件路径速查（所有路径相对 `~/.codex/`）

```
config.toml                               ← [plugins.*] + [marketplaces.*]，必同步
plugins/cache/<mp>/<plugin>/<version>/    ← 真实 active plugin 源码，跨机共享强烈推荐
plugins/data/<plugin>-<mp>/               ← hook 运行时数据，跨机不同步
plugins/.marketplace-plugin-source-staging/  ← install 期间 git clone 临时区，瞬态
plugins/.remote-plugin-install-staging/   ← 远端 plugin tar.gz 解压临时区，瞬态
.tmp/plugins/                             ← curated marketplace（openai/plugins.git clone）
.tmp/plugins.sha                          ← curated marketplace HEAD SHA
.tmp/marketplaces/<mp>/                   ← user-added marketplace clone
.tmp/marketplaces/.staging/               ← marketplace add/upgrade 临时区
.tmp/bundled-marketplaces/openai-bundled/ ← Codex Desktop (Electron) 写入，本机 absolute
.tmp/app-server-remote-plugin-sync-v1     ← startup remote sync 完成 marker
```

## 10. 关键源码引用（基于 `main`，`<file>:<line>`）

- `PLUGINS_CACHE_DIR = "plugins/cache"` → `codex-rs/core-plugins/src/store.rs:14`
- `PLUGINS_DATA_DIR = "plugins/data"` → `codex-rs/core-plugins/src/store.rs:15`
- `INSTALLED_MARKETPLACES_DIR = ".tmp/marketplaces"` → `codex-rs/core-plugins/src/installed_marketplaces.rs:13` 和 `marketplace_upgrade.rs:25`
- `CURATED_PLUGINS_RELATIVE_DIR = ".tmp/plugins"` → `codex-rs/core-plugins/src/startup_sync.rs:27`
- `CURATED_PLUGINS_SHA_FILE = ".tmp/plugins.sha"` → `startup_sync.rs:28`
- `STARTUP_REMOTE_PLUGIN_SYNC_MARKER_FILE = ".tmp/app-server-remote-plugin-sync-v1"` → `startup_remote_sync.rs:13`
- `REMOTE_PLUGIN_INSTALL_STAGING_DIR = "plugins/.remote-plugin-install-staging"` → `remote_bundle.rs:30`
- `marketplace-plugin-source-staging` 路径 → `loader.rs:1103`
- `OPENAI_CURATED_MARKETPLACE_NAME = "openai-curated"` → `core-plugins/src/lib.rs:21`
- `OPENAI_BUNDLED_MARKETPLACE_NAME = "openai-bundled"` → `lib.rs:22`
- `MARKETPLACE_MANIFEST_RELATIVE_PATHS = [".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"]` → `marketplace.rs:21`
- `set_user_plugin_enabled` 写 `[plugins."<key>"] enabled = true` → `config/src/plugin_edit.rs:90-104`
- `record_user_marketplace` 写 `[marketplaces."<n>"]` → `config/src/marketplace_edit.rs:30-38`
- Plugin install RPC handler → `app-server/src/request_processors/plugins.rs::plugin_install_response` (~line 980)
- `PluginsManager::install_resolved_plugin` → `core-plugins/src/manager.rs` (位于 `install_plugin` 之后约 50 行)
- `git clone https://github.com/openai/plugins.git` (curated, hardcoded) → `startup_sync.rs:140-148`
- `GIT_TERMINAL_PROMPT=0` 禁交互认证 → `marketplace_add/install.rs:124`
- `PluginsMigration` 类型定义 → `app-server-protocol/src/protocol/v2/config.rs`
- `plugin.json` schema 示例 → `codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md`
