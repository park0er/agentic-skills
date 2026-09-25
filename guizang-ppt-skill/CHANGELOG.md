# guizang-ppt-skill CHANGELOG

## 2026-05-17 — initial-install-from-upstream

- 首次纳入 Skill Factory 分发，源仓库 `https://github.com/op7418/guizang-ppt-skill`（git HEAD 取自 2026-05-17 浅克隆）。
- 上游用途：生成单 HTML 横向翻页 PPT，提供 Style A（电子杂志 + 电子墨水）与 Style B（瑞士国际主义）两套视觉系统，配 `assets/template.html` / `assets/template-swiss.html` 与 `references/` 下的主题色和布局规范。
- 安全审计：未发现 `os.system` / `eval(remote)` / `curl|sh` / 提权或混淆路径；脚本均使用 list-arg `subprocess`，依赖一份本地 `motion.min.js`（jsDelivr/Rollup 标准产物，签名正常）。
- 本次未对上游做任何修改，与 op7418 的 main 分支 1:1 一致；后续如需修改请只在 Factory 的 `skills/guizang-ppt-skill/` 下改动并重 release。
- 已知风险 / 迁移指引：暂无。后续若上游升级，按 `release.sh guizang-ppt-skill upstream-sync-<commit>` 模式更新。
