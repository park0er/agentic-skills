# agent-sync-doctor CHANGELOG

> Skill 用途：跨多台 Mac 通过 iCloud 同步 Claude Code 和 Codex 的状态。
> 当前安装版可在 `~/.claude/skills/agent-sync-doctor/` 和 `~/.agents/skills/agent-sync-doctor/` 找到。
> 历史 archive 在 Factory 的 `archives/agent-sync-doctor/<ts>-<label>/`。

---

## 2026-05-16 — fix-skill-frontmatter-yaml

修 Codex 启动时报错 `invalid YAML: mapping values are not allowed in this context at line 2 column 420`。

**根因**：description 里包含 `Use for: handoff` 这个 `: `（colon-space）模式，被严格的 YAML 1.2 解析器当成 mapping 分隔符。Claude Code 的 YAML 解析器宽容所以一直没暴露，但 Codex 拒绝加载。

- 重写 description 906 → ~520 字符，无任何 `: ` 模式（改用 em-dash `—` 和句号）
- 按 superpowers:writing-skills CSO 原则：`Use when ...` 触发式开头，剥离工作流复述（原描述列了 `--products` 等运行细节，应只在 SKILL.md 正文出现）
- frontmatter 总字节 949 → 584，远低于 1024 spec 限制
- 同期 mify-model-gateway / icloud-materialization-doctor 也做了类似修复

---

## 2026-05-16 — add-changelog-md

合规性 release（无功能改动）。

- 新增本文件 `CHANGELOG.md`，作为今后 skill 的标准版本日志
- 同步全局规则：FACTORY.md / `~/.claude/CLAUDE.md` / `~/.codex/AGENTS.md` 三处都补充了"每个 skill 必备 CHANGELOG.md，release 前必须更新"的强制要求
- CHANGELOG 格式约定见 FACTORY.md "CHANGELOG 强制要求"段
- 此前的 release 历史（追溯）见下方各条目

---

## 2026-05-16 — v4.1-v4.2-v4.3-plugin-sync

三波 v4 改动一次 release（archive `20260516-131924-v4.1-v4.2-v4.3-plugin-sync`）。

### v4.1 整合数据完整性审计进 check / leave / arrive（2026-05-13）

- `check` 默认显示 integrity 摘要：top 3 条 session-integrity warning + top 3 条 iCloud conflict（30min gap 阈值）
- 新 flag `--no-integrity` / `--integrity-gap-minutes`
- `leave` 在 "Current check" 之后插入 "Integrity pre-check" 段
- `arrive` 最后加 "post-arrive integrity" 扫 conflict（warn 不阻塞）
- 内部提炼共享 helper `print_integrity_summary`，避免 cmd_check 和 run_handoff 重复

### v4.2 Conflict 升级为阻塞 + clean-conflicts 子命令（2026-05-14）

- **`leave` 现在被 iCloud conflict 残骸阻塞**（return 1），除非 `--ignore-conflicts`。理由：5/7 incident 的根因就是 conflict 文件被静默忽略；架构上不再让它溜过。
- 新子命令 `clean-conflicts`：默认 dry-run，`--apply` 才真删；`--under <prefix>` 可缩范围
- 安全闸：必须能推断 canonical 名 + canonical 必须存在才删
- `arrive` 后置扫 conflict，若新出现就 warn（不阻塞）

### v4.3 Plugin / Marketplace 跨机同步（2026-05-14 → 2026-05-16）

- **新机制**：`leave` 自动写 `iCloud/CodexSync/snapshots/config-toml/_merged.toml`；`arrive` 读它做 union-merge 写回本机 config.toml
- **设计哲学**：只同步 `[plugins.*]` 和 `[marketplaces.*]` 两段；plugin 源代码（`plugins/cache/`、`.tmp/*`）不再 doctor 管，**让 Codex 启动时 `refresh_curated_plugin_cache` / `refresh_non_curated_plugin_cache` 自愈**
- Union 算法：plugin 的 `enabled` 字段 any-true wins；marketplace 字段 take-cloud
- Sanity check：arrive 后扫所有 `source_type=local` 的 marketplace，验证 source 路径存在；缺失列 warning（针对跨用户名场景的防御）
- 新增模块函数：`extract_codex_plugin_config`、`union_merge_plugin_config`、`codex_plugin_leave_sync`、`codex_plugin_arrive_sync`、`verify_local_marketplace_paths`
- TOML 处理用 surgical regex 文本编辑（不依赖 tomllib / tomli_w），其它段（`model_providers`、`shell_environment_policy`、`projects`、`[[skills.config]]` 等）byte-for-byte 保留
- **manifest 改动**：`products.codex.json` 移除 `plugins` 条目（17 → 16 entries）。doctor 不再 verify `~/.codex/plugins/` symlink 状态。
- **迁移依赖**：用户机器上 `~/.codex/plugins/` 可能仍是 symlink → iCloud。一次性迁移流程见 `plans/2026-05-14-codex-plugin-migration-plan.md` §3。

### 关联文档

- 调研：`plans/2026-05-14-codex-plugin-architecture-research.md`
- 迁移方案：`plans/2026-05-14-codex-plugin-migration-plan.md`
- v4 总体路线：`plans/2026-05-13-v4-integrated-roadmap.md`
- 5/7 事故复盘：`ISSUES-2026-05-13-codex-data-loss.md`

### 已知风险 / 迁移指引

- 用户必须在每台 Mac 上跑一次 §3 一次性迁移把 `~/.codex/plugins/` 从 symlink 解开为本地目录。否则 leave 会被 conflict BLOCKER 拦住（除非用 `--ignore-conflicts`）。
- iCloud `CodexSync/dotcodex/plugins/` 89MB 冷备份保留不删（用户决策）。一周观察期后再决定清理。

---

## 2026-05-13 — integrate-materialization-gate

- 接入 `icloud-materialization-doctor` 配套 skill（File-Provider dataless 检测）
- `check` 显示 `iCloud dataless count`；不可用时 fail-open 显示 "n/a (install icloud-materialization-doctor to enable)"
- `arrive` 第二步加 dataless gate
- `leave` 通过 `icloud.ready` 字段隐式包含 dataless 检查

---

## 2026-05-14 — pre-git-removal-baseline

非功能性 release：删除 `Skill_Factory/.git/` 之前的基线快照。Factory 从此切换到 archive-based versioning（详见 `FACTORY.md`）。代码本身没变。

---

## 2026-05-08 — initial agent-sync-doctor release（archive `20260508-173935`）

`claude-sync-doctor` 重命名 / 升级为 `agent-sync-doctor`。统一处理 Claude Code 和 Codex 两个产品。支持 `--products claude,codex`。子命令包括 `leave`、`arrive`、`check`、`handoff`（旧版兼容）等。

前身 `claude-sync-doctor` 的早期 release（仅 Claude Desktop / Claude Code 单产品）见 Factory 的 `archives/claude-sync-doctor/`，最早 2026-05-05。
