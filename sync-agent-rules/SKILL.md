---
name: sync-agent-rules
description: "Precipitate a shared rule/experience into the user's 3 global agent rule files (Claude CLAUDE.md, Codex/Kiro AGENTS.md, Gemini GEMINI.md). The AGENT edits each file itself — choosing placement, heading level, and per-file phrasing — and wraps each rule in stable marker comments so later updates are idempotent. Trigger on '把这条经验/规则沉淀到全局', 'update global agent rules', '写入全局规则', 'sync rule to all agents'. Skip for per-project or per-skill rules."
---

# sync-agent-rules

Write or update a shared rule into the user's THREE source-of-truth global agent
rule files. Everything else (Claude Code, Codex, Kiro, Gemini/Antigravity) is
symlinked from these.

**Design: the agent edits the files, not a dumb script.** A script can only paste
a flat text block — no heading hierarchy, no sensible placement, no per-file
voice. So YOU (the agent) author and place each rule, matching each file's existing
markdown structure. Stable marker comments are kept ONLY as idempotency anchors so
a later update finds and rewrites the same rule instead of duplicating it. A small
helper script handles the mechanical safety rails (backup / locate / verify).

## Target files

| # | Path | Consumed by |
|---|------|-------------|
| 1 | `~/Library/Mobile Documents/com~apple~CloudDocs/ClaudeSync/dotclaude/CLAUDE.md` | Claude Code |
| 2 | `~/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/AGENTS.md` | Codex AND Kiro (Kiro steering symlinks to this) |
| 3 | `~/Library/Mobile Documents/com~apple~CloudDocs/GeminiSync/dotgemini/config/GEMINI.md` | Gemini / Antigravity |

Editing file #2 covers both Codex and Kiro.

## Workflow (agent-driven)

1. **Backup first**: `python3 scripts/rule_tool.py backup` — copies all targets to
   `<file>.bak-<timestamp>` and prints the paths.
2. **Locate**: `python3 scripts/rule_tool.py locate --topic <slug>` — for each file,
   reports whether the rule's marker block already exists and at which line range.
3. **Edit each file yourself** with your file-editing tools:
   - Pick a `<topic-slug>` (kebab-case) that identifies the rule.
   - Wrap the rule in markers so updates stay idempotent:
     ```
     <!-- BEGIN agent-rule:<topic-slug> -->
     ## <A real heading, in this file's style>

     <well-structured body: prose / bullets / sub-headings as the rule deserves>
     <!-- END agent-rule:<topic-slug> -->
     ```
   - **If the block already exists** (from `locate`): rewrite the content *between*
     its markers in place; keep its location. Do not add a second copy.
   - **If it does not exist**: place it in the most fitting section (or append a new
     top-level section), matching the heading depth and tone the file already uses.
   - Adapt wording per file if useful (e.g., Claude vs Codex vs Gemini voice); the
     intent must be identical across all three.
4. **Verify**: `python3 scripts/rule_tool.py verify --topic <slug>` — asserts each
   file has exactly one marker pair for the topic (catches dupes / mismatched markers).
5. **Report** the per-file result and the backup paths.

## Helper script

`scripts/rule_tool.py` is mechanical only — it never authors content:

- `backup` — back up all 3 targets, print backup paths.
- `locate --topic <slug>` — show presence + line range of the topic's block per file.
- `verify --topic <slug>` — exit non-zero unless every file has exactly one block.
- `--targets-file <json>` — override target paths (used for sandbox testing).

## When to use

- "把这条经验/规则沉淀到全局" / "update global agent rules" / a newly agreed
  cross-agent convention that must land in all 3 files.

## When NOT to use

- Per-project rules (project `AGENTS.md` / `CLAUDE.md`).
- Per-skill instructions (the skill's own `SKILL.md`).
