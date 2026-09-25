---
name: interviewer
description: Generate a self-contained, zero-network interactive interview HTML app for one user. Use when the user wants AI-led structured questioning to collect details, gather story/project material, or organize messy thinking into a persistent artifact, e.g. 采访我关于 X, 做个访谈系统, 交互式访谈边看问题边填答案, interview me about Z, build an interview app for a topic. Produces a warm-paper single-file app with localStorage autosave, JSON import/export, single-card flow, sidebar overview, and atomic 5W1H questions. Prefer this over long compound question lists. Skip for chat-only Q&A, multi-user surveys, or weekly-report writing.
---

# Interviewer Skill

Build a self-contained interactive interview HTML app that helps a **single user** think through a topic by being asked atomic questions one at a time. Inspired by the Socratic method (asking beats telling) and structured 5W1H decomposition. The app is for one user — it is not a multi-user survey tool.

## When to use

Use whenever the user wants AI to interview them about a topic to collect details, organize thoughts, or gather raw material — and they want a **persistent, interactive artifact**, not just a chat exchange. Common cues:

- "采访我一下关于 X 的细节" · "帮我做一个关于 Y 的访谈系统"
- "做个交互式访谈，让我能边看问题边填答案"
- "我有一个项目 / 经历 / 想法需要梳理 — 用提问的方式帮我"
- "Build me an interview app for [topic]" · "interview me about Z"

**Skip** when:
- The user just wants chat-based Q&A in this conversation (no app needed → just ask in chat)
- The user wants a survey form for **others** to fill out (this skill is for single-user introspection)
- The user wants weekly-report writing assistance (use the `weekly-report` skill)

## What this skill outputs

**One self-contained HTML file**. The user double-clicks it in their browser to start the interview. Hard rules — break any and the skill is broken:

1. **Single file** — no separate CSS / JS / JSON files. Schema embedded as `<script type="application/json">`.
2. **Zero network requests** — works offline. No CDN, no Google Fonts. CJK-safe system font stack.
3. **localStorage as primary storage** (key: `interviewer-<topic-slug>-v1`); JSON export / import as backup.
4. **5 save triggers** — input (debounced 200ms) · blur · navigation · beforeunload · visibilitychange. See `references/data-contract.md` for the rationale.
5. **Warm-paper palette** — ivory background, clay accent, oat secondary, olive for save indicator. Serif H1, sans body. **NOT Swiss / klein blue.** The user's previous attempts were "太艳了" (too vivid); the warm tone is mandatory because being interviewed is reflective work, and warm reads quieter.
6. **Single-card progressive flow** — one question at a time, with [上一题 · 跳过 · 保存并下一题] navigation + a sidebar overview of all questions for jumping around.
7. **Atomic question schema** — each question asks ONE thing decomposed by 时间 / 在哪 / 人物 / 什么 / 为什么 / 怎么发生 (5W1H). See `references/schema-design.md`.

## The 4-phase workflow

Follow these phases in order. Do not skip Phase 1 — generating an HTML before understanding the topic produces a generic, useless interview.

### Phase 1: Topic intake

Talk to the user briefly to clarify:

1. **Topic / theme** — what is being interviewed about? (a project, decision, story, week of work, design exploration …)
2. **Why now** — what will the user do with the answers afterwards? (write a doc, prep a talk, plan a decision, organize their own thinking)
3. **Domain structure** — is there an existing structure to respect? Examples:
   - Storyline projects → may already have red / green / blue color blocks
   - Behavior interviews → STAR (Situation / Task / Action / Result)
   - Project retros → phases (intake / exploration / build / launch / learn)
   - Decision prep → options / criteria / risks / verification

The structure is just a hint for grouping topics. If there's no obvious one, default to a flat topic list with no categories.

### Phase 2: Schema design

Sketch the question schema. Read `references/schema-design.md` for the full principles. Quick heuristic:

- **Topics** = 5-15 named clusters of related questions (e.g., "规则式工具失效的拐点", "飞书第一次 @ 机器人"). Each topic should be a coherent moment, decision, or area.
- **Questions per topic** = 4-6 atomic questions, each asking ONE thing.
- **Use 5W1H labels** as the `kind` field: 时间 / 在哪 / 人物 / 什么 / 为什么 / 怎么发生 (or English: when / where / who / what / why / how). The label appears on the question card as a chip — it cues the user what kind of memory to retrieve.
- **One question = one cognitive load.** Don't ask "when and where and who" in one prompt — split into three.

Sketch the schema as a draft and **confirm with the user** before generating the HTML. Show them topic titles + question counts; let them add / remove / reorganize. This is the highest-leverage step — a good schema produces a useful interview, a bad schema produces noise.

The schema shape (see `references/schema-design.md` for full reference):

```json
{
  "version": 1,
  "categories": [
    { "id": "red", "name": "红块 · 奠基", "color": "#C73E36" }
  ],
  "topics": [
    { "id": "t1", "title": "Topic title", "category": "red", "ch": "Optional chapter label", "intro": "1-2 sentence intro shown above first question of this topic." }
  ],
  "questions": [
    { "id": "t1-q1", "topic_id": "t1", "kind": "时间", "prompt": "Short prompt asking one thing.", "hint": "Optional hint shown below prompt." }
  ]
}
```

Categories are optional — only use them if the user has 2+ visually distinct groups (e.g., the storyline V6 case had 红 / 绿 / 蓝). For most one-off interviews, leave `categories: []` and don't set `category` on topics; the template falls back to a single neutral accent.

### Phase 3: HTML generation

Start from `templates/interview-app.html`. Replace the four `[BRACKETED]` placeholders with real values:

| Placeholder | What goes there |
|---|---|
| `[INTERVIEW_TITLE]` | Human-friendly title shown in `<title>` and hero. Example: "项目复盘采访 V1" |
| `[INTERVIEW_LEDE]` | 1-2 sentence description of why this interview exists. Shown below H1. |
| `[STORAGE_KEY]` | localStorage key — kebab-case, prefix with `interviewer-`. Example: `interviewer-project-retro-v1` |
| `[SCHEMA_JSON]` | Pretty-printed schema JSON from Phase 2. Goes inside `<script id="schema" type="application/json">`. |

**Do not modify** the CSS, the save logic, the keyboard shortcuts, or the UI structure in the template. These implement the data contract from `references/data-contract.md` and are battle-tested. If you think a tweak is needed, raise it back to the user — don't silently customize.

Save the generated file to wherever the user is working from. If they have an active project directory, save it there. If not, save to a sensible path under their working directory and tell them the absolute path.

### Phase 4: Hand-off

Tell the user the four things they need to know:

1. **Path** — where the file is saved (absolute path).
2. **How to open** — double-click in any browser, or use a Launch preview tool if available.
3. **localStorage origin pin** — localStorage is bound to the file's `file://` origin. Same file double-clicked from the **same path** sees the same data. **Move the file mid-interview = new origin = different (empty) data.** Tell them this explicitly so they don't lose work by reorganizing their files.
4. **Backup discipline** — export JSON every 5-10 questions. The app auto-toasts a reminder every 5 questions. To go cross-device, import the exported JSON on the new device.

When they're done, they can:
- Paste the exported JSON back into a chat with you (or another agent) for downstream synthesis (drafting a doc, prepping a talk, organizing notes).
- Or open the HTML on another device after importing the JSON.

## Visual style: warm-paper palette (non-negotiable)

The template is themed warm-paper. Don't switch it to Swiss. The reasoning matters more than the color choice itself:

> Being interviewed is reflective, sometimes uncertain work. The user is digging through their own memory, often without precise dates or names. Vivid, decision-shaped UI (klein blue + lemon yellow) projects "ship now, decide" energy that conflicts with the introspective register of the task. Warm-paper reads quieter and gives the user permission to think — closer to a notebook than to a dashboard.

Token reference (already wired into the template; documented here so you understand what each color does):

```css
--ivory:  #FAF9F5;   /* page background — warm off-white */
--paper:  #FFFFFF;   /* card surface */
--slate:  #141413;   /* body text — dark sepia, not pure black */
--clay:   #D97757;   /* primary accent — italic emphasis, active node, current question */
--clay-d: #B85C3E;   /* clay strong — links, hover */
--oat:    #E3DACC;   /* secondary surface fill — TL;DR card, kind chip background */
--olive:  #788C5D;   /* success — "saved" indicator, JSON backup green */
--warn:   #C2502C;   /* error — save-failed banner, reset confirmation */
```

Typography (already in template):
- **H1**: serif stack (Charter / Iowan Old Style / Source Han Serif SC), weight **500** (not 900), italic emphasis in clay
- **Body**: sans stack (system-ui / PingFang SC / Source Han Sans SC), 16.5px
- **Mono**: ui-monospace with PingFang SC fallback (so CN comments don't render as tofu)
- **CN density**: `:lang(zh) body { letter-spacing: 0.01em; }` — opens up paragraphs without breaking rhythm

## Architecture overview

For the system architecture (HTML/JS layer, localStorage, save triggers, JSON I/O, failure modes, the "completely-doesn't-exist" zone of server / DB / cloud / network), open **`README.html`** in a browser. It's a clickable diagram with sticky detail panel — built using the `tariq-html` skill's diagram branch in warm-paper palette. Click any node to see its role.

This is the same architecture diagram that's been validated on the project that originated this skill (MayGroupAIShare V6 故事采访). When users ask "where is my data" or "what happens if my browser crashes", point them at `README.html`.

## Schema design reference

For:
- Why atomic questions over compound questions
- The 5W1H taxonomy and when to add domain-specific kinds (STAR, etc.)
- Worked examples decomposing real topics into 4-6 questions

→ Read `references/schema-design.md`.

## Data contract reference

For:
- The 4 storage layers (L1 localStorage / L2 JSON file / L3 JS memory / L4 schema in HTML)
- Each save trigger and why redundancy matters
- The JSON export / import format
- Failure modes and how each is mitigated

→ Read `references/data-contract.md`.

## Interview method reference

For:
- Why "ask one thing at a time" beats "ask everything"
- How to write hint text that helps without leading
- When to follow up vs. when to move on
- The "drop empty answers" rule that protects user from feeling stuck

→ Read `references/interview-method.md`.

## Naming conventions

- **File name**: `<topic-slug>-interview.html` (kebab-case, no spaces). Example: `project-retro-interview.html`
- **Storage key**: `interviewer-<topic-slug>-v1`. The `-v1` suffix means future schema changes can bump to `-v2` without colliding with old data.
- **Title** (in `[INTERVIEW_TITLE]`): human-friendly, mixed CN / EN OK, under 30 chars.
- **Backup files** the app generates: `<storage-key>-backup-<ISO-timestamp>.json` (the template generates this automatically).

## Anti-patterns (don't do these)

- **Don't ask the user "what questions should I ask?"** — your job is to propose questions and let them refine. Asking back is offloading the work.
- **Don't generate compound questions** like "When did this happen and who was involved?" Split into two questions, both with appropriate `kind` labels.
- **Don't use Swiss palette / klein blue / vivid colors.** The user has already specifically said "太艳了" (too vivid) about the previous version.
- **Don't add fake "submit / finish" actions** that lock the answers. The user must always be able to revisit any question.
- **Don't write the HTML from scratch.** Always start from the template — it has accumulated bug fixes (cross-platform mobile beforeunload, localStorage quota handling, etc.).
- **Don't fetch the schema from a separate JSON file.** `file://` protocol blocks `fetch()` for security. Schema MUST be embedded inline.
