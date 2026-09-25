# rollie-data-dev CHANGELOG

## 2026-06-16 — initial-release

- 新增 rollie-data 开发发布专用 skill
- 一键发布脚本 publish.sh：精准复制到 Factory + release.sh 发布 + git 同步
- Git 工作流：开发分支改动 → 审阅 → 合并 develop，不自动 push develop
- 配置文件管理：首次询问开发分支名，保存到 .dev-config
- 精准复制：排除 state/cookies、__pycache__、.DS_Store 等敏感/临时文件
