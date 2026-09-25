# beautiful-feishu-whiteboard CHANGELOG

## 2026-09-24 — import-upstream-1.1.1

- 从 GitHub [`zarazhangrui/beautiful-feishu-whiteboard`](https://github.com/zarazhangrui/beautiful-feishu-whiteboard) 导入为本机 Skill Factory skill（upstream commit `6989843`，version 1.1.1）。
- 内容与上游一致：35 个配色风格模板（`templates/`）+ `CATALOG.md` / `RULES.md` + 风格预览图（`assets/styles/`）+ `scripts/preflight.sh` + README / README.zh / LICENSE。
- 唯一适配：SKILL.md frontmatter 的 `description` 由 YAML 折叠多行（`>`）改为单行标量，满足 Factory 的元数据校验；未改动正文与任何其他文件。
- 运行时依赖：Node ≥ 20；`lark-cli`（npm `@larksuite/cli`，需认证）；`@larksuite/whiteboard-cli`（经 npx 自动下载）。
