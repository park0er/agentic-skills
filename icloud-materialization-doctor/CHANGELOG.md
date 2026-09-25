# icloud-materialization-doctor CHANGELOG

> Skill 用途：诊断 macOS iCloud Drive 双向（下载侧 dataless + 上传侧 stuck）的同步卡死。
> 当前安装版可在 `~/.claude/skills/icloud-materialization-doctor/` 和 `~/.agents/skills/icloud-materialization-doctor/` 找到。
> 历史 archive 在 Factory 的 `archives/icloud-materialization-doctor/<ts>-<label>/`。

---

## 2026-05-16 — fix-description-length

修 Codex 启动时报错 `invalid description: exceeds maximum length of 1024 characters`（实测 1532 字符）。

- 重写 description 1532 → ~553 字符
- 从 `description: >` 多行 block scalar 改回 plain scalar 单行
- 按 superpowers:writing-skills CSO 原则：保留双向 stuck 的核心症状和 trigger 关键词（`sig:<file-pending>`, `brctl quota` hangs, dataless 等），删掉子命令枚举（`check` / `fix` / `upload-check` / `housekeeping-suggest`）——这些细节本来就该读 SKILL.md 正文
- frontmatter 总字节 1675 → 623
- 同期 agent-sync-doctor / mify-model-gateway 也做了类似修复

---

## 2026-05-16 — add-changelog-md

合规性 release（无功能改动）。

- 新增本文件 `CHANGELOG.md`，按 FACTORY.md "CHANGELOG 强制要求"段格式约定整理历史 release
- 顺手清掉 `scripts/__pycache__/` 噪音（不影响功能）
- 此前的 release 历史（追溯）见下方各条目

---

## 2026-05-14 — add-upload-side-diagnostics

v2 大版本：从单纯的"download-side dataless 检测"扩展为"双向卡死诊断"。

- **新子命令 `upload-check`**：诊断"文件存在本地但传不上 iCloud"的 stuck 上传
  - 解析 `brctl status` 输出找 `sig:<file-pending>` + `[active]` 但 stuck 的会话
  - 加 `brctl quota` hang 检测（>15s 不返回视作 hang，降级路径）
  - sandbox-aware：sandboxed 进程跑 brctl 会失败，自动降级到 filesystem upload-pressure heuristic
  - **关键警告**：multi-machine 时 stuck 现象的"始作俑者"经常不是当前 Mac，要去**写文件那台**机器查
- **新子命令 `housekeeping-suggest`**：dry-run 默认，扫 build artifact 目录（`node_modules` / `target` / `__pycache__`等）建议清理以减小 sync 队列压力。**默认不动**用户对话历史（Codex sessions / Claude project history）
- SKILL.md 加了 multi-machine pitfall 段 + correlation-not-causation 段：明确声明"做了 X 不等于修好 Y"
- **不破坏 v1 contract**：`check --json` schema 不变（schemaVersion=1），agent-sync-doctor 调用兼容

archive: `20260514-194240-add-upload-side-diagnostics`

---

## 2026-05-14 — pre-git-removal-baseline

非功能性 release：删除 `Skill_Factory/.git/` 之前的基线快照。Factory 从此切换到 archive-based versioning（详见 `FACTORY.md`）。代码本身没变。

archive: `20260514-032752-pre-git-removal-baseline`

---

## 2026-05-13 — fix-argparse-paths-after-subcmd

v1.1 bugfix：修 argparse 在子命令后处理 `--paths` 多值参数的 bug。

archive: `20260513-231954-fix-argparse-paths-after-subcmd`

---

## 2026-05-13 — detect-file-provider-dataless（v1 initial release）

初版。专门处理 macOS 12+ File Provider 下的 "dataless" 文件——表面看 100%
synced（Finder 显示正确大小、`ls` 正常列出、无 `.icloud` placeholder），
但本地物理 0 字节（`st_size > 0 && st_blocks == 0`）。

- 子命令 `check`：dry-run 报告，给 agent-sync-doctor 当 readiness gate
- 子命令 `fix`：stat-walk nudge → optional `--force-read` 主动 cat → daemon-kick 升级提示
- **诊断对象**：`bird` / `fileproviderd` 误以为已 materialize 的文件，传统 placeholder check
  抓不住的盲区
- **agent-sync-doctor 集成**：通过 subprocess `python3 <this>.py check --json` 调用，
  schemaVersion=1，顶层 `summary.datalessCount`、`summary.ready`、`paths[].dataless_samples[]`

archive: `20260513-231838-detect-file-provider-dataless`

### 历史背景（保留作教训）

2026-05-13 晚发生过一次本 skill 的 Python 脚本因 iCloud + git corruption 丢失的事件
（详见 `../agent-sync-doctor/ISSUES-2026-05-13-codex-data-loss.md`）。当时一度只剩
SKILL.md。后续从其他 Mac / iCloud Recently Deleted 等位置恢复了脚本。**这就是为什么
Factory 现在不放在 git 里、靠 `archives/` 快照做版本管理**（FACTORY.md 详细说明）。
