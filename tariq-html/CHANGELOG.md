# tariq-html CHANGELOG

## 2026-06-03 — images-must-be-inlined

**新增硬规则：所有图片必须内嵌成 base64 `data:` URI，禁止本地/远程路径外链。** 起因：一次实战中生成的页面用了 `<img src="本地目录/xxx.png">` 相对路径，在作者本机正常，但单文件发出去后图片全裂。validator 之前只拦 `http(s)` 远程图，本地相对路径能蒙混过关 —— 这违背了「单文件可独立渲染」这一格式的根本目的。

**What changed:**

- **`SKILL.md` Hard Rule #1** 重写为「Single file, fully self-contained」，点名最常见的破坏方式：残留 `<img src>` 相对路径。**Hard Rule #2** 补一句：raster 图片永不按路径引用，一律 base64 `data:` URI。
- **`SKILL.md` 新增小节 "Images must be inlined (no local or remote file refs)"** —— 讲清为什么不能外链、体积权衡（≤1500px / JPEG q≈82 / 单文件 <2 MB）、给出 Python+Pillow 压缩内嵌配方、并强调矢量内容用 inline `<svg>` 而非图片。
- **`SKILL.md` Common mistakes** 置顶新增「Don't leave images as local file paths」。
- **`scripts/validate.mjs` 新增检查** "All <img> inlined as data: URI (no local/remote file refs)"：扫描所有 `<img src>`，任何非 `data:` 开头的（含本地相对路径与 http 远程）即判 FAIL；inline `<svg>`（无 src）不受影响。header 注释同步加 rule 2b。

**迁移指引：** 旧产物若用相对路径图片，跑一遍 SKILL.md 里的压缩内嵌脚本，把每个 `src` 替换成 `data:` URI 即可通过新校验。需要快速本地迭代时可保留一份相对路径副本，但交付给用户分享的必须是内嵌版。

## 2026-05-18 — font-strategy-default-bc

**The "zero web fonts" hard rule is retired.** CN serif quality on most user machines was unacceptable — Source Han Serif SC isn't preinstalled on macOS, so the stack fell through to Songti SC, which renders dense and uneven. Parker's PAR-170 review surfaced this on a 70 KB single-file deconstruction page, then chose Mode B / Mode C as the new default. This release flips the skill to match.

**What changed:**

- **`SKILL.md` Hard Rule #2** rewritten. Before: "Zero external requests — no Google Fonts, no Tailwind CDN, no CDN icons, no remote images." Now: "Typography-only network dependency allowed — the page may load Noto Serif SC + Noto Sans SC from Google Fonts (Mode B, default), or inline them as base64 woff2 subset (Mode C, archive). Everything else (Tailwind, CDN icons, remote images, jsdelivr, unpkg, cdnjs, arbitrary fonts) is still banned."
- **`SKILL.md` new section "Font strategy: Mode B by default, Mode C for permanence"** — codifies the trade-off table, the decision rule the LLM applies before generating, and how to swap between modes inside a template.
- **All 8 templates** (`comparison`, `decision-plan`, `deck`, `design-system`, `diagram`, `exploration`, `research-explainer`, `status-report`) now ship Mode B `<link>` block in `<head>` (active by default) plus a commented-out Mode C `<style>` block immediately below as the offline-permanent alternative. Swap = comment one out, uncomment the other; replace `PASTE_BASE64_HERE` markers with real woff2 subset.
- **`--font-serif` / `--serif`** stacks now lead with `"Noto Serif SC"` (the actually-loaded family); **`--font-sans` / `--sans`** stacks lead with `"Noto Sans SC"`. The full kami-aligned CN fallback chain stays intact behind the loaded family for offline degradation.
- **`scripts/validate.mjs`** updated:
  - Removed `fonts.googleapis.com|fonts.gstatic.com` from the external-offenders list (now sanctioned for typography only — strips them out before scanning so generic remote-`<link>` check stays meaningful).
  - "Zero external requests" check renamed to "No arbitrary CDNs (Google Fonts permitted; data:font base64 permitted)".
  - "System font stack present" check renamed to "CJK-aware font stack present"; pattern broadened to also accept `"Noto Sans SC" / "Noto Serif SC"`.
  - **New positive check:** "Font Mode B (Google Fonts) or Mode C (base64 inline) wired up" — fails if the page has neither the Noto Serif/Sans SC `<link>` (Mode B) nor a `@font-face` block referencing `"Noto Serif/Sans SC"` with `data:font/woff2;base64,` (Mode C). Bare-system fallback is no longer a passing state.
- **`references/design-tokens.md`** — "What we deliberately do NOT do" section flipped into "Font strategy: Mode B by default, Mode C for permanence", with paste-ready Mode B (3 `<link>` lines) and Mode C (`@font-face` + `pyftsubset` recipe) snippets. CJK-stacks section updated to explain why the loaded family now leads each stack.
- **Template top-of-file comment in `comparison.html`** — old "zero CDNs, system fonts" line replaced with the correct policy summary.

**What we deliberately did NOT do:**
- Did not bundle font files in the skill repo (no `assets/fonts/*.woff2`). Mode C base64 is generated on demand from the user's own subset; the skill ships the recipe, not 300 KB of woff2 bytes.
- Did not load Tariq's full Inter or Charter via Google Fonts. Sans Latin still resolves via Apple/Linux system fonts; only the CN-coverage fonts (Noto Serif SC + Noto Sans SC) are loaded.
- Did not add a Mode A fallback (system Songti SC). The whole point of this release is that bare-system was the bug.

**Reason:** Parker's PAR-170 review — "我们默认 B 和 C 吧。另外记得把这个 PAR-165 对应的那个 skill 也更新成我要的方案 B 或 C". Mode A (no web fonts at all) was the previous default and was producing visibly ugly CN serif. Mode B is the lighter, daily-use default; Mode C is the offline / archive / handoff-permanence alternative. The LLM picks per output based on intent (`归档 / 离线 / 永久 / PDF` → C, otherwise B).

**Inheriting from kami without copying its identity:** kami ships TsangerJinKai TTFs inside `assets/fonts/`; we don't. Tariq's identity is "one HTML file you can email anyone" — Mode B respects that (one file, optional network) and Mode C strengthens it (one file, fully offline). Neither breaks the email-it test.

## 2026-05-17 — codex-skill-md-yaml-fix

- 修掉 `SKILL.md` frontmatter 的 YAML 解析失败（Codex 报 `mapping values are not allowed in this context at line 2 column 606`）。根因：description 是 unquoted plain scalar，里面出现了 `Strong default: 方案对比`——YAML 1.2 spec 不允许 plain scalar 内含 `: ` 序列（会被解释成嵌套 mapping），Codex 的 parser 严格执行，Claude Code 的 parser 早先放过了。
- 修法：把那处冒号换成破折号 → `Strong default — 方案对比`。语义零改动，触发词、Hard rules、模板列表全部不动。
- 关联工单：`PAR-167 codex skill 格式适配`。

## 2026-05-17 — cjk-font-stacks-kami-aligned

**What changed:** all 8 templates now ship CJK-safe font stacks, modelled on the `kami` skill's typography contract (Parker's call: "该用什么中文字体，参考一下 kami 那个 skill"). Concretely:

- **Unified font tokens.** Every Swiss template now defines `--font-sans / --font-serif / --font-mono` in its own `:root` block (separate from the palette `:root` so Swiss↔warm toggle leaves type alone). The Tariq warm template's existing `--serif / --sans / --mono` were upgraded in place. Both naming schemes coexist by template, but the *stacks themselves are identical*.
- **Sans stack:** `"Helvetica Neue", "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Source Han Sans SC", "Noto Sans CJK SC", sans-serif`. Latin first (English text uses Helvetica/Inter); PingFang before YaHei (Apple priority); Source Han + Noto Sans CJK as Linux/cross-platform fallbacks.
- **Serif stack:** `Charter, "Iowan Old Style", Georgia, "Times New Roman", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong", serif`. Charter is Apple's Editorial system serif (kami's EN choice); Songti SC / STSong are the matching macOS / Windows CN serifs after the open-source Source Han Serif fallback.
- **Mono stack with CJK fallback:** `ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, "PingFang SC", "Source Han Sans SC", monospace`. The kami lesson here is critical — pure mono stacks (`Menlo, Consolas, monospace`) render `// 这是中文注释` as tofu boxes on systems without monospace CJK glyph synthesis. We accept the slight kerning quirk (CN glyphs aren't strictly monospaced) to keep CN comments legible.
- **CN density compensation rule** added to every template: `:lang(zh) body, html[lang^="zh"] body { letter-spacing: 0.01em; }`. Per kami's design.md: serif-class CN fonts read denser than Latin at the same size; a hair of letter-spacing opens up paragraphs without breaking rhythm. Scoped to `:lang(zh)` so EN-only pages aren't affected.
- **Validator strengthened:** new check `Mono font-family declarations include a CJK fallback` greps every `font-family: ...monospace;` rule in the file and fails if none of `PingFang SC / Source Han Sans SC / Source Han Serif SC / Microsoft YaHei / Noto Sans CJK / Noto Serif CJK / Songti SC / STSong / Hiragino` appears. Caught and fixed a real miss in `design-system.html` (two leftover single-quoted `font-family:'SF Mono',Menlo,monospace;` inline styles).
- **References updated:**
  - `references/design-tokens.md` — new section "CJK-safe font stacks (kami-aligned)" with per-line rationale, the deliberate non-decisions (no bundled fonts, no CDN fonts) and override guidance.
  - `SKILL.md` Hard-rule #4 rewritten to point at the new section and explain why mono needs CJK fallback.

**What we deliberately did NOT do:**
- Did **not** bundle font files (no `assets/fonts/TsangerJinKai*.ttf` like kami) — Tariq's contract is `single file, zero CDNs, zero external requests`. Bundling would break the validator and the skill's identity as "one HTML file you can email anyone".
- Did **not** add `@font-face` with CDN fallback (kami's `cdn.jsdelivr.net/gh/tw93/Kami@...` pattern). Same reason.
- Did **not** introduce a third palette. Palette is colors only; type stays unified.

**Reason:** Parker's review — "该用什么中文字体，我建议你参考一下 kami 那个 skill". Read `OiAnthony/.agents/skills/kami/` (templates/*.html, references/design.md), saw kami's three rules (Latin-first stack with full CJK fallback chain; mono stack must include CJK fallback; serif-led pages need a CN serif chain ending in Songti SC/STSong), applied them across all 8 templates, codified mono-CJK as a validator hard-fail.

**Inheriting from kami without copying its identity:** kami is serif-led editorial typography; tariq-html is sans-led Swiss decision-design + serif-led warm narrative. We borrowed kami's *fallback discipline*, not its *visual register*.

## 2026-05-17 — full-template-interactivity-parity-and-warm-default

**Audit + fix:** every template now actually ships the interaction it promised in `scenarios.md`, not just its visual style. Previous release only covered diagram. Per-template changes:

- **comparison.html** — decision matrix is now **sortable** (click any header to sort; cells carry `data-v` so visual decorations don't block sorting). Sticky anchor nav has **scroll-spy** that highlights the current section.
- **exploration.html** — direction cards and trade-off-table columns share a `data-d` attribute; hovering either side **cross-highlights** the other. Neutrality preserved (no "推荐" badge anywhere).
- **decision-plan.html** — system-diagram nodes are now **clickable** with a sticky right detail panel (`window.SYS` dict, `#dp-title/meta/body`). Open-questions list is **toggleable** (click to mark resolved → strikethrough + green fill).
- **research-explainer.html** — sticky TOC has **scroll-spy** highlighting the current section.
- **status-report.html** — items list gets **filter pills** (shipped / slipped / blocked); bar chart gets **hover tooltip** on every `<rect>`; incident-timeline variant is now a working component (still commented for activation, no longer a fake example).
- **deck.html** — added **scroll listener** so trackpad/wheel scrolling syncs the slide-index back to arrow-key state (previously desynced).
- **design-system.html** — click-to-copy now also covers **type rows** (CSS shorthand) and **spacing chips** (`--space-N` token), not just color swatches. Removed the fake "Hover" button instances and replaced with a single working button + a callout that real `:hover/:focus/:disabled` is live on the demo.
- **diagram.html** — already shipped click-to-detail in the previous release; no logic changes, just gained the palette-swap header to match the rest of the suite.

**Palette default policy flipped from "default Swiss" to "pick by intent, prefer warm-paper when ambiguous":**

- Every template now carries **both `:root` blocks** at the top — one active, one in an HTML comment. Swap = toggle a comment.
- `SKILL.md` introduces a routing table: Swiss for decision/data/engineering content; **Tariq warm-paper for editorial / concept / narrative content** (= the actual look of thariqs.github.io).
- `references/design-tokens.md` and `references/scenarios.md` updated in lockstep — each branch now has a default-palette column.
- Tie-breaker rule: when uncertain, prefer warm-paper. Old "default Swiss" was making everything read as engineering-decision register even when it wasn't.

**Reason:** Parker's review — "好多好像没有抓到人家 tariq 的精髓 … 别都只是扒了个样子，每个都过一遍" + "能不能把默认的效果弄成人家 Tariq 那种'暖纸'的感觉？或者加一个功能，让大模型自己判断". Both addressed: every template gained real interaction matching its scenarios.md promise; palette default flipped from blanket-Swiss to LLM-judges-by-intent with warm-paper as the ambiguous-case fallback.

**Housekeeping:** removed `templates/design-system 2.html` iCloud-sync duplicate (got `--delete`d on next rsync anyway, but cleaned up at source).

## 2026-05-16 — interactivity-contract

- **Diagram template rebuilt** to ship Tariq's canonical click-to-detail interaction (§13 flowchart-diagram). Every `<g class="node" data-k="...">` now reveals a sticky right-panel detail (title / meta / body / code). Pre-activates the first node on load so the panel is never empty. Adds keyboard support (Tab/Enter) — strict improvement over Tariq's own demo.
- **`SKILL.md`** gains a "Interactivity is part of the contract" section listing per-branch interaction requirements. Static templates that lack required interaction are flagged as "阉割版" (castrated version) of the pattern.
- **`references/scenarios.md`** — `07 · diagram` rewritten with full must-have interactivity checklist (clickable `<g>`, `pointer-events:none` text, flat DETAIL dict, sticky aside, pre-activated first node, `tabindex` for keyboard). Adds a cross-branch "Interactivity contract" table.
- Reason: Parker's review — "好多好像没有抓到人家 tariq 的精髓 … diagram 里面每一个节点都是在点击后能看到具体模块说明的". The previous static SVG diagram template was the most visible gap; this release closes it.

## 2026-05-16 — initial-release

- Initial release of `tariq-html` skill.
- Inspired by [Tariq Shihadah's HTML effectiveness page](https://thariqs.github.io/html-effectiveness/) (9 categories of "give me HTML, not markdown") and the Swiss-international visual system Rollie shipped on PAR-162.
- Router-style skill: `SKILL.md` decides scenario branch, `references/scenarios.md` documents 8 branches, `templates/*.html` provides paste-and-fill starts, `scripts/validate.mjs` enforces hard rules.
- Primary branch is **comparison** (方案对比) — the polished template that mirrors `ppt-tools-comparison.html` from PAR-162.
- Hard rules enforced: single file, zero external requests, system font stack, UTF-8, responsive.
- Defaults to Swiss palette (klein blue + lemon yellow + safety orange + ink black). Tariq's warm-paper palette available as alternate.
