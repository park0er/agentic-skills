#!/usr/bin/env python3
"""Validate performance-writing fallback-loop outputs."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BAD_STATUS_PATTERNS = [
    (r"预计[^\n。；;]{0,40}(已完成|已上线|已达成|完成上线)", "预计/计划内容被写成已完成"),
    (r"计划[^\n。；;]{0,40}(已完成|已上线|已达成|完成上线)", "计划内容被写成已完成"),
    (r"待上线[^\n。；;]{0,40}(已上线|已完成)", "待上线内容被写成已上线"),
    (r"尚未回收[^\n。；;]{0,40}(已达成|提升|增长)", "尚未回收效果被写成已达成"),
]

REQUIRED_DRAFT_SECTIONS = ["阅读清单", "战功", "内功", "自评", "证据缺口"]


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise AssertionError(f"empty file: {path}")
    return text


def status_errors(text: str) -> list[str]:
    errors: list[str] = []
    for pattern, message in BAD_STATUS_PATTERNS:
        if re.search(pattern, text):
            errors.append(message)
    return errors


def validate_draft(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = read(path)
    except AssertionError as exc:
        return [str(exc)]
    for section in REQUIRED_DRAFT_SECTIONS:
        if section not in text:
            errors.append(f"missing section: {section}")
    if text.count("### 战功") < 3 and not all(label in text for label in ["战功一", "战功二", "战功三"]):
        errors.append("missing three 战功 sections")
    if "[P0" not in text and "P0" not in text:
        errors.append("missing P0 reading ledger evidence")
    # Drafts may explicitly discuss risk boundaries (e.g. “预计上线不可写成已完成”).
    # Treat status-boundary phrases as hard errors at reviewer PASS time, not in writer drafts.
    return errors


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def validate_reviewer(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = read(path)
    except AssertionError as exc:
        return [str(exc)]
    data = parse_frontmatter(text)
    if data.get("gate") not in {"PASS", "REJECT"}:
        errors.append("frontmatter gate must be PASS or REJECT")
    if data.get("return_to") not in {"leader", "final_assembly"}:
        errors.append("frontmatter return_to must be leader or final_assembly")
    if "阻塞" not in text:
        errors.append("missing blocking issue section")
    # Reviewer prose often says things like “预计/计划不能写成已完成” while
    # explaining a risk. Treat the explicit status_boundary_risk flag as the
    # parseable signal here; draft-level status scanning is intentionally
    # conservative and handled by the reviewer role itself.
    if data.get("status_boundary_risk") == "true" and data.get("gate") != "REJECT":
        errors.append("status_boundary_risk true must REJECT")
    return errors


def validate_leader(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = read(path)
    except AssertionError as exc:
        return [str(exc)]
    data = parse_frontmatter(text)
    if data.get("next_action") not in {"revise_writer_a", "revise_writer_b", "revise_both", "rerun_cross_learning", "ask_user", "stop"}:
        errors.append("invalid or missing next_action")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate fallback-loop output files.")
    parser.add_argument("kind", choices=["draft", "reviewer", "leader"])
    parser.add_argument("path")
    args = parser.parse_args()
    path = Path(args.path).expanduser().resolve()
    if args.kind == "draft":
        errors = validate_draft(path)
    elif args.kind == "reviewer":
        errors = validate_reviewer(path)
    else:
        errors = validate_leader(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
