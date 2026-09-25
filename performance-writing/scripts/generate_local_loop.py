#!/usr/bin/env python3
"""Generate Claude Code fallback-loop prompts for performance writing.

This script is intentionally deterministic: it reads the already-confirmed
planner artifacts and emits role-specific prompts with concrete inputs,
outputs, and guardrails. It does not call external models.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass(frozen=True)
class RoleSpec:
    key: str
    file_name: str
    model: str
    output_path: str
    title: str
    task: str


ROLE_SPECS = [
    RoleSpec(
        key="leader",
        file_name="00_leader.md",
        model="opus",
        output_path="Performance_Workspace/07_Fallback_Local_Loop/state/leader_plan_round_01.md",
        title="Leader / Coordinator",
        task="Read reviewer gate records when present and write a structured next-round plan. Do not write performance prose directly.",
    ),
    RoleSpec(
        key="writer_a",
        file_name="01_writer_a.md",
        model="opus",
        output_path="Performance_Workspace/03_Writers/01_Writer_A/2026H1_writer_A_draft.md",
        title="Writer A",
        task="Write a complete first full draft with a rigorous structure and evidence-first style.",
    ),
    RoleSpec(
        key="writer_b",
        file_name="02_writer_b.md",
        model="sonnet",
        output_path="Performance_Workspace/03_Writers/02_Writer_B/2026H1_writer_B_draft.md",
        title="Writer B",
        task="Write a complete second full draft with business-outcome-first expression and higher reader persuasion. Do not paraphrase Writer A.",
    ),
    RoleSpec(
        key="cross_learning_a",
        file_name="03_cross_learning_a.md",
        model="opus",
        output_path="Performance_Workspace/04_Cross_Learning/01_Writer_A_After_Learning/2026H1_writer_A_after_learning.md",
        title="Cross Learning A",
        task="Read Writer A and Writer B drafts; keep A's strengths, learn from B, reject inappropriate B choices, then produce a complete A after-learning full draft.",
    ),
    RoleSpec(
        key="cross_learning_b",
        file_name="04_cross_learning_b.md",
        model="sonnet",
        output_path="Performance_Workspace/04_Cross_Learning/02_Writer_B_After_Learning/2026H1_writer_B_after_learning.md",
        title="Cross Learning B",
        task="Read Writer A and Writer B drafts; keep B's strengths, learn from A, reject inappropriate A choices, then produce a complete B after-learning full draft.",
    ),
    RoleSpec(
        key="reviewer",
        file_name="05_reviewer.md",
        model="opus",
        output_path="Performance_Workspace/05_Reviewer/01_Gate_Records/2026H1_reviewer_gate_record_round_01.md",
        title="Reviewer",
        task="Review after-learning drafts against the confirmed outline, writing rules, historical format sample, and status-boundary rules. Output a parseable PASS/REJECT gate record.",
    ),
]


def resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def read_head(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return f"[MISSING: {path}]"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit]


def build_common_context(
    workspace: Path,
    outline: Path,
    materials: Path,
    multica_instruction: Path,
    best_practices: Path | None,
    historical_example: Path | None,
) -> str:
    best_line = rel(best_practices, Path.cwd()) if best_practices else "auto-detect from materials manifest"
    historical_line = rel(historical_example, Path.cwd()) if historical_example else "auto-detect from materials manifest"
    return dedent(
        f"""
        ## Shared Context

        Workspace: `{workspace}`
        Confirmed outline: `{outline}`
        Multica squad instruction: `{multica_instruction}`
        Materials manifest: `{materials}`
        Best practices: `{best_line}`
        Historical style sample: `{historical_line}`

        You must follow the confirmed outline and the Multica instruction. The Multica instruction is the closest known-good process baseline; adapt it to this local Claude Code fallback role, but do not change the workflow structure.

        ## Required Reading

        1. Read the confirmed outline completely.
        2. Read the Multica squad instruction completely.
        3. Read the materials manifest and all locally available P0/P1 markdown or html materials listed there.
        4. Read best practices and the historical style sample. Historical examples are only for structure/style, never for business facts.

        ## Non-negotiable Guardrails

        1. Do not fabricate completion status, adoption, progress, launch state, metrics, role ownership, or business impact.
        2. Words such as 预计、计划、待上线、尚未回收、待确认 must never be rewritten as 已完成、已上线、已达成效果.
        3. If a status is uncertain, write 待确认 / 需补证据 / 计划中.
        4. Do not alter the three confirmed 战功 structure unless the prompt explicitly asks for a review comment.
        5. Do not use 2025H2 business facts in 2026H1 content.
        6. Keep Chinese prose concise, clear, and high-density; use numbered structures for complex sections.
        7. Only create or overwrite the requested output file. Do not modify unrelated files.
        """
    ).strip()


def full_draft_template() -> str:
    return dedent(
        """
        ## Required Full Draft Structure

        Your output file must be a complete performance-writing draft, not an outline or smoke-test title list:

        # 2026H1 <Role> Draft

        ## 阅读清单与吸收要点
        - [P0/P1] <material>: 已读；3-5句阅读感想；可引用事实；证据缺口/不可引用限制

        ## 战功
        ### 战功一：<完整总结句标题>
        <总述段：先总后分，说明业务问题、解法、结果>
        1. <分点：问题/解法/创新/数据/贡献>
        2. <分点>
        3. <分点>

        ### 战功二：...
        ### 战功三：...

        ## 内功
        ### 内功一：<完整总结句标题>
        <总述 + 分点>
        ### 内功二：...
        ### 内功三：...

        ## 自评
        ### 做得好
        1. ...
        ### 待提升
        1. ...

        ## 证据缺口与未写成事实的内容
        - <missing evidence or cautious wording>
        """
    ).strip()


def reviewer_template() -> str:
    return dedent(
        """
        ## Required Reviewer Output

        Start the output file with YAML frontmatter exactly like this shape:

        ---
        gate: PASS | REJECT
        return_to: final_assembly | leader
        round: 1
        blocking_issue_count: <integer>
        status_boundary_risk: true | false
        ---

        Then write:

        ## 三条最强项
        ## 阻塞问题
        ## 非阻塞建议
        ## 状态边界审查
        ## 如果 REJECT，给 Leader 的下一轮组织建议

        Hard REJECT conditions:
        1. Any expected/planned/pending state is rewritten as completed/launched/effect-achieved.
        2. Any P0 required material is not read.
        3. The three confirmed 战功 structure is changed without user approval.
        4. 2025H2 business facts are used as 2026H1 facts.
        """
    ).strip()


def leader_template() -> str:
    return dedent(
        """
        ## Required Leader Output

        Start with YAML frontmatter:

        ---
        next_action: revise_writer_a | revise_writer_b | revise_both | rerun_cross_learning | ask_user | stop
        round: 2
        assigned_roles:
          - writer_a
        reason: <short reason>
        ---

        Then explain:
        1. What the reviewer rejected or asked to improve.
        2. Which role should run next.
        3. Which input files the role must read.
        4. Which output file the role must create.
        5. What must not be changed.
        """
    ).strip()


def role_prompt(spec: RoleSpec, common: str) -> str:
    role_specific = ""
    if spec.key.startswith("writer"):
        role_specific = full_draft_template()
    elif spec.key.startswith("cross"):
        role_specific = full_draft_template() + dedent(
            """

            ## Cross Learning Requirements

            Before the full after-learning draft, include:
            1. 保留自己原稿哪些优点。
            2. 吸收对方哪些优点。
            3. 拒绝对方哪些写法及原因。

            Required inputs:
            - `Performance_Workspace/03_Writers/01_Writer_A/2026H1_writer_A_draft.md`
            - `Performance_Workspace/03_Writers/02_Writer_B/2026H1_writer_B_draft.md`
            """
        ).strip()
    elif spec.key == "reviewer":
        role_specific = reviewer_template() + dedent(
            """

            Required inputs:
            - `Performance_Workspace/04_Cross_Learning/01_Writer_A_After_Learning/2026H1_writer_A_after_learning.md`
            - `Performance_Workspace/04_Cross_Learning/02_Writer_B_After_Learning/2026H1_writer_B_after_learning.md`
            """
        ).strip()
    elif spec.key == "leader":
        role_specific = leader_template()

    return dedent(
        f"""
        # {spec.title}

        Model policy: `{spec.model}`
        Output file: `{spec.output_path}`

        ## Role Task

        {spec.task}

        {common}

        {role_specific}

        ## Final Instruction

        Create or overwrite exactly this file: `{spec.output_path}`.
        Do not modify any other files. If you cannot complete the task safely, write the blocker into the requested output file instead of inventing content.
        """
    ).strip() + "\n"


def config_yaml(args: argparse.Namespace, workspace: Path, outline: Path, materials: Path, multica: Path, best: Path | None, historical: Path | None) -> str:
    best_value = str(best) if best else ""
    historical_value = str(historical) if historical else ""
    return dedent(
        f"""
        workspace: {workspace}
        confirmed_outline: {outline}
        multica_instruction: {multica}
        materials_manifest: {materials}
        best_practices: {best_value}
        historical_example: {historical_value}
        max_rounds: {args.max_rounds}
        models:
          leader: opus
          writer_a: opus
          writer_b: sonnet
          cross_learning_a: opus
          cross_learning_b: sonnet
          reviewer: opus
        """
    ).lstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Claude Code fallback-loop prompt files.")
    parser.add_argument("--workspace", required=True, help="Performance workspace path")
    parser.add_argument("--outline", required=True, help="Confirmed outline path")
    parser.add_argument("--materials", required=True, help="Materials manifest path")
    parser.add_argument("--multica-instruction", required=True, help="Known-good Multica squad instruction path")
    parser.add_argument("--best-practices", help="Best practices file path")
    parser.add_argument("--historical-example", help="Historical style sample path")
    parser.add_argument("--out", default="Performance_Workspace/07_Fallback_Local_Loop", help="Output directory")
    parser.add_argument("--round", type=int, default=1, dest="round_number", help="Round number for generated prompts")
    parser.add_argument("--max-rounds", type=int, default=3, help="Max workflow rounds")
    args = parser.parse_args()

    workspace = resolve(args.workspace)
    outline = resolve(args.outline)
    materials = resolve(args.materials)
    multica = resolve(args.multica_instruction)
    best = resolve(args.best_practices) if args.best_practices else None
    historical = resolve(args.historical_example) if args.historical_example else None
    out_dir = resolve(args.out)
    prompts_dir = out_dir / "prompts" / f"round_{args.round_number:02d}"
    state_dir = out_dir / "state"
    logs_dir = out_dir / "logs" / f"round_{args.round_number:02d}"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    common = build_common_context(workspace, outline, materials, multica, best, historical)
    for spec in ROLE_SPECS:
        (prompts_dir / spec.file_name).write_text(role_prompt(spec, common), encoding="utf-8")

    run_plan = [
        "# Local Claude Code Fallback Loop Run Plan",
        "",
        "Status: prompt-generation v2. Use run_local_loop.py for controlled execution.",
        "",
        "Execution order:",
    ]
    for index, spec in enumerate(ROLE_SPECS, start=1):
        run_plan.append(f"{index}. `{spec.file_name}` — model `{spec.model}` — output `{spec.output_path}`")
    (out_dir / "RUN_PLAN.md").write_text("\n".join(run_plan) + "\n", encoding="utf-8")
    (out_dir / "config.yaml").write_text(config_yaml(args, workspace, outline, materials, multica, best, historical), encoding="utf-8")
    print(out_dir)


if __name__ == "__main__":
    main()
