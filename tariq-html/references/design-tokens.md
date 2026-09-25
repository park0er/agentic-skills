# Design tokens

Two palette systems are supported. **Pick by intent — there is no global default.** Swiss = decision/data. Tariq warm-paper = editorial/concept. When in doubt, prefer Tariq warm-paper (it's closer to the source aesthetic of thariqs.github.io). Both palettes ship as ready-to-uncomment `:root` blocks in every `templates/*.html`.

Don't mix palettes mid-document.

---

## Palette A · Swiss-international

This is the system used on PAR-162's `ppt-tools-comparison.html` and `opus-vs-gpt55.html`. It reads as data-dense, decision-oriented, and confident — the right register for option comparisons, internal decks, status reports, and analytical content.

```css
:root {
  /* core palette */
  --klein:         #002FA7;  /* primary brand, italic emphasis, anchor links, recommendation borders */
  --lemon-yellow:  #FFED00;  /* TL;DR background, hover-link highlight */
  --lemon-green:   #B5DF4A;  /* footer links on dark, secondary accent */
  --safety-orange: #FF6B00;  /* warning / 避坑 / dot indicators / strikethrough */
  --ink:           #111;     /* body text, borders, dark-mode bg */
  --mute:          #666;     /* metadata, eyebrows, sub-labels */

  /* surfaces */
  --bg:            #fafaf7;  /* page background — warm off-white, NOT pure white */
  --card:          #ffffff;  /* card / hero / sticky-nav surface */
  --line:          #111;     /* used for hard 1px borders — same as --ink, named for intent */

  /* code */
  --code-bg:       #efefe9;
}
```

### Typography

```css
body {
  font-family: "Helvetica Neue", "Inter", -apple-system, BlinkMacSystemFont,
               "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.55;
  color: var(--ink);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}

code, kbd {
  font-family: "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  font-size: 0.88em;
  background: var(--code-bg);
  padding: 1px 5px;
  border-radius: 2px;
}

/* Hero title: heavy weight, tight tracking, italic slot for klein-blue emphasis */
h1.title {
  font-size: clamp(36px, 6vw, 72px);
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.02em;
}
h1.title em {
  font-style: italic;
  color: var(--klein);
  font-weight: 900;
}

/* Section header: 60px-wide klein-blue numeral + 28px ink-black title */
.section-num {
  font-size: 44px;
  font-weight: 900;
  color: var(--klein);
  letter-spacing: -0.04em;
  line-height: 1;
}
.section-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.01em;
}

/* Eyebrow: tiny mono-uppercase line above any major heading */
.eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--mute);
}
```

### Primitives

**TL;DR callout** (always lemon-yellow with ink border):

```html
<div class="tldr">
  <div class="label">TL;DR</div>
  <div class="body">主推 <strong>guizang Style B</strong>，因为场景匹配度最高。</div>
</div>
```

```css
.tldr {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 24px;
  padding: 24px;
  background: var(--lemon-yellow);
  border: 2px solid var(--ink);
}
.tldr .label { font-size: 11px; letter-spacing: 0.2em; font-weight: 700; text-transform: uppercase; }
.tldr .body { font-size: 16px; line-height: 1.5; }
.tldr .body strong { background: var(--ink); color: var(--lemon-yellow); padding: 2px 6px; font-weight: 700; }
```

**Sticky anchor nav** (pills, klein-blue on hover):

```css
nav.jump {
  position: sticky; top: 0; z-index: 10;
  padding: 14px 6vw;
  background: var(--card);
  border-bottom: 1px solid var(--line);
  display: flex; flex-wrap: wrap; gap: 8px;
  font-size: 13px;
}
nav.jump a {
  border: 1px solid var(--line);
  padding: 6px 12px;
  border-radius: 999px;
  color: var(--ink);
  background: var(--card);
  text-decoration: none;
}
nav.jump a:hover,
nav.jump a.primary { background: var(--klein); color: white; border-color: var(--klein); }
```

**Card** (white surface, hard-edge klein-blue offset shadow on hover):

```css
.card {
  background: var(--card);
  border: 2px solid var(--ink);
  padding: 24px;
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.card:hover {
  transform: translate(-2px, -2px);
  box-shadow: 6px 6px 0 var(--klein); /* HARD edge, no blur — Swiss-grid signature */
}
.card.recommended {
  border-color: var(--klein);
  position: relative;
}
.card.recommended::before {
  content: "推荐";
  position: absolute;
  top: -2px; right: -2px;
  background: var(--klein);
  color: white;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 4px 10px;
}
```

**Decision matrix** (data-dense table with sticky thead, hover row, klein-blue rank column):

```css
table.matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--card);
  border: 2px solid var(--ink);
}
table.matrix th, table.matrix td {
  padding: 10px 12px; text-align: left;
  border-bottom: 1px solid #ddd;
  vertical-align: top;
}
table.matrix thead th {
  background: var(--ink);
  color: var(--card);
  font-weight: 700;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  position: sticky; top: 0;
}
table.matrix tbody tr:hover { background: #fffbde; }
table.matrix .rank { font-weight: 900; color: var(--klein); }
```

**Mini-bar** (inline horizontal bar inside a table cell or card):

```css
.bar {
  display: inline-block;
  height: 8px;
  background: var(--klein);
  vertical-align: middle;
  margin-right: 8px;
}
.bar.warn { background: var(--safety-orange); }
.bar.go   { background: var(--lemon-green); }
```

**Avoidance card** (safety-orange left border, "避坑" semantics):

```css
.avoid {
  border-left: 4px solid var(--safety-orange);
  padding: 12px 16px;
  background: var(--card);
  margin-bottom: 8px;
}
.avoid .tag {
  font-size: 10px; letter-spacing: 0.15em; font-weight: 700;
  color: var(--safety-orange); text-transform: uppercase;
}
```

### Motion rules

- **120ms ease** for card hover transforms. Faster than Material's 200ms — Swiss design is responsive, not luxurious.
- **No blur** in box-shadows. Hard offset (`6px 6px 0 color`) only.
- **No transitions on color** — color changes are instant. Only transform / opacity / box-shadow get easing.
- **Sticky nav** has no slide-down animation. It's just there.

---

## Palette B · Tariq warm-paper

Use whenever the page is editorial / concept / narrative — research explainers, "what is X" walkthroughs, story-led retros, design-system catalogs, narrative decks. Reads quieter, more literary, less data-heavy. This is also the closer-to-source-aesthetic of thariqs.github.io itself, so it's the right call when the user says "make it feel like Tariq's actual page".

```css
:root {
  --ivory:  #FAF9F5;  /* page background */
  --paper:  #FFFFFF;  /* card surface */
  --slate:  #141413;  /* body text */
  --clay:   #D97757;  /* primary accent — italic emphasis, links */
  --clay-d: #B85C3E;  /* clay hover state */
  --oat:    #E3DACC;  /* secondary surface fill */
  --olive:  #788C5D;  /* tertiary accent */
  --g100:   #F0EEE6;
  --g200:   #E6E3DA;
  --g300:   #D1CFC5;
  --g500:   #87867F;
  --g700:   #3D3D3A;

  /* Type — see "CJK-safe font stacks" section at the bottom for rationale */
  --serif:
    Charter, "Iowan Old Style", ui-serif, Georgia, "Times New Roman", Times,
    "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong",
    serif;
  --sans:
    system-ui, -apple-system, "Segoe UI", "Helvetica Neue",
    "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB",
    "Source Han Sans SC", "Noto Sans CJK SC",
    Roboto, Helvetica, Arial, sans-serif;
  --mono:
    ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Monaco, Consolas,
    "PingFang SC", "Source Han Sans SC",
    monospace;
}
```

### Typography (Tariq variant)

- **H1**: serif, weight 500 (NOT 900), `clamp(38px, 5.4vw, 62px)`, line-height 1.06, letter-spacing -0.018em, max-width 17ch.
- **H2**: serif, weight 500, 27px.
- **Body**: sans, 16.5px, line-height 1.55.
- Italic emphasis in headings is `var(--clay)`, not klein-blue.
- Code is `var(--mono)`.

This palette is for editorial-feel pages: research explainers, concept walkthroughs, design-system catalogs. **Don't use it for decision matrices or status reports** — the warm tone reads as "I'm here to think, not to ship."

---

## Picking between palettes

| If the page is for… | Use |
|---|---|
| 方案对比 / 选型 / 投票 / 决策矩阵 | Swiss |
| 内部周报 / 项目状态 / 事故 timeline | Swiss |
| 数据驱动的 deck / pitch / pre-read | Swiss |
| RFC handoff · system pipeline · 工程 diagram | Swiss |
| Concept explainer · "what is X" / research deep-dive | Tariq warm-paper |
| Story-led retro · narrative postmortem | Tariq warm-paper |
| Editorial brainstorm · 反思式 fan-out exploration | Tariq warm-paper |
| Design-system catalog | Either — Tariq for editorial brand work, Swiss for engineering tokens |
| Talk-style deck / keynote pre-read | Either — Tariq if narrative, Swiss if structural |

**When in doubt → Tariq warm-paper.** Swiss is the right call when the page is *built around data or a decision*; in everything else, warm-paper is closer to the source aesthetic of thariqs.github.io and the register Parker is asking for. (Old guidance was "default Swiss" — we flipped it because most non-decision content reads better warm.)

---

## Font strategy: Mode B by default, Mode C for permanence

The skill **ships its own CN typography** rather than depending on whatever
the user happens to have installed. Bare system fallback (Mode A) was retired
on 2026-05-18 (PAR-170 review: "中文字体很丑") because Songti SC — the
cross-platform default for CN serif — renders dense and uneven on most
machines, especially when the upstream stack expects Source Han Serif SC
(which Apple does not preinstall).

There are now two production modes. Pick by intent before generating:

### Mode B — Google Fonts (DEFAULT)

Three lines in `<head>` load Noto Serif SC + Noto Sans SC weights 400/500/700.
~150–250 KB woff2 over the wire, HTTP-cached after first paint, degrades to
system Songti SC if offline. Use for daily iteration / internal sharing /
local browsing — the common case.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@400;500;700&display=swap" rel="stylesheet">
```

`display=swap` ensures text is readable during the ~600 ms font fetch (browser
paints with the system fallback first, swaps to Noto when the woff2 lands).

### Mode C — Base64 inline (ARCHIVE / OFFLINE / HANDOFF)

Replace the 3 Mode B `<link>` lines with a `<style>` block whose `@font-face`
rules embed Noto Serif SC + Noto Sans SC as `data:font/woff2;base64,...`. File
grows ~150–300 KB; single static HTML works offline forever. Use for
PDF-export / archive / handoff to non-technical users / "must render the same
in 5 years" / 国内裸网或防火墙环境.

Generation recipe:

```bash
# 1. Get the .otf source from notofonts.org or Google Fonts download
# 2. Subset to GB18030-Plus (covers Simplified Chinese + Latin + punct)
pyftsubset NotoSerifSC-Regular.otf \
  --unicodes-file=gb18030-plus.txt \
  --output-file=NotoSerifSC-Regular-subset.woff2 \
  --flavor=woff2 --layout-features='*' --no-hinting

# 3. Repeat for weights 500 and 700, plus Noto Sans SC variants
# 4. base64-encode each woff2 → paste into the @font-face src URL
base64 -i NotoSerifSC-Regular-subset.woff2 -o /tmp/serif400.b64
```

Template:

```html
<style>
  @font-face {
    font-family: "Noto Serif SC";
    font-weight: 400;
    src: url(data:font/woff2;base64,PASTE_BASE64_HERE) format('woff2');
    font-display: swap;
  }
  @font-face {
    font-family: "Noto Serif SC";
    font-weight: 700;
    src: url(data:font/woff2;base64,PASTE_BASE64_HERE) format('woff2');
    font-display: swap;
  }
  /* repeat for Noto Sans SC weights 400 / 500 / 700 */
</style>
```

If you don't yet have base64-subset assets handy, ship Mode B and tell the
user how to upgrade later. Don't fake Mode C with placeholders.

---

## CJK-safe font stacks (kami-aligned, Mode B/C-aware)

The same three font tokens (`--font-sans / --font-serif / --font-mono` in Swiss
templates, `--sans / --serif / --mono` in the Tariq warm template) ship in **all
8 templates** and stay identical across both palettes. Palette-A vs Palette-B
toggles **colors only** — never type — so a single page can switch palettes
without breaking text fit.

### The stacks (post-Mode-B flip)

The serif/sans stacks now lead with the actually-loaded family
(`"Noto Serif SC"` / `"Noto Sans SC"`) so the browser uses Mode B/C glyphs
first, then falls back to Apple/Windows/open-source CN fonts if the woff2 hasn't
arrived yet.

```css
--font-sans:
  "Noto Sans SC", "Helvetica Neue", "Inter", -apple-system, BlinkMacSystemFont,
  "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB",
  "Source Han Sans SC", "Noto Sans CJK SC",
  sans-serif;

--font-serif:
  "Noto Serif SC", Charter, "Iowan Old Style", Georgia, "Times New Roman",
  "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong",
  serif;

--font-mono:
  ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas,
  "PingFang SC", "Source Han Sans SC",
  monospace;
```

### Why this exact order — kami lessons + Mode-B priority

1. **Loaded family first.** Mode B/C ship Noto Serif SC + Noto Sans SC, so the
   browser should reach for those glyphs whenever they're available. Putting
   them at the head of each stack guarantees that — and keeps the page
   self-consistent across OSes (the same glyphs render on macOS / Windows /
   Linux / Android).
2. **Latin Apple fallback after CN.** Once the loaded family is in place, the
   next layer (Helvetica Neue / Charter / Georgia) only matters when the page
   contains Latin text the user starts reading before woff2 finishes; the
   browser renders that Latin in Helvetica/Charter and swaps when fonts arrive.
3. **PingFang SC before Microsoft YaHei.** Mac before Windows when the loaded
   font also fails (e.g. user is offline and Songti SC missing).
4. **Source Han Sans / Noto Sans CJK as cross-platform fallback.** Open-source
   fonts shipping on Linux distros — last resort before generic `sans-serif`.
5. **Songti SC / STSong for serif.** Same intent as before: macOS/Windows
   serif fallbacks.
6. **Mono stack must include CJK fallback.** Pure mono stacks (`Menlo,
   Consolas, monospace`) render `// 这是中文注释` as tofu on systems without
   built-in CJK glyph fallback for monospace. Adding `"PingFang SC"` and
   `"Source Han Sans SC"` to the mono stack lets CN comments render at the cost
   of slight kerning quirks (CN glyphs aren't strictly monospaced) — kami
   accepts this trade-off and so do we.

> Direct quote from kami's `references/design.md`:
> > Any font-family that may render Chinese or Japanese must include a CJK
> > fallback, including `@page` footer text, `pre`, `code`, and SVG labels. A
> > pure mono stack can render missing glyph boxes in WeasyPrint.

### What changed on 2026-05-18 (vs the original kami-aligned release)

- **Mono stack: unchanged.** Mono CN fallback still rides on system PingFang;
  loading a CN mono web font is overkill for the small amount of `code` /
  `pre` content these templates carry.
- **Sans/serif stacks: led by the loaded family.** Was Latin-first; now
  Loaded-CN-first. Latin still flows correctly because Latin glyphs in Noto
  Serif/Sans SC are well-designed (they pair with their Latin siblings, Noto
  Serif / Noto Sans, but the SC variants ship Latin coverage too).
- **Validator: accepts Google Fonts and base64 woff2.** Previously hard-failed
  on `fonts.googleapis.com` to enforce the (now-retired) zero-external-requests
  rule.

### CN density compensation

Each template includes:

```css
:lang(zh) body, html[lang^="zh"] body { letter-spacing: 0.01em; }
```

Kami's design.md explains: CN glyphs (especially serif/楷-style ones) read
denser than Latin at the same size. A hair of letter-spacing (≈0.01em on web,
0.1–0.2pt in kami's print PDFs) opens up paragraphs without breaking density.
The rule scopes to `:lang(zh)` so EN-only pages don't get spacing artifacts.

### When to override

If the user names a specific brand whose typography is part of the brand
identity (e.g. a tech brand that uses `Inter` exclusively), override the stack
in that page's `:root` — but keep the CN fallback chain intact. Don't replace
`Noto Sans SC, ..., sans-serif` with bare `Inter, sans-serif`; the browser will
fall to Linux default for CN and you'll see tofu in production.
