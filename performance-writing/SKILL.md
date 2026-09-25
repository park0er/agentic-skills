---
name: performance-writing
description: End-to-end Chinese performance-writing workflow for collecting materials, building a planner outline, running two independent writers, cross-learning, expert review, and final Feishu/local delivery. Use when drafting or operating绩效/述职/自评 artifacts, especially with战功/内功 structures, Feishu sources, Multica squads, or Claude/Codex worker loops. Includes strict anti-fabrication, priority-tagged material reading, Multica squad instruction generation, and optional local automation scaffolding.
---

# Performance Writing

## Core Contract

Use this skill to run a staged performance-writing workflow. Treat it as a governance process, not a one-shot writing prompt.

Non-negotiables:

1. Do not invent progress, launches, completion status, adoption, metrics, or user role. If evidence is missing, write “待确认 / 需补证据 / 计划中”.
2. Keep writing concise, clear, and high-density. Do not enforce “每条 500 字”, but avoid both verbosity and vague compression.
3. Prefer numbered structures for complex levels, usually 3 points and at most 4 points per layer. Do not create scattered bullet dumps.
4. Lead with business value and user impact, then explain methods, innovation, personal/team contribution, and quantified evidence.
5. Historical performance examples are style/format references only. Never copy their business facts into the current cycle.
6. After spawning sub-agents, do not block the main thread by habit. Continue user coordination unless the next step strictly depends on the result.

## Workspace Setup

Create the workflow folders before collecting materials:

```text
Performance_Workspace/
  01_Human_Preparation/
    01_Performance_Context_and_Deliverables/
      01_Performance_Form_Structure/
        01_Input_Box_Screenshots/
        02_Battle_and_Internal_Work_Definitions/
      02_Performance_Deliverable_Structure_Template/
    02_Input_Materials/
      01_Weekly_Reports_Required/
      02_Two_Quarter_OKRs_Required/
      03_Two_Quarter_Summary_Documents_Required/
      04_Other_References_Optional/
    03_Writing_Rules/
      01_Best_Practices/
      02_Historical_Performance_Examples_Optional/
  02_Planner/
  03_Writers/
    01_Writer_A/
    02_Writer_B/
  04_Cross_Learning/
    01_Writer_A_After_Learning/
    02_Writer_B_After_Learning/
  05_Reviewer/
    01_Gate_Records/
  06_Human_Final_Review/
```

If a period lacks an OKR because of role transfer or another confirmed reason, mark it “不适用” and do not keep asking.

## Material Collection

Create a local `materials_to_collect.md` and **must attempt to create a Feishu sheet** with matching rows for the user to fill in. Do not stop after creating only the local Markdown.

Feishu sheet creation rules:

1. Treat Feishu sheet creation as a required first-class step whenever the Feishu CLI/app connector is present or plausibly available.
2. Actively try to create the sheet, write the same rows as `materials_to_collect.md`, and configure the priority column as a single-select/dropdown with `P0`, `P1`, `P2` when the tooling supports it.
3. If sheet creation succeeds, write the Feishu sheet link back into the top of `materials_to_collect.md` using `<!-- feishu: https://... -->`, and mention the sheet link in the user-facing handoff.
4. Only fall back to local Markdown alone after a concrete blocker occurs, such as missing Feishu CLI, failed authentication, permission denial, unavailable network, or repeated API/tool failure. Record the blocker in `materials_to_collect.md` and tell the user exactly what prevented sheet creation.

Include these columns in both the local Markdown and Feishu sheet:

| Column | Required behavior |
|---|---|
| 序号 | Stable row id for discussion |
| 对应目录 | Exact target folder |
| 材料项 | Only defined material categories; put extras under other references |
| 是否必填 | 必填 / 条件必填 / 可选但推荐 / 可选 |
| 默认优先级 | Feishu single-select: P0, P1, P2 |
| 链接或本地路径 | User-provided Feishu URL or local path |
| 初始说明 | Scope, expected evidence, constraints |
| 备注 | User notes, citation limits, status |

Priority rules:

- Do not default any row to P0. Let the user explicitly mark P0.
- Treat P0 as mandatory deep-reading material; P1 as important supporting material; P2 as auxiliary.
- Before drafting instructions, sync the latest priority values from the sheet and state each worker’s reading list with P-levels.

## Deep Reading Gate

Before planning or writing, require every planner/writer/reviewer to output a reading ledger:

```text
文档阅读清单
- [P0/P1/P2] <file/url>: 已读；3-5 句阅读感想；可引用事实；不可引用/待确认事项
```

Reject and rerun any planner/writer/reviewer output that does not cover all assigned reading. Main agent acts as gatekeeper.

## Planner Stage

The planner must not write formal performance prose. It first reads all materials, then outputs three outline options.

Each option must include:

1. 战功：几条、每条完整标题、关键 evidence/metrics.
2. 内功：几条、每条完整标题、关键 evidence/metrics.
3. 总结/自评：做得好与待提升分别怎么写，列要点.
4. Trade-off: why this structure, what it emphasizes, what it de-emphasizes.

Title rule: write full summary sentences, preferably “通过 X，解决 Y，实现 Z / 达成量化成果”. Avoid vague labels like “AI 能力建设”.

Wait for user confirmation or correction before formal drafting.

## Multica Squad Main Path

When the user has Multica, generate a squad instruction as a required artifact in `02_Planner/multica_squad_instruction.md`. Use `references/multica_squad_instruction_template.md`.

The Multica loop should contain:

1. **Leader / Coordinator**: good model. Owns material pack, priorities, task routing, gatekeeping, and final assembly. Rejects incomplete reading or fabricated status.
2. **Writer A**: good or medium model. Independently drafts a full version from confirmed outline and required readings.
3. **Writer B**: good or medium model. Independently drafts a second full version with different expression choices, not a paraphrase.
4. **Cross learning**: Writer A reads Writer B and produces Writer A after-learning version; Writer B reads Writer A and produces Writer B after-learning version. This yields two documents, not one fusion role output.
5. **Reviewer**: good model. Reviews against best practices and historical format sample; also acts as an informed outsider to challenge logic gaps.
6. **Reject path**: reviewer rejection returns to Leader, not directly to one writer. Leader organizes the next loop.

Reviewer must check:

- Whether content follows writing best practices and accepted historical style.
- Whether business logic is understandable to an industry expert outside the department.
- Whether role/contribution is clear for a large-team owner: 主导 / 共同设计 / 推动协调 / 参与支持.
- Whether metrics, status, and completion claims are traceable.

## Claude Code Fallback Loop

If Multica is unavailable, use the controlled Claude Code fallback workflow. Preserve `01_Human_Preparation/` and `02_Planner/`; only clear or regenerate downstream writer/reviewer outputs. The fallback path must use the confirmed outline and the known-good Multica instruction as its process baseline.

Use `scripts/generate_local_loop.py` to generate role-specific prompts:

```bash
scripts/generate_local_loop.py \
  --workspace Performance_Workspace \
  --outline Performance_Workspace/02_Planner/2026H1_confirmed_outline.md \
  --materials Performance_Workspace/01_Human_Preparation/02_Input_Materials/materials_to_collect.md \
  --multica-instruction Performance_Workspace/02_Planner/multica_squad_instruction.md \
  --best-practices Performance_Workspace/01_Human_Preparation/03_Writing_Rules/01_Best_Practices/performance_writing_best_practices.md \
  --historical-example Performance_Workspace/01_Human_Preparation/03_Writing_Rules/02_Historical_Performance_Examples_Optional/2025H2_performance_example.md
```

Use `scripts/run_local_loop.py` to run the controlled workflow through Claude Code CLI. It keeps flow control in Python: Writer A/B, Cross A/B, Reviewer, then PASS or REJECT-to-Leader. Start with `--dry-run`; run live only after prompt paths and output targets look right.

Model assignment:

- Leader and Reviewer: `opus`.
- Writer A: `opus`.
- Writer B: `sonnet`.
- Cross Learning: use each writer's assigned model, or upgrade to `opus` when quality risk is high.
- Do not use `haiku` for this workflow.

Validation:

- Use `scripts/validate_outputs.py draft <path>` for writer and cross-learning full drafts.
- Use `scripts/validate_outputs.py reviewer <path>` for gate records.
- Status-boundary violations such as rewriting 预计/计划/待上线/尚未回收 into 已完成/已上线/已达成效果 are blocking errors.

Loop behavior: on Reviewer `REJECT`, the runner calls Leader to create a structured plan, parses `next_action` / `assigned_roles` / `needs_cross_learning`, runs targeted writer revisions, reruns cross-learning when needed, and then reruns Reviewer until `PASS`, `ask_user`, `stop`, parse failure, validation failure, or `max_rounds`.

## Final Assembly

After user chooses the direction or specific parts:

1. Combine only the selected writer/version sections.
2. Preserve user-provided replacement text exactly unless editing is requested.
3. Save final local Markdown under `06_Human_Final_Review/`.
4. If synced to Feishu, write the source link at the top of the local file:

```markdown
<!-- feishu: https://... -->
```

If the user makes final edits in Feishu, fetch the Feishu Markdown and save it as the final local truth.
