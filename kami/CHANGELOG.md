# kami CHANGELOG

## 2026-05-17 — initial-install-from-upstream

- 首次纳入 Skill Factory 分发，源仓库 `https://github.com/tw93/Kami`（git HEAD 取自 2026-05-17 浅克隆）。
- 上游用途：用 WeasyPrint 把 Markdown 排版成印刷级 PDF（One-Pager / Long Doc / Letter / Portfolio / Resume / Slides / Equity Report / Changelog 八种文档形态），以及 14 种结构化 diagram 作为 long-doc 内嵌组件（架构图 / 流程图 / 象限 / 状态机 / K 线 / 瀑布图等）。米黄信笺底 + 墨蓝衬线主调。
- 命名说明：上游 GitHub 仓库名是 `Kami`（首字母大写），但 SKILL.md 的 frontmatter `name: kami` 走小写，Skill Factory / Claude Code / Codex 三处的目录名统一用 `kami` 与 frontmatter 对齐。
- 体积裁剪：剔除 `dist/`（12MB 的项目自身 release 压缩包）、`index*.html`、`styles.css`、`vercel.json`、`robots.txt`、`sitemap.xml` 等纯属仓库 marketing landing page 的文件；保留 `assets/`（55MB）整包，因为 SKILL.md 的 diagrams 决策表和 fonts（含 TsangerJinKai02 / Charter / YuMincho）会按相对路径引用 `assets/diagrams/*.html`、`assets/templates/`、`assets/fonts/`。最终安装体积 55MB。
- 安全审计：`scripts/build.py`、`scripts/draft-release-notes.py` 均使用 list-arg `subprocess`，无 shell 注入；只有可选的 `~/.config/kami/brand.md` 读取（XDG 标准位置，opt-in），无凭据外传。
- 兄弟 skill 提示：上游说 Kami 是 "Kaku · Waza · Kami" 三件套之一，对应不同仓库；本次只装 Kami。
- 已知风险 / 迁移指引：要做最佳排版需要本机有 WeasyPrint（`pip install weasyprint`）和上述字体；缺时降级为 PNG 截图风格但仍可跑。
