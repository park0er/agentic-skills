#!/usr/bin/env python3
"""Run a controlled Claude Code fallback loop for performance writing.

The runner deliberately keeps flow control in Python. Models write content;
this script decides which role runs next, validates outputs, and stops safely
when parsing fails or max rounds is reached.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

SCRIPT_DIR = Path(__file__).resolve().parent
GENERATOR = SCRIPT_DIR / "generate_local_loop.py"
VALIDATOR = SCRIPT_DIR / "validate_outputs.py"

ROLE_ORDER = ["01_writer_a.md", "02_writer_b.md", "03_cross_learning_a.md", "04_cross_learning_b.md", "05_reviewer.md"]
MODEL_BY_PROMPT = {
    "00_leader.md": "opus",
    "01_writer_a.md": "opus",
    "02_writer_b.md": "sonnet",
    "03_cross_learning_a.md": "opus",
    "04_cross_learning_b.md": "sonnet",
    "05_reviewer.md": "opus",
}

INITIAL_OUTPUTS = {
    "writer_a": "Performance_Workspace/03_Writers/01_Writer_A/2026H1_writer_A_draft.md",
    "writer_b": "Performance_Workspace/03_Writers/02_Writer_B/2026H1_writer_B_draft.md",
    "cross_learning_a": "Performance_Workspace/04_Cross_Learning/01_Writer_A_After_Learning/2026H1_writer_A_after_learning.md",
    "cross_learning_b": "Performance_Workspace/04_Cross_Learning/02_Writer_B_After_Learning/2026H1_writer_B_after_learning.md",
}

REVISION_OUTPUTS = {
    "writer_a": "Performance_Workspace/03_Writers/01_Writer_A/round_{round_number:02d}_revision.md",
    "writer_b": "Performance_Workspace/03_Writers/02_Writer_B/round_{round_number:02d}_revision.md",
    "cross_learning_a": "Performance_Workspace/04_Cross_Learning/01_Writer_A_After_Learning/2026H1_writer_A_after_learning_round_{round_number:02d}.md",
    "cross_learning_b": "Performance_Workspace/04_Cross_Learning/02_Writer_B_After_Learning/2026H1_writer_B_after_learning_round_{round_number:02d}.md",
    "reviewer": "Performance_Workspace/05_Reviewer/01_Gate_Records/2026H1_reviewer_gate_record_round_{round_number:02d}.md",
}
VALIDATION_BY_PROMPT = {
    "01_writer_a.md": ("draft", "Performance_Workspace/03_Writers/01_Writer_A/2026H1_writer_A_draft.md"),
    "02_writer_b.md": ("draft", "Performance_Workspace/03_Writers/02_Writer_B/2026H1_writer_B_draft.md"),
    "03_cross_learning_a.md": ("draft", "Performance_Workspace/04_Cross_Learning/01_Writer_A_After_Learning/2026H1_writer_A_after_learning.md"),
    "04_cross_learning_b.md": ("draft", "Performance_Workspace/04_Cross_Learning/02_Writer_B_After_Learning/2026H1_writer_B_after_learning.md"),
    "05_reviewer.md": ("reviewer", "Performance_Workspace/05_Reviewer/01_Gate_Records/2026H1_reviewer_gate_record_round_01.md"),
    "00_leader.md": ("leader", "Performance_Workspace/07_Fallback_Local_Loop/state/leader_plan_round_01.md"),
}


def run(cmd: list[str], cwd: Path, log_file: Path | None = None, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(cmd))
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(f"$ {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}\n", encoding="utf-8")
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    current_key: str | None = None
    list_values: dict[str, list[str]] = {}
    for line in parts[1].splitlines():
        stripped = line.strip()
        if stripped.startswith("-") and current_key:
            list_values.setdefault(current_key, []).append(stripped[1:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            data[current_key] = value.strip()
        else:
            current_key = None
    for key, values in list_values.items():
        data[key] = ",".join(values)
    return data


def parse_assigned_roles(value: str | None) -> set[str]:
    if not value:
        return set()
    cleaned = value.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    return {part.strip().replace("- ", "") for part in cleaned.split(",") if part.strip()}


def bool_value(value: str | None, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"true", "yes", "1", "y"}


def reviewer_output(round_number: int) -> str:
    return REVISION_OUTPUTS["reviewer"].format(round_number=round_number)


def role_output(role: str, round_number: int) -> str:
    if round_number == 1 and role in INITIAL_OUTPUTS:
        return INITIAL_OUTPUTS[role]
    return REVISION_OUTPUTS[role].format(round_number=round_number)


def latest_role_output(role: str, current_round: int, cwd: Path) -> str:
    for round_number in range(current_round, 0, -1):
        candidate = role_output(role, round_number)
        if (cwd / candidate).exists():
            return candidate
    return role_output(role, 1)


def base_context(args: argparse.Namespace) -> str:
    best = args.best_practices or "auto-detect from materials manifest"
    historical = args.historical_example or "auto-detect from materials manifest"
    return dedent(
        f"""
        Workspace: `{args.workspace}`
        Confirmed outline: `{args.outline}`
        Multica instruction: `{args.multica_instruction}`
        Materials manifest: `{args.materials}`
        Best practices: `{best}`
        Historical style sample: `{historical}`

        Hard rules:
        1. Follow the confirmed outline and Multica instruction.
        2. Do not invent completion, launch, adoption, progress, metrics, role ownership, or business impact.
        3. 预计/计划/待上线/尚未回收/待确认 must never become 已完成/已上线/已达成效果.
        4. Historical samples are format/style only; never copy 2025H2 business facts.
        5. Only create or overwrite the requested output file.
        """
    ).strip()


def revision_prompt(
    role: str,
    output_path: str,
    args: argparse.Namespace,
    cwd: Path,
    round_number: int,
    leader_plan: str,
    reviewer_record: str,
) -> str:
    role_label = "Writer A" if role == "writer_a" else "Writer B"
    prior = latest_role_output(role, round_number - 1, cwd)
    other = latest_role_output("writer_b" if role == "writer_a" else "writer_a", round_number - 1, cwd)
    return dedent(
        f"""
        # {role_label} Targeted Revision Round {round_number:02d}

        Model role: {role_label}
        Output file: `{output_path}`

        {base_context(args)}

        Required inputs:
        - Previous own draft: `{prior}`
        - Other writer reference draft: `{other}`
        - Reviewer gate record: `{reviewer_record}`
        - Leader plan: `{leader_plan}`

        Task:
        Revise only the issues assigned by the Leader plan and Reviewer gate record. Produce a complete revised performance draft, not a patch note only.

        Required output structure:
        ## 本轮修改清单
        ## 阅读清单与吸收要点
        ## 战功
        ### 战功一
        ### 战功二
        ### 战功三
        ## 内功
        ## 自评
        ## 证据缺口与未写成事实的内容

        Do not change the confirmed three 战功 structure. Do not add unsupported facts. Preserve strengths from the previous draft unless the Leader explicitly asks to change them.
        """
    ).strip() + "\n"


def cross_revision_prompt(
    role: str,
    output_path: str,
    args: argparse.Namespace,
    cwd: Path,
    round_number: int,
    leader_plan: str,
    reviewer_record: str,
) -> str:
    label = "Cross Learning A" if role == "cross_learning_a" else "Cross Learning B"
    own_writer = "writer_a" if role == "cross_learning_a" else "writer_b"
    other_writer = "writer_b" if own_writer == "writer_a" else "writer_a"
    own = latest_role_output(own_writer, round_number, cwd)
    other = latest_role_output(other_writer, round_number, cwd)
    return dedent(
        f"""
        # {label} Round {round_number:02d}

        Output file: `{output_path}`

        {base_context(args)}

        Required inputs:
        - Own-side writer draft/revision: `{own}`
        - Other-side writer draft/revision: `{other}`
        - Reviewer gate record: `{reviewer_record}`
        - Leader plan: `{leader_plan}`

        Task:
        Produce a complete after-learning full draft for this side. Include what you keep, what you learn, what you reject and why, then write the full revised performance content.

        Required output structure:
        ## 本轮互学决策
        ## 阅读清单与吸收要点
        ## 战功
        ### 战功一
        ### 战功二
        ### 战功三
        ## 内功
        ## 自评
        ## 证据缺口与未写成事实的内容
        """
    ).strip() + "\n"


def reviewer_revision_prompt(output_path: str, args: argparse.Namespace, cwd: Path, round_number: int) -> str:
    writer_a = latest_role_output("writer_a", round_number, cwd)
    writer_b = latest_role_output("writer_b", round_number, cwd)
    cross_a = latest_role_output("cross_learning_a", round_number, cwd)
    cross_b = latest_role_output("cross_learning_b", round_number, cwd)
    return dedent(
        f"""
        # Reviewer Round {round_number:02d}

        Output file: `{output_path}`

        {base_context(args)}

        Required inputs:
        - Writer A latest draft/revision: `{writer_a}`
        - Writer B latest draft/revision: `{writer_b}`
        - Writer A after-learning/revision: `{cross_a}`
        - Writer B after-learning/revision: `{cross_b}`

        Start the output file with YAML frontmatter:
        ---
        gate: PASS | REJECT
        return_to: final_assembly | leader
        round: {round_number}
        blocking_issue_count: <integer>
        status_boundary_risk: true | false
        recommended_action: revise_writer_a | revise_writer_b | revise_both | rerun_cross_learning | ask_user
        ---

        Then write: 三条最强项、阻塞问题、非阻塞建议、状态边界审查、如果 REJECT 给 Leader 的下一轮建议.

        Hard REJECT if expected/planned/pending status is written as completed/launched/effect-achieved, if P0 materials are not read, if confirmed 战功 structure changes, or if 2025H2 facts pollute 2026H1.
        """
    ).strip() + "\n"


def leader_revision_prompt(output_path: str, args: argparse.Namespace, cwd: Path, round_number: int, reviewer_record: str) -> str:
    cross_a = latest_role_output("cross_learning_a", round_number, cwd)
    cross_b = latest_role_output("cross_learning_b", round_number, cwd)
    return dedent(
        f"""
        # Leader Plan After Reviewer REJECT Round {round_number:02d}

        Output file: `{output_path}`

        {base_context(args)}

        Required inputs:
        - Reviewer gate record: `{reviewer_record}`
        - Writer A current after-learning/draft: `{cross_a}`
        - Writer B current after-learning/draft: `{cross_b}`

        Start with YAML frontmatter:
        ---
        next_action: revise_writer_a | revise_writer_b | revise_both | rerun_cross_learning | ask_user | stop
        round: {round_number + 1}
        assigned_roles:
          - writer_a
        needs_cross_learning: true | false
        needs_reviewer: true
        reason: <short reason>
        ---

        Then explain: 返工目标、要保留的内容、必须修改的问题、指派给各角色的任务、下一轮输入文件、下一轮输出文件、不得改动的边界。

        Decide only the next workflow action. Do not write performance prose directly.
        """
    ).strip() + "\n"


def write_dynamic_prompt(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def claude_run(prompt_path: Path, model: str, cwd: Path, log_dir: Path, dry_run: bool) -> None:
    prompt = prompt_path.read_text(encoding="utf-8")
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--allowedTools",
        "Read,Write,Edit,Glob,Grep,LS",
        "--dangerously-skip-permissions",
    ]
    run(cmd, cwd=cwd, log_file=log_dir / f"{prompt_path.stem}.log", dry_run=dry_run)


def validate(prompt_name: str, cwd: Path, dry_run: bool) -> None:
    if prompt_name not in VALIDATION_BY_PROMPT:
        return
    kind, output = VALIDATION_BY_PROMPT[prompt_name]
    run([sys.executable, str(VALIDATOR), kind, output], cwd=cwd, dry_run=dry_run)


def validate_output(kind: str, output: str, cwd: Path, dry_run: bool) -> None:
    run([sys.executable, str(VALIDATOR), kind, output], cwd=cwd, dry_run=dry_run)


def generate(args: argparse.Namespace, round_number: int, cwd: Path, dry_run: bool) -> Path:
    cmd = [
        sys.executable,
        str(GENERATOR),
        "--workspace",
        args.workspace,
        "--outline",
        args.outline,
        "--materials",
        args.materials,
        "--multica-instruction",
        args.multica_instruction,
        "--out",
        args.out,
        "--round",
        str(round_number),
        "--max-rounds",
        str(args.max_rounds),
    ]
    if args.best_practices:
        cmd += ["--best-practices", args.best_practices]
    if args.historical_example:
        cmd += ["--historical-example", args.historical_example]
    run(cmd, cwd=cwd, dry_run=False)
    return (cwd / args.out / "prompts" / f"round_{round_number:02d}").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Claude Code fallback workflow.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--outline", required=True)
    parser.add_argument("--materials", required=True)
    parser.add_argument("--multica-instruction", required=True)
    parser.add_argument("--best-practices")
    parser.add_argument("--historical-example")
    parser.add_argument("--out", default="Performance_Workspace/07_Fallback_Local_Loop")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-after-review", action="store_true", help="Stop after first reviewer gate even on REJECT")
    parser.add_argument("--resume-from-reviewer", help="Resume from an existing REJECT reviewer gate record")
    parser.add_argument("--resume-round", type=int, default=1, help="Round number of --resume-from-reviewer")
    args = parser.parse_args()

    cwd = Path.cwd().resolve()
    leader_plan_path: Path | None = None
    previous_reviewer_path: Path | None = None
    next_action = "initial_full_run"
    assigned_roles: set[str] = set()
    needs_cross_learning = True
    start_round = 1

    if args.resume_from_reviewer:
        previous_reviewer_path = (cwd / args.resume_from_reviewer).resolve()
        if not previous_reviewer_path.exists():
            print(f"resume reviewer record not found: {previous_reviewer_path}", file=sys.stderr)
            return 2
        data = parse_frontmatter(previous_reviewer_path)
        if data.get("gate") != "REJECT":
            print("--resume-from-reviewer requires a REJECT gate record", file=sys.stderr)
            return 2
        resume_round = args.resume_round
        prompts_dir = generate(args, resume_round, cwd, args.dry_run)
        log_dir = cwd / args.out / "logs" / f"round_{resume_round:02d}"
        leader_output = f"Performance_Workspace/07_Fallback_Local_Loop/state/leader_plan_round_{resume_round:02d}.md"
        leader_prompt = write_dynamic_prompt(
            prompts_dir / f"00_leader_round_{resume_round:02d}.md",
            leader_revision_prompt(leader_output, args, cwd, resume_round, str(previous_reviewer_path.relative_to(cwd))),
        )
        claude_run(leader_prompt, MODEL_BY_PROMPT["00_leader.md"], cwd, log_dir, args.dry_run)
        validate_output("leader", leader_output, cwd, args.dry_run)
        if args.dry_run:
            print("dry-run resume complete")
            return 0
        leader_plan_path = cwd / leader_output
        data = parse_frontmatter(leader_plan_path)
        next_action = data.get("next_action", "")
        assigned_roles = parse_assigned_roles(data.get("assigned_roles"))
        needs_cross_learning = bool_value(data.get("needs_cross_learning"), default=True)
        if not next_action:
            print(f"Cannot parse leader next_action from {leader_plan_path}; stopping.", file=sys.stderr)
            return 2
        print(f"Resumed leader plan parsed: next_action={next_action}, assigned_roles={sorted(assigned_roles)}, needs_cross_learning={needs_cross_learning}")
        start_round = resume_round + 1

    for round_number in range(start_round, args.max_rounds + 1):
        prompts_dir = generate(args, round_number, cwd, args.dry_run)
        log_dir = cwd / args.out / "logs" / f"round_{round_number:02d}"

        if round_number == 1:
            for prompt_name in ROLE_ORDER:
                prompt_path = prompts_dir / prompt_name
                model = MODEL_BY_PROMPT[prompt_name]
                claude_run(prompt_path, model, cwd, log_dir, args.dry_run)
                validate(prompt_name, cwd, args.dry_run)
        else:
            if next_action == "ask_user":
                print("Leader requested user input; stopping workflow.")
                return 1
            if next_action == "stop":
                print("Leader requested stop; stopping workflow.")
                return 1

            roles_to_revise: set[str]
            if next_action == "revise_writer_a":
                roles_to_revise = {"writer_a"}
            elif next_action == "revise_writer_b":
                roles_to_revise = {"writer_b"}
            elif next_action == "revise_both":
                roles_to_revise = {"writer_a", "writer_b"}
            elif next_action == "rerun_cross_learning":
                roles_to_revise = set()
                needs_cross_learning = True
            else:
                roles_to_revise = assigned_roles & {"writer_a", "writer_b"}

            if not roles_to_revise and not needs_cross_learning:
                print(f"No executable roles for next_action={next_action}; stopping.", file=sys.stderr)
                return 2

            leader_plan = str(leader_plan_path.relative_to(cwd)) if leader_plan_path else ""
            reviewer_record = str(previous_reviewer_path.relative_to(cwd)) if previous_reviewer_path else ""

            for role in sorted(roles_to_revise):
                output = role_output(role, round_number)
                prompt_path = write_dynamic_prompt(
                    prompts_dir / f"{role}_revision.md",
                    revision_prompt(role, output, args, cwd, round_number, leader_plan, reviewer_record),
                )
                model = "opus" if role == "writer_a" else "sonnet"
                claude_run(prompt_path, model, cwd, log_dir, args.dry_run)
                validate_output("draft", output, cwd, args.dry_run)

            if needs_cross_learning:
                for role in ["cross_learning_a", "cross_learning_b"]:
                    output = role_output(role, round_number)
                    prompt_path = write_dynamic_prompt(
                        prompts_dir / f"{role}_round_{round_number:02d}.md",
                        cross_revision_prompt(role, output, args, cwd, round_number, leader_plan, reviewer_record),
                    )
                    model = "opus" if role == "cross_learning_a" else "sonnet"
                    claude_run(prompt_path, model, cwd, log_dir, args.dry_run)
                    validate_output("draft", output, cwd, args.dry_run)

            reviewer_output_path = reviewer_output(round_number)
            reviewer_prompt_path = write_dynamic_prompt(
                prompts_dir / f"05_reviewer_round_{round_number:02d}.md",
                reviewer_revision_prompt(reviewer_output_path, args, cwd, round_number),
            )
            claude_run(reviewer_prompt_path, "opus", cwd, log_dir, args.dry_run)
            validate_output("reviewer", reviewer_output_path, cwd, args.dry_run)

        reviewer_path = cwd / reviewer_output(round_number)
        if args.dry_run:
            print("dry-run complete")
            return 0
        data = parse_frontmatter(reviewer_path)
        gate = data.get("gate")
        if gate == "PASS":
            print("Workflow PASS. Ready for final assembly.")
            return 0
        if gate != "REJECT":
            print(f"Cannot parse reviewer gate from {reviewer_path}; stopping.", file=sys.stderr)
            return 2
        if args.stop_after_review:
            print("Reviewer REJECT; stop-after-review enabled.")
            return 1

        leader_output = f"Performance_Workspace/07_Fallback_Local_Loop/state/leader_plan_round_{round_number:02d}.md"
        leader_prompt = write_dynamic_prompt(
            prompts_dir / f"00_leader_round_{round_number:02d}.md",
            leader_revision_prompt(leader_output, args, cwd, round_number, str(reviewer_path.relative_to(cwd))),
        )
        claude_run(leader_prompt, MODEL_BY_PROMPT["00_leader.md"], cwd, log_dir, args.dry_run)
        validate_output("leader", leader_output, cwd, args.dry_run)
        leader_plan_path = cwd / leader_output
        data = parse_frontmatter(leader_plan_path)
        next_action = data.get("next_action", "")
        assigned_roles = parse_assigned_roles(data.get("assigned_roles"))
        needs_cross_learning = bool_value(data.get("needs_cross_learning"), default=True)
        previous_reviewer_path = reviewer_path
        if not next_action:
            print(f"Cannot parse leader next_action from {leader_plan_path}; stopping.", file=sys.stderr)
            return 2
        print(f"Leader plan parsed: next_action={next_action}, assigned_roles={sorted(assigned_roles)}, needs_cross_learning={needs_cross_learning}")

    print("Reached max rounds without PASS; human intervention required.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
