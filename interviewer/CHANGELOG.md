# interviewer CHANGELOG

## 2026-05-21 — shorten-description-metadata

- Shortened the `SKILL.md` frontmatter description so it stays under the 1024-character loader limit.
- Preserved the important trigger cues, output contract, warm-paper default, and skip cases in the concise metadata.
- No migration needed; the detailed workflow remains in the skill body.

## 2026-05-18 — initial-release

**What this is.** A new skill for generating self-contained interactive interview HTML apps. Use case: when the user wants AI to interview them about a topic to collect details and organize messy thinking. The skill produces a single warm-paper-styled HTML file with localStorage autosave + JSON export/import + atomic 5W1H question schema.

**What's in the box:**

- `SKILL.md` — main skill, the 4-phase workflow (intake / schema design / generation / handoff)
- `templates/interview-app.html` — the canonical warm-paper interview app template; replace 4 `[BRACKETED]` placeholders to ship
- `references/schema-design.md` — atomic question decomposition by 5W1H, with worked examples
- `references/data-contract.md` — 4 storage layers, 5 save triggers, JSON export/import format, failure modes
- `references/interview-method.md` — Socratic principles, hint design, when-to-skip discipline
- `README.html` — interactive architecture diagram (clickable SVG with sticky detail panel) — open in browser to understand the system

**Origin.** This skill was extracted from a one-off interview app built for the MayGroupAIShare V6 故事采访 project (2026-05-17). The one-off app validated the architecture under real use — 39 atomic questions, multi-day interview, multi-Mac handoff via JSON export/import. After validation, I extracted the data contract + visual style + workflow into this generic skill so future "interview me about X" requests don't reinvent the same pattern.

**Visual style decision: warm-paper, not Swiss.** The original one-off used Swiss palette (klein blue / lemon yellow). The user's feedback: "太艳了" (too vivid) — being interviewed is reflective work, vivid decision-shaped UI conflicts with the introspective register. Switched to Tariq warm-paper (ivory / clay / oat / olive on warm off-white, serif H1). The template enforces this; do not switch back to Swiss.

**Architecture decision: zero network requests.** The skill outputs single HTML files with no CDN, no Google Fonts, no fetch calls. This means:
- Works on a plane / VPN-blocked corporate network / no wifi
- HTML can be emailed and opened anywhere
- localStorage origin pinning is the only constraint

This conflicts with the latest `tariq-html` Mode B/C font strategy (which requires Google Fonts or base64 inlined fonts for CN serif quality). **Conscious tradeoff:** the interviewer skill prioritizes portability over CN serif rendering quality. The system stack (`Charter, "Source Han Serif SC", Songti SC, ...`) renders fine on macOS; Windows/Linux fall back to plain Songti SC which is acceptable for an introspective-register page. Both `templates/interview-app.html` and `README.html` therefore fail the tariq-html validator's Font-Mode-B-or-C check — this is **intentional and documented**, not a bug.

**Schema design philosophy: atomic 5W1H questions over compound questions.** Each question card asks ONE thing, labeled with a `kind` chip (时间 / 在哪 / 人物 / 什么 / 为什么 / 怎么发生). Compound questions (the original V1 dashboard had 8 paragraph-length questions) lose 70%+ of intended detail because users pick the easiest sub-part and answer that. Atomic decomposition produces 4-6 questions per topic where each gets a real answer.

**Data safety: 5 redundant save triggers.** localStorage is written by 5 different events (input debounced 200ms / blur / navigation / beforeunload / visibilitychange). Plus JSON export for cross-device backup. Plus reset-archives-don't-delete. The user requirement was strict ("数据弄丢就弄死你") and the redundancy is calibrated to the failure modes documented in `references/data-contract.md`.

**Known limitations:**
- Single-user only — not a survey form for distribution
- localStorage origin-pinned — moving the file across directories creates a new origin (empty data); use JSON export/import for cross-device
- No native mobile app — runs in mobile browser but typing on phone is suboptimal for long interviews
