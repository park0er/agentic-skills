# Scenarios

Eight branches. Map the user's ask to one. When in doubt and the content compares 2+ options, pick **comparison**.

The branches are an abstraction over Tariq's original 9 categories — collapsed where redundant for Parker's actual workflow (analysis-heavy, not coding-heavy), and elevated where high-value (comparison gets the most polish).

---

## 01 · comparison ⭐ PRIMARY

**Maps to Tariq**: §01 (exploration code approaches), §03 (annotated PR diff conceptually) — really a Parker-specific category.

**When to pick**: The user is comparing N options/tools/models/vendors/approaches and wants to **decide**. Triggers: 方案对比 / 选型对比 / 工具对比 / decision matrix / "我要直接对比" / "选哪个好".

**Must-have**:
1. **TL;DR callout** at the very top — lemon-yellow, ink-bordered, 1–2 sentences max. Recommendation is wrapped in `<strong>` (inverse-marker style).
2. **One-screen decision matrix** — table with N rows × M criteria. Sortable visually (rank column in klein-blue). Mini-bars or score chips inside cells where applicable.
3. **Tool/option cards** — one card per option. Recommended option has klein-blue border + "推荐" angle badge. Filter pills on top to slice by attribute (e.g., output format, license).
4. **Recommendation path** — numbered steps (1 → 2 → 3). Each step is a klein-blue numeral + an instruction.
5. **避坑提醒** — safety-orange left-border cards with concrete pitfalls.

**Must-avoid**:
- More than 8 options on one page. If you have 10+, group into "tools" vs "methodology" tiers (the latter on muted background to de-emphasize).
- Long prose between sections — every section is structural, not narrative.
- Vague rankings without justification — every "recommended" must have one-line reason in the matrix.

**Template**: `templates/comparison.html` (the most polished template — mirrors PAR-162's `ppt-tools-comparison.html`).

---

## 02 · exploration

**Maps to Tariq**: §01 exploration-code-approaches, §02 exploration-visual-designs.

**When to pick**: User isn't sure what they want yet. They want N draft directions side-by-side so they can react/point. Triggers: "给我列三种思路" / "fan out" / "几个方向" / "show me options".

Distinction from comparison: **no recommendation yet**. The whole point is to NOT decide — to lay out neutrally so the user can pick.

**Must-have**:
1. Brief framing — what problem these directions solve, in 2–3 lines.
2. **N panels** rendered side-by-side (or 2x2 grid on desktop, stacked on mobile). Each panel is a real-looking artifact, not just a description.
3. **Trade-off table** below the panels — the same N options across rows, with 3–5 dimensions.
4. **No "推荐" badge anywhere.** Neutrality is the contract.

**Must-avoid**:
- Picking a winner. The user picks.
- More than 4 directions. Three is the sweet spot.

**Template**: `templates/exploration.html`.

---

## 03 · decision-plan

**Maps to Tariq**: §01 implementation-plan, §02 PR writeup (loosely).

**When to pick**: A pick has been made; now we hand it to the implementer. Triggers: "出一份执行计划" / "implementation plan" / "RFC" / "把这个落地一下".

**Must-have**:
1. **One-line goal** at top — what we're building.
2. **Milestones on a horizontal timeline** — dates + deliverables.
3. **Data-flow / system diagram** (inline SVG) — show the moving parts.
4. **Risk table** — rows are risks, columns are likelihood / impact / mitigation.
5. **Open questions** — small section at bottom, klein-blue numbered.

**Must-avoid**:
- Pretending you've thought of every risk. Mark unknowns explicitly.
- Long prose explanations of the diagram — the diagram is the explanation.

**Template**: `templates/decision-plan.html`.

---

## 04 · research-explainer

**Maps to Tariq**: §07 research-feature-explainer, §07 research-concept-explainer.

**When to pick**: User wants to understand a concept / feature / mechanism deeply. Triggers: "解释一下 X" / "X 是怎么工作的" / "教我一下" / "deep-dive 一下".

**Must-have**:
1. **TL;DR callout** at the top.
2. **Section anchors** in sticky nav — research pages get long.
3. **Collapsible details** for the deep parts (`<details><summary>` is sufficient — no JS needed).
4. **Inline diagram** if the concept is spatial (caches, pipelines, ring algorithms, etc.).
5. **Glossary or key-terms sidebar** if there are 5+ jargon terms.
6. **Tabbed code samples** if multiple languages / configs apply.

**Must-avoid**:
- Dumping everything at the same indent level. The user reads top-down — surface the punchline, hide the depth behind summaries.
- Walls of code. Every code block needs one-line context above it.

**Template**: `templates/research-explainer.html`. Consider Tariq warm-paper palette here for editorial feel.

---

## 05 · status-report

**Maps to Tariq**: §08 status-report, §08 incident-report.

**When to pick**: Recurring updates — 周报, 双周报, 项目复盘, 事故报告. Triggers: "周报" / "项目状态" / "post-mortem" / "事故复盘".

**Must-have**:
1. **Date / period** prominently in the eyebrow.
2. **Headline status** — one of `on-track / at-risk / blocked` with corresponding color (lemon-green / lemon-yellow / safety-orange).
3. **What shipped** list — short, verb-led, with link/PR/issue references.
4. **What slipped** list — same shape, with one-line reason per item.
5. **Small chart** if there are numbers — bar / sparkline / progress dots. Use SVG, not Canvas.
6. **Next milestone** — date + 3 things needed to hit it.

**For incident-report variant**:
- Replace "what shipped" with **timeline** (vertical, minute-by-minute).
- Add **root cause** + **follow-up checklist**.

**Must-avoid**:
- Prose paragraphs. Status is a list, not a memoir.
- Hiding the headline. The status color belongs in the first 200px of the page.

**Template**: `templates/status-report.html`.

---

## 06 · deck

**Maps to Tariq**: §06 slide-deck.

**When to pick**: User explicitly wants something to arrow-key through in a meeting. Triggers: "做个 deck" / "内部分享" / "demo day slides".

**Must-have**:
1. **Each slide is a `<section class="slide">`** — full viewport, snap-scroll on the container.
2. **Arrow-key navigation** via tiny inline JS (~20 lines).
3. **Slide counter** in a corner ("3 / 12").
4. **First slide = title slide**, last slide = "questions / contact".
5. **One idea per slide.** If a slide has > 7 lines of text, split it.

**Must-avoid**:
- Reading-mode density. Decks are for talking over, not reading.
- Long bullet lists. Three bullets per slide max.
- Animations. Swiss decks don't dance.

**Template**: `templates/deck.html`.

---

## 07 · diagram

**Maps to Tariq**: §05 svg-illustrations, §05 flowchart-diagram, §02 module-map. Specifically captures the interaction model from Tariq's `13-flowchart-diagram.html`.

**When to pick**: The artifact IS the diagram. User wants a flowchart, module map, pipeline visualization, sequence diagram. Triggers: "画一下 pipeline" / "module map" / "system diagram".

**Must-have** (interactivity is non-negotiable here — a static diagram is the "阉割版"):
1. **Inline SVG** drawn by hand (no Mermaid, no D3 — they pull CDNs and look generic).
2. **Every node is clickable.** Wrap each shape in `<g class="node" data-k="UNIQUE_KEY">` with `<text pointer-events:none>` so the parent `<g>` always catches the click.
3. **Sticky right detail panel** with 4 slots: `#p-title`, `#p-meta`, `#p-body` (innerHTML, supports inline `<code>`), `#p-code` (textContent for code blocks; `display:none` when empty).
4. **Flat `window.DETAIL` dictionary** keyed by `data-k` — title / meta / body / code per node.
5. **Pre-activate the first node on load** so the panel is never empty on first paint.
6. **Active state**: `.node.active` gets a klein-blue 3px stroke. Hover: `transform: translateY(-1px)` + `cursor: pointer`.
7. **Keyboard support**: each `<g class="node">` gets `tabindex="0"` and listens for Enter/Space to activate (Tariq's own demo doesn't do this; we strictly improve on it).
8. **Legend** if more than 3 colors / shapes are used.
9. **One-line caption** below the diagram.

**Must-avoid**:
- Box-and-arrow with no semantics (everything a rectangle). Use shape variation to encode meaning.
- More than ~12 nodes on one diagram. Group into sub-diagrams.
- Skipping the detail panel "to save space". Without it the diagram is decoration, not information — it's the click-to-detail that turns a flowchart into a navigable doc.

**Template**: `templates/diagram.html` — clickable-node + sticky panel scaffolded; replace placeholders + DETAIL dict.

---

## Interactivity contract (cross-cutting)

Tariq's demos are not pretty pictures — they're **navigable documents**. Every template now ships the interaction inline. Match this energy per branch:

| Branch | Default palette | Required interaction (verify after editing!) | Source pattern |
|---|---|---|---|
| **comparison** ★ | Swiss | Filter pills · **sortable matrix** (click header, `data-v` carries true value) · scroll-spy nav | Tariq §03, §02 |
| exploration | Swiss (Tariq for narrative) | Equal-tier panels (no winner) · **cross-highlight panel↔column** | Tariq §01 |
| decision-plan | Swiss | **Clickable system-diagram** with sticky `#dp-*` panel · **toggleable open questions** | Tariq §07 + §13 lite |
| research-explainer | **Tariq warm-paper** | `<details>` accordion · tabbed code (`:checked`) · **scroll-spy TOC** · glossary | Tariq §07 |
| status-report | Swiss | **Filter pills** (shipped/slipped/blocked) · **chart hover tooltip** · live incident-timeline variant | Tariq §08 |
| deck | Swiss (Tariq for narrative) | Arrow-key nav · counter · ESC index · F-fullscreen · **idx syncs on manual scroll** | Tariq §06 |
| **diagram** ★ | Swiss | **Click-to-detail panel**: `<g.node[data-k]>` + `window.DETAIL` + pre-activate first + `tabindex` | **Tariq §07 / §13** |
| design-system | Either (Tariq for brand work) | Click-to-copy on swatches **and** type rows **and** spacing chips · real `:hover/:focus/:disabled` | Tariq §03 |

**Default palette ≠ rule** — every template ships both palettes (one active, one in a comment block). The LLM must **judge by intent** before generating: see the routing table in `references/design-tokens.md`. Rule of thumb when ambiguous → **Tariq warm-paper** unless the content is explicitly about a decision or a number.

If a branch ships static when its row above demands interaction, the validator (or you) must reject the output and re-author. After any template edit, re-walk the row above and confirm every bullet is still wired up — losing the JS during a markup rewrite is the most common regression.

---

## 08 · design-system

**Maps to Tariq**: §03 design-system, §03 component-variants.

**When to pick**: User wants tokens / swatches / a component contact sheet. Triggers: "渲染一下 tokens" / "design system" / "颜色板" / "组件 sheet".

**Must-have**:
1. **Color swatches** with hex copy-on-click (use a `<button>` and `navigator.clipboard.writeText` — graceful fallback if unsupported).
2. **Type scale** — render every size/weight you actually use.
3. **Spacing scale** — visual blocks at each step.
4. **Component contact sheet** — every state (default / hover / disabled / loading) of each component.

**Must-avoid**:
- Faking content variety. Use real labels — "Primary CTA" not "Lorem ipsum".
- Hiding tokens behind tabs. They're meant to be a single scannable canvas.

**Template**: `templates/design-system.html`. Tariq warm-paper palette is a strong fit here.

---

## How to choose when an ask is ambiguous

Ask one clarifying question if the request is genuinely ambiguous (e.g., "make this into HTML" with no scenario hint). The question to ask:

> 这个页面的主要目的是 **(a) 帮你做选型决策**、**(b) 解释一个概念**、**(c) 汇报项目状态**、还是 **(d) 别的**？

Defaulting blind, pick **comparison** if there are 2+ named options in the source content, otherwise **research-explainer**.
