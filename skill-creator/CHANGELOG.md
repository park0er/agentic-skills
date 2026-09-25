# skill-creator CHANGELOG

## 2026-09-21 — require-dedicated-rollica-worktree

- Rollica 仓库 Skill 同步禁止在当前会话原 checkout 中直接修改。
- 一批同步只允许创建或复用一个专用临时 worktree，禁止按 Skill、Agent 或会话重复 checkout。
- commit 后必须确认 worktree 干净且分支保留 commit，再立即移除 worktree 并清理元数据。

## 2026-09-21 — add-rollica-repository-target

- 将 Rollica 仓库 `.agents/skills/` 纳入指定共享 Skill 的第四发布目标。
- 要求先核对仓库 remote 和脏状态，再同步完整目录、验证并创建仓库 checkpoint commit。
- 明确 Factory 仍是编辑真源，发布脚本不会猜 checkout、自动 push、开 PR、合并或部署。

## 2026-08-30 — adopt-skill-factory-workflow

- 将现有安装副本纳入 Skill Factory，Factory 成为本地开发和发布真源。
- 明确本地 skill 必须更新 CHANGELOG、先 dry-run、再发布到全部 Agent 安装目标。
- 修正通用“不要创建 CHANGELOG”和本地 Factory 强制要求之间的冲突。
