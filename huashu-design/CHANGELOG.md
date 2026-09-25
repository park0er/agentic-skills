# huashu-design CHANGELOG

## 2026-05-17 — codex-skill-md-desc-trim

- 把 `SKILL.md` frontmatter 的 `description` 从 1079 unicode chars 压到 735 chars，让 Codex 的 SKILL.md 校验通过（上限 1024）。Claude Code 一直能读，是 Codex 这边新加的硬限。
- 信息保真：触发词全集保留（仅去掉少量近义词）；主干能力保留所有 pipeline 节点（Junior Designer 工作流、反 AI slop、Tweaks、Speaker Notes、Starter Components、App 原型守则、视频导出、带解说长动画 pipeline）；fallback 模式与 5 维度评审保留。
- 没有改 SKILL.md 正文/scripts/templates，只动了 frontmatter 一行 description。
- 关联工单：`PAR-167 codex skill 格式适配`。

## 2026-05-17 — initial-install-from-upstream

- 首次纳入 Skill Factory 分发，源仓库 `https://github.com/alchaincyf/huashu-design`（git HEAD 取自 2026-05-17 浅克隆），32MB 全量保留。
- 上游用途：用 HTML 做高保真原型、交互 Demo、幻灯片、动画、设计变体探索的一体化设计 skill。包含 5 流派 × 20 种设计哲学的方向顾问、24 个预制 showcase、Tweaks 变体切换、Speaker Notes、App 原型守则、Playwright 验证、HTML 动画→MP4/GIF 视频导出（25fps 基础 + 60fps 插帧 + palette GIF + 6 首场景化 BGM + 自动 fade）、带解说的长动画 pipeline（豆包 TTS + timeline.json + NarrationStage）。
- 安全审计：`scripts/narrate-pipeline.mjs` / `scripts/tts-doubao.mjs` / `scripts/render-video.js` 均使用 `execFileSync` / `spawnSync` 等 list-arg API，无 shell 注入；`Buffer.from(json.data, 'base64')` 是 TTS API 的标准音频解码而非可疑 payload；未发现凭据外传 / 提权 / 自动 hook。
- 依赖说明：完整动画→视频 pipeline 需要本机有 `ffmpeg` + Playwright（首次 `playwright install chromium`）；TTS 需要豆包 API key（按需配置环境变量，本次安装不预置）；不跑视频 pipeline 时上述都可省。
- 已知风险 / 迁移指引：上游 README 推荐通过 `npx skills add alchaincyf/huashu-design` 安装，但本工作流改走 Skill Factory 以保证 Claude Code 与 Codex 看到同一份 skill；后续上游升级请按 `release.sh huashu-design upstream-sync-<commit>` 模式更新，不要在已安装位置直改。
