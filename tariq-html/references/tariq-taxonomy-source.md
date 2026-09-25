# Tariq's original 9 categories (verbatim summary)

Source: <https://thariqs.github.io/html-effectiveness/> — companion page to Tariq Shihadah's blog post "The unreasonable effectiveness of HTML".

The page argues that an LLM agent should ship one self-contained `.html` file instead of a wall of markdown when the content is **spatial, decisional, or interactive**. Twenty demos are grouped by what kind of work each replaces.

This document captures Tariq's taxonomy as the source of truth. Our skill collapses these into 8 branches (`references/scenarios.md`) — this file exists so future maintainers can trace each branch back to Tariq's original framing.

---

## 01 · Exploration & Planning (3 demos)

> When you're not sure what you want yet. Ask the agent to fan out across several directions and lay them next to each other so you can point at one — instead of reading three sequential walls of text and trying to hold them all in your head.

| Demo | What it is |
|---|---|
| `01-exploration-code-approaches.html` | Three code approaches side-by-side, trade-offs called out inline |
| `02-exploration-visual-designs.html` | A handful of layout / palette options rendered live |
| `16-implementation-plan.html` | Milestones on a timeline, data-flow diagram, mockups, risk table |

→ Maps to our **comparison** (when there's a recommendation), **exploration** (when neutral), **decision-plan** (the implementation handoff).

---

## 02 · Code Review & Understanding (3 demos)

> Diffs and call-graphs are spatial information; markdown flattens them.

| Demo | What it is |
|---|---|
| `03-code-review-pr.html` | Annotated diff with margin notes, severity tags, jump links |
| `17-pr-writeup.html` | Author-side PR description: motivation, before/after, file-by-file tour |
| `04-code-understanding.html` | Module map: boxes + arrows, hot path highlighted |

→ Maps to our **diagram** (module map) and **decision-plan** (PR writeup variant). Annotated-PR is intentionally **not** a top-level branch in our skill since it's coding-tool-specific and Parker's workflow rarely needs it.

---

## 03 · Design (2 demos)

> HTML is the medium your design system ships in, so it's the natural format for talking about it.

| Demo | What it is |
|---|---|
| `05-design-system.html` | Tokens (color/type/spacing) as swatches |
| `06-component-variants.html` | Every size/state/intent of one component on a single sheet |

→ Maps directly to our **design-system** branch.

---

## 04 · Prototyping (2 demos)

> Motion and interaction can't be described, only felt.

| Demo | What it is |
|---|---|
| `07-prototype-animation.html` | Animation sandbox with sliders for duration/easing |
| `08-prototype-interaction.html` | Four screens linked together — clickable flow |

→ **Not directly exposed** as a top-level branch. Prototypes are usually multi-file projects where the LLM should generate code, not a static `.html`. If a user really wants a single-file prototype, route them through **research-explainer** with embedded interactive demos.

---

## 05 · Illustrations & Diagrams (2 demos)

> Inline SVG gives the agent a real pen.

| Demo | What it is |
|---|---|
| `10-svg-illustrations.html` | A figure sheet for a blog post — vector art tweakable by hand |
| `13-flowchart-diagram.html` | Deploy pipeline as a real flowchart with click-to-detail |

→ Maps directly to our **diagram** branch.

---

## 06 · Decks (1 demo)

> A handful of `<section>` tags and twenty lines of JS is a slide deck.

| Demo | What it is |
|---|---|
| `09-slide-deck.html` | A short presentation as one HTML file. Arrow keys to navigate, no build step |

→ Maps directly to our **deck** branch.

---

## 07 · Research & Learning (2 demos)

> An explainer with collapsible sections, tabbed code samples and a glossary in the margin reads very differently from the same words dumped linearly.

| Demo | What it is |
|---|---|
| `14-research-feature-explainer.html` | "Explain rate limiting in this repo" — TL;DR + collapsibles + tabbed configs + FAQ |
| `15-research-concept-explainer.html` | Consistent hashing taught with a live ring + comparison table + glossary |

→ Maps directly to our **research-explainer** branch.

---

## 08 · Reports (2 demos)

> Recurring documents — status updates, post-mortems — benefit most from a bit of structure and color.

| Demo | What it is |
|---|---|
| `11-status-report.html` | Weekly status: shipped / slipped / small chart |
| `12-incident-report.html` | Post-mortem with timeline, log excerpts, follow-up checklist |

→ Maps directly to our **status-report** branch (covers both the regular and incident variants).

---

## 09 · Custom Editing Interfaces (3 demos)

> Sometimes it's hard to describe what you want in a text box. Ask for a throwaway editor for the exact thing you're working on — and always end with an export button.

| Demo | What it is |
|---|---|
| `18-editor-triage-board.html` | Drag tickets across Now / Next / Later / Cut, copy out as markdown |
| `19-editor-feature-flags.html` | Toggle grid with dependency warnings, "copy diff" button |
| `20-editor-prompt-tuner.html` | Editable template + 3 sample inputs that re-render live |

→ **Not directly exposed.** Custom editors are bespoke per-task and don't templatize well. If a user asks for one, build it from scratch using the design tokens — don't try to fit into a branch.

---

## What Tariq's page does itself (and we steal from)

The page itself is a Tariq-warm-paper-style **comparison** page (using our taxonomy):

- Hero with a markdown-vs-html visual figure.
- TOC pills at top, anchor-linked.
- 9 sections, each with index numeral + title + count chip + intro paragraph.
- Each section is a card grid (3-up / 2-up depending on demo count).
- Cards have a custom inline-SVG thumbnail, serif title, sans description, mono filename.
- Hover state: card lifts, thumbnail bg darkens, filename arrow shifts right.
- Footer with italic serif tagline + repo link.

Our **comparison** branch borrows the section-numeral pattern and the card-grid layout. We use the Swiss palette by default because that's what Parker's existing artifacts use, but `templates/research-explainer.html` is a closer aesthetic clone of Tariq's own page (and uses Palette B).
