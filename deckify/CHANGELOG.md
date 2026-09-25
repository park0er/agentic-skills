# deckify CHANGELOG

## 2026-05-17 — add-xiaomi-factory-bundle

- 在 `references/presets/xiaomi/` 下新增「小米品牌预设包」，整套挂回原版 deckify 树而非新建独立 skill：
  - `xiaomi-PPT-Design-System.md`（70 KB DS 主合同，中文版）
  - `xiaomi-deck.html`（115 KB 9-slide 验证 deck）
  - `source/{brand.json, decisions.json, pages.txt}`（一次完整 Phase 1–2 recon 快照）
  - `source/assets/{logo.svg, logo.png, logo.dataurl, logo.embed.html, logo.report.json}`（5 种 logo 形态）
  - `README.md`（调用说明 + 锁死的小米品牌值清单）
- 触发场景：用户说"做一份小米风 deck / 按 mi.com 调性出 PPT / 用 deckify 出厂调好的小米这套来做"——builder agent 直接读 `references/presets/xiaomi/xiaomi-PPT-Design-System.md` 当合同，**跳过** Phase 1（recon）/ Phase 2（confirm）/ Phase 3（DS 写作），直接进 Phase 4 / 5 / 6 跑 deck。
- 锁死的品牌值：`#FF6700` 小米橙、`#191919` ink、`#FFFFFF` paper、`#000000` stage、`#1D4ED8` link；MiSans Latin via 小米官方 CDN；slide-emphasis Type A/F/H/J。
- 上游来源：deckify 自己一次跑在 `https://www.mi.com/global/` 上的完整产物（覆盖 7 个代表性子页），不是 hand-craft。需要刷新就重跑 pipeline，不要手编。
- 授权延续上游 PolyForm Noncommercial 1.0.0，加上小米 logo / 品牌色作为 Xiaomi 财产——**仅限内部使用**，不能打包进对外收费产品。

## 2026-05-17 — initial-install-from-upstream

- 首次纳入 Skill Factory 分发，源仓库 `https://github.com/seacen/deckify`（git HEAD 取自 2026-05-17 浅克隆，仅取 `skills/deckify/` 子目录，剔除 `tools/phase-a/`、`decks/`、`assets/` 等仓库级开发产物以保持安装体积干净，408K 全量）。
- 上游用途：从一个参考品牌站点 URL 反推出可工程化复用的 `Design System.md` + 9 页 HTML 示例 deck，内置 11 项技术自检 + 6 项视觉自评，依赖外部 CLI `agent-browser`（Vercel Labs 出品，独立二进制）和 `python3` 标准库。
- 授权：上游为 **PolyForm Noncommercial 1.0.0**，仅限非商用。本次安装用于公司内部分享 / 个人产出，符合授权范围；如需对外打包售卖必须重新评估。
- 安全审计：脚本均使用 list-arg `subprocess`，无 shell 注入；`agent-browser eval` 是该 CLI 的合法子命令（在受控 Headless Chromium 内跑 JS），不是 Python `eval()`；未发现凭据外传 / 提权 / 自动 hook。
- 已知风险 / 迁移指引：本机如果尚未安装 `agent-browser` CLI，第一次跑 deckify 时它会引导走 `scripts/setup.py` 安装；走通后 `scripts/init_workspace.py` 会在调用目录下生成 workspace（不是 skill 目录里）。后续上游升级请按 `release.sh deckify upstream-sync-<commit>` 模式更新。
