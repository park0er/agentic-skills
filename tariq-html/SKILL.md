---
name: tariq-html
description: Generate single-file HTML artifacts (one .html, zero CDNs, system fonts) instead of dumping markdown. Use when the user wants visual impact for 方案对比 / option comparison, exploration & planning, decision plans, research explainers, status / incident reports, decks, diagrams, or design systems — anywhere reading a wall of markdown is "太痛苦了" and the content is spatial / decision-oriented. Triggers on 方案对比 / 选型对比 / 工具对比 / option comparison / decision matrix / 把这段做成 HTML / 这段读起来太累了能不能可视化 / Tariq HTML / unreasonable effectiveness of HTML / 帮我做个 HTML 网页 / one-pager / 内部分享 deck. Strong default — 方案对比 (the most-used branch). Inherits the Swiss-international visual system (klein blue / lemon yellow / safety orange / ink black) proven on PAR-162. Skip when the user explicitly wants markdown, a Word doc, a PDF, a PPTX, or a multi-file frontend project — this skill outputs ONE static HTML file.
---

# Tariq HTML Skill

A skill for turning content into one self-contained `.html` file the user actually wants to read, instead of a wall of markdown. Inspired by Tariq Shihadah's [The unreasonable effectiveness of HTML](https://thariqs.github.io/html-effectiveness/) and the Swiss-international visual system already proven on PAR-162.

## When to use

Trigger when **any** of these are true:

1. The user says some variant of "this is too hard to read", "做成 HTML", "可视化一下", "我想直接对比" — they want a spatial / scannable artifact, not prose.
2. The content is decision-shaped: comparing N options, picking one, reading a matrix, justifying a recommendation — the canonical 方案对比 case (Parker's #1 use case).
3. The content has structure that markdown flattens: side-by-side options, timelines, before/after, module graphs, status snapshots, design tokens.
4. The user references Tariq's page, "thariq HTML", or asks for a comparison page styled like the prior agent's PAR-162 output.

**Skip** when:
- The user wants a PDF / PPTX / Word doc (use Kami / guizang / huashu-design instead).
- The user wants a multi-file React/Vue project.
- The content is a one-line answer or a pure code change.

## What this skill outputs

**Always one self-contained `.html` file.** Hard rules — these are non-negotiable, the validation script enforces them:

1. **Single file, fully self-contained** — no separate CSS/JS/asset files, **and no external image files either**. The one `.html` must render completely when sent on its own (email / WeChat / 内网 link), with **zero** dependency on the author's local folder. This is the whole point of the format. The most common way to break it: leaving an `<img src="imgs/foo.png">` relative path in — it works on your machine, then renders as a broken-image icon the instant someone else opens the lone file. See "Images must be inlined" below.
2. **Typography-only network dependency allowed** — the page may load **Noto Serif SC + Noto Sans SC** from Google Fonts (Mode B, default), or inline them as base64 woff2 subset (Mode C, archive). Everything else (Tailwind, CDN icons, remote images, jsdelivr, unpkg, cdnjs, arbitrary fonts) is still banned. Raster images are **never** referenced by path (local or remote) — they are embedded as base64 `data:` URIs. See "Font strategy" and "Images must be inlined" below.
3. **Offline-aware**: in Mode B the page degrades to the system CN fallback when the user is offline (still readable, just less stylish); in Mode C it renders identically forever, no network. Both are acceptable defaults — A "no web fonts at all" mode (system Songti SC fallback) is no longer supported because CN serif quality is unacceptable on most machines.
4. **UTF-8** declared, **CJK-safe font stack** in every text-bearing rule. The skill defines `--font-sans / --font-serif / --font-mono` (or `--sans / --serif / --mono` in the warm template) once and references them everywhere — including `pre`, `code`, and SVG `<text>`. The serif/sans stacks now lead with `"Noto Serif SC"` / `"Noto Sans SC"` (the actually-loaded families); the mono stack ends with `"PingFang SC", "Source Han Sans SC"` to keep CN comments from rendering as tofu boxes. See `references/design-tokens.md` § "Font strategy: Mode B by default, Mode C for permanence" for the full rationale.
5. **Responsive**: works from a phone (~375px) up to a 1440px desktop.
6. **Information architecture serves the decision**, not the reader's patience. The user is here to pick / scan / decide, not to read.

If the user asks to break any of these rules (e.g., "use Tailwind"), push back once and explain — the whole point of this format is portability and scannability.

## Font strategy: Mode B by default, Mode C for permanence

CN serif typography on most user machines defaults to system Songti SC, which renders dense and uneven (Parker's PAR-170 review: "中文字体很丑"). The skill ships two production-grade modes; **never default to bare-system fallback (Mode A — abandoned)**.

| Mode | What it does | Trade-off | When to pick |
|---|---|---|---|
| **B · Google Fonts (default)** | 3 `<link>` lines in `<head>` load Noto Serif SC + Noto Sans SC weights 400/500/700 | Sacrifices "zero CDN" purity for typographic fidelity. ~150–250 KB woff2 over the wire on first paint, then HTTP-cached. Degrades to system Songti SC if offline. | Daily iteration · sharing internally · local browsing · the common case. |
| **C · Base64 inline** | Replace the 3 `<link>` lines with a `<style>` block containing `@font-face` rules whose `src` is a `data:font/woff2;base64,...` URL holding a subset (GB2312/GB18030-Plus, ~3500 chars × 3 weights) | File grows ~150–300 KB. Single static HTML works offline forever. | PDF-export · archive · handoff to non-technical user · "this needs to render the same in 5 years" · 国内裸网/防火墙环境. |

**Decision rule the LLM applies before generating:**
- If the user said "归档", "离线", "永久保留", "导出 PDF", "发给客户", or the output is high-stakes one-shot → **Mode C**.
- Otherwise → **Mode B**.

Each `templates/<branch>.html` ships Mode B active in `<head>` and Mode C as a commented-out alternative right below it. To swap: comment out the 3 `<link>` lines, uncomment the `<style>` block, and paste real base64 (see `references/design-tokens.md` for the `pyftsubset` recipe).

## Images must be inlined (no local or remote file refs)

**Hard rule, validator-enforced.** Every raster image (screenshot, photo, diagram PNG/JPG) that appears in the page must be embedded as a base64 `data:` URI. A relative path like `<img src="imgs/dashboard.png">` is **forbidden** even though it renders fine on your own machine — the moment the single `.html` is sent on its own (the entire purpose of this format), that path resolves to nothing and the reader sees a broken-image icon. There is no "ship the HTML next to a folder" mode; the folder will get lost.

**The trade-off you must manage: file size.** Naively base64-ing raw screenshots bloats the file fast (a handful of full-res PNGs → 5–10 MB, which chokes email and some 内网 viewers). So **compress before embedding**:

- Downscale to **≤ 1500px wide** (dashboard text stays legible; nobody zooms past that on screen).
- Re-encode as **JPEG quality ≈ 82** (screenshots tolerate it; flatten transparency onto white). Keep PNG only for crisp line-art / true screenshots of text where JPEG artifacts hurt.
- Target **< 2 MB total** for the finished single file. If real photos push past that, tell the user the size and offer a lossless variant on request.

Recipe (Python + Pillow) — compress each referenced image and rewrite every `src="…path…"` to a `data:` URI in place:

```python
import base64, io, re, os
from PIL import Image

html = open("page.html", encoding="utf-8").read()
srcs = sorted(set(re.findall(r'src="([^"]+\.(?:png|jpe?g))"', html, re.I)))  # local refs

def encode(path, max_w=1500, q=82):
    im = Image.open(path)
    im = im.convert("RGB") if im.mode not in ("RGB",) else im   # flatten alpha → white
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

for s in srcs:
    if os.path.exists(s):
        html = html.replace('src="%s"' % s, 'src="%s"' % encode(s))

open("page.html", "w", encoding="utf-8").write(html)
```

**Vector content (flowcharts, diagrams, icons) should be inline `<svg>`, not images** — it has no `src`, scales crisply, costs almost nothing, and is the diagram branch's default. Reserve base64 for genuine raster (screenshots, photos).

It is fine to keep a second relative-path copy of the HTML for fast local iteration, but the **deliverable** the user shares must be the inlined one. When in doubt, inline.

## How to invoke

The skill is a **router**, not a one-size template. The flow is:

1. **Identify scenario** from the user's request → pick a branch from `references/scenarios.md`.
2. **Read** `references/design-tokens.md` for the Swiss visual system (palette, typography, primitives).
3. **Start from** the matching template in `templates/<scenario>.html` — copy it, then fill in real content.
4. **Output** a single `.html`. Do not output markdown narration around it unless the user asked for an explanation.
5. **Validate** with `scripts/validate.mjs <output.html>` (or do the same checks by eye).

## Branch routing

Map the user's ask to one of these eight branches. When in doubt and the content compares 2+ options → **comparison**.

| Branch | When to pick | Template |
|---|---|---|
| **comparison** ⭐ (primary) | 方案对比, 选型对比, 工具对比, "我要直接对比这几个" | `templates/comparison.html` |
| **exploration** | "给我列三种思路", "fan out across N directions", side-by-side draft directions before any pick | `templates/exploration.html` |
| **decision-plan** | "出一份执行计划", "implementation plan", milestones + risks + mockups handoff | `templates/decision-plan.html` |
| **research-explainer** | "解释一下 X 是什么", "feature 怎么工作的", concept walkthrough with TL;DR + collapsibles | `templates/research-explainer.html` |
| **status-report** | "周报", "项目复盘", "事故报告", recurring docs that need a small chart | `templates/status-report.html` |
| **deck** | "做个 deck", "做个内部分享", arrow-key slides for a meeting | `templates/deck.html` |
| **diagram** | "画一下 pipeline", "module map", "flowchart", spatial illustrations | `templates/diagram.html` |
| **design-system** | "渲染一下我们的 tokens", "组件 contact sheet", "swatches" | `templates/design-system.html` |

The full taxonomy and decision rules are in `references/scenarios.md`.

## Visual system — pick palette by intent (no blanket default)

There is **no global default palette anymore**. Pick one *per output* based on what the page is actually for. Both palettes ship as ready-to-uncomment `:root` blocks at the top of every template — swap by toggling the comment.

**Two palettes:**

- **Swiss-international** — klein blue + lemon yellow + safety orange + ink black on warm off-white. Reads as data-dense, decision-oriented, confident. Proven on PAR-162.
- **Tariq warm-paper** — ivory + clay + oat + olive on warm off-white, serif H1, clay accent. Reads as editorial, literary, "agent-companion" — closer to the actual look of thariqs.github.io.

**Routing rule (LLM judges, applies before generation):**

| Page intent | Palette |
|---|---|
| Decision matrix / 选型对比 / 投票 / RFC handoff / pipeline diagram | **Swiss** |
| Status / weekly / incident / metrics-led report | **Swiss** |
| Boardroom deck / data-led pitch | **Swiss** |
| Concept explainer · "what is X" / research walkthrough / editorial deep-dive | **Tariq warm-paper** |
| Story-led retro / human-narrative postmortem | **Tariq warm-paper** |
| Editorial brainstorm / fan-out exploration where tone is reflective | **Tariq warm-paper** |
| Design-system / token catalog | **Either** — lean Tariq for editorial brand work, Swiss for engineering tokens |
| Talk-style deck / keynote pre-read | **Either** — Tariq if narrative, Swiss if structural |

**Tie-breaker when ambiguous**: prefer Tariq warm-paper. Swiss is the right call when the page is *built around data or a decision*; in everything else (most concept / explainer / story content), warm-paper is closer to the source aesthetic Parker is asking for.

**Don't mix palettes mid-document.** Pick one at the start, swap the `:root` block accordingly, and commit. The full token tables and per-palette typography rules live in `references/design-tokens.md`. Per-branch palette default ships in each `templates/<branch>.html` header comment.

## The 方案对比 / comparison branch (强化画面感)

This is Parker's #1 use case so it gets the most polish. The comparison template enforces a 5-section architecture that's already been validated:

1. **Hero + TL;DR** — one-line title with italic klein-blue emphasis + lemon-yellow callout box with the recommendation in inverse-marker.
2. **One-screen decision matrix** — sortable, horizontally scrollable, with inline mini-bars / score chips so the reader can rank options without reading prose.
3. **Tool cards** — N cards with filter pills on top (group by attribute), recommended option marked with klein-blue border + "推荐" angle badge.
4. **Methodology / context cards** — secondary tier on a muted background so it's clearly "read this if you want to, not required".
5. **Recommendation path** — numbered execution steps + safety-orange "避坑提醒" cards.

Top-level sticky anchor nav. Cards have `translateY(-2px)` + hard-edge `box-shadow: 6px 6px 0 var(--klein)` on hover (no blur — Swiss style is geometric).

`templates/comparison.html` already has all of this scaffolded. Fill it in.

## Output workflow

```bash
# 1. write the file
# (Claude Code or Codex calls Edit / Write — agent-side; not a CLI command)

# 2. validate it (from the skill's scripts dir, run via node)
node ~/.claude/skills/tariq-html/scripts/validate.mjs ./my-output.html

# 3. quick eye-check
open ./my-output.html
```

The validator checks: single file, zero `<link>` / `<script src>` to remote URLs, no `@import url(http`, system font stack present, UTF-8 declared, has at least one section, `<title>` set.

## Interactivity is part of the contract

Tariq's demos aren't decorative HTML — they're **navigable documents**. A static template that ships without the required interaction for its branch is a "阉割版" (castrated version) of the pattern, not a faithful one.

Every template now carries its required interaction inline (no extra deps, no CDNs). Per-branch contract — what the LLM must verify is still wired up after editing:

- **comparison** ★ — filter pills on tool cards · **sortable decision matrix** (click any header to sort, `data-v` carries the real value behind the visual cell) · scroll-spy on sticky anchor nav.
- **exploration** — equal-tier panels (no winner, no "推荐") · **cross-highlight**: hovering a direction card lights up its column in the trade-off table and vice versa, but never picks a winner.
- **decision-plan** — **clickable system-diagram** with sticky detail panel (Tariq §13 lite) · **toggleable open-questions list** (click to mark resolved).
- **research-explainer** — `<details>` accordion · tabbed code samples (CSS `:checked`) · **scroll-spy** on TOC · glossary card.
- **status-report** — **filter pills** (shipped / slipped / blocked) · **chart hover tooltip** showing actual numbers · live (commented-out but functional) incident-timeline variant.
- **deck** — arrow-key nav · slide counter · ESC index view · F-fullscreen · **idx-syncs-on-manual-scroll** so trackpad users don't desync.
- **diagram** ★ — every `<g class="node" data-k="...">` is clickable · sticky right-panel `#p-title` / `#p-meta` / `#p-body` (innerHTML) / `#p-code` (textContent) · pre-activate first node on load · keyboard support (Enter/Space).
- **design-system** — click-to-copy on color swatches (hex), type rows (CSS shorthand), and spacing chips (`--space-N` token) · real `:hover` / `:focus` / `:disabled` button states (no fake separate styled instances).

Pattern budget: roughly **20–60 lines of inline JS** per template covers all of the above. If you find yourself writing a framework, you've left the format. After editing a template, re-verify every bullet above for the branch you touched — replacing markup but losing the interactivity is the most common regression.

## Common mistakes to avoid

- **Don't leave images as local file paths.** `<img src="imgs/foo.png">` works on your machine and silently breaks for everyone you send the lone `.html` to. Inline every raster as a compressed base64 `data:` URI (≤1500px, JPEG q≈82, <2 MB total); use inline `<svg>` for diagrams. This is now validator-enforced. See "Images must be inlined".
- **Don't pull arbitrary CDNs.** Tailwind via CDN, jsdelivr, unpkg, cdnjs — all banned. The only sanctioned typography network dependency is `fonts.googleapis.com / fonts.gstatic.com` for Noto Serif SC + Noto Sans SC (Mode B); for everything else use inline data URIs or system stack.
- **Don't fall back to bare system Songti SC.** The old "no web fonts at all" stance produced visibly ugly CN serif on most user machines (Parker's PAR-170 incident). Mode B (Google Fonts) is now the default; Mode C (inline base64) is the offline-permanent alternative. Mode A (system-only) is no longer supported.
- **Don't write more than ~5 sections.** If the page has 8+ sections, the user will skim past 6 of them. Compress.
- **Don't ship static templates where the branch requires interaction.** See contract above. Static diagram is the most common bug.
- **Don't use blurry box-shadows for Swiss style.** Use hard-edge offset shadows (`6px 6px 0 var(--klein)`) — that's what makes it read as Swiss-grid, not as generic Material Design.
- **Don't center the body title.** Swiss style is left-aligned with strong baseline. The validator doesn't catch this; you have to.
- **Don't use horizontal rules `<hr>` between sections.** Use a 1px ink border at the bottom of each section. Cleaner.
- **Don't forget the eyebrow.** Every Swiss-style hero has a tiny mono-uppercase eyebrow above the H1 (e.g. `INTERNAL · 调研 · 2026-05-16`). It anchors the page.

## References

- `references/design-tokens.md` — paste-ready CSS variable blocks (Swiss + Tariq palettes), font stacks, typography scale, motion rules.
- `references/scenarios.md` — full 8-branch decision tree with what-must-have / what-must-avoid for each.
- `references/tariq-taxonomy-source.md` — verbatim summary of Tariq's 9 original categories and which of his demos each maps to.
- `templates/*.html` — paste-and-fill starts for each branch.
- `scripts/validate.mjs` — node script to verify hard rules.
