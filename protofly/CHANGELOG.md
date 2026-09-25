# protofly CHANGELOG

## 2026-05-18 — default-public

- **行为变更（默认翻转）**：`upload.py` 不带 visibility flag 时，**默认就 publish + `set_visibility public`**。之前默认是 draft（owner-only preview），需要显式 `--publish` 才发布、`--public` 才公开。
- 新增互斥可见性开关：
  - `--private` → publish 但保持 private（仅 protofly 控制台授权过的用户能看）
  - `--draft` → 不 publish，资源停在草稿，仅 owner 可通过 preview 链接预览
  - 不传 → public（新默认）
- 旧 flag `--public` 和 `--publish` 保留为新默认的别名（no-op），不会报错，老调用不会断。
- SKILL.md 同步更新：触发清单、Step 2/3/4、迭代示例、"常见坑 #3"、输出契约都改为公开优先的语义。
- 动机：用户主用例是"发给同事看一眼"，private 默认要求每个人都去 protofly 控制台单独加授权，摩擦太大；本身也不会泄露到公网（protofly 是小米内网域名）。需要授权清单的场景显式走 `--private` 即可。

## 2026-05-18 — initial-release

- 首版发布。包含：
  - `SKILL.md`：在什么场景该被触发（HTML 内网分享）、token 一键安装协议、5 步标准工作流（status → upload → publish → set_visibility → list/get/iterate）、CLI 命令对照表。
  - `scripts/install_token.py`：从 stdin 读 JWT，校验格式 + exp，写入 `~/.mcporter/mcporter.json`，跑 `list_resources` 实测。
  - `scripts/upload.py`：包装 `create_resource` 走 `--args <json>`，绕过 shell 长 base64 截断 bug；`--publish` 链上 publish_resource、`--public` 加 set_visibility。
  - `scripts/status.py`：健康检查（配置存在性、token 过期、可达性）。
  - `references/api.md`：5 个 MCP 工具的完整 schema + 返回示例 + 已知不一致（`visibility` 字段在 set_ vs get_ 之间是 string/int 两种类型）。
- 触发覆盖：proto-fly / protofly / mitvos / 内网分享 / 内部 demo / "发给同事看"等关键词，以及 tariq-html / kami / deckify / frontend-design / huashu-design / guizang-ppt-skill 等 HTML 输出 skill 后立刻要分享的衔接场景。
- 安全：token 只写入 `~/.mcporter/mcporter.json`，禁止落到 skill 目录、源码、或对话日志。`install_token.py` 用 stdin 输入避开 shell 历史。
