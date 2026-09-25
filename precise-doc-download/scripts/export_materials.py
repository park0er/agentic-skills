#!/usr/bin/env python3
"""Run the local feishu2md exporter safely for project material imports."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_TOOL_ROOT = Path("/Users/park0er/coding/PerKnowledgeBase/feishu2md")


def quote_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run(command: list[str], cwd: Path, dry_run: bool) -> None:
    print(f"$ (cd {cwd} && {quote_command(command)})")
    if dry_run:
        return
    subprocess.run(command, cwd=str(cwd), check=True)


def require_toolchain(tool_root: Path) -> None:
    required = [
        tool_root / "scripts" / "feishu_exporter.py",
        tool_root / "scripts" / "fix_links.py",
        tool_root / "scripts" / "audit_staging.py",
        tool_root / "feishu-docx",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing feishu2md toolchain files:\n" + "\n".join(missing))


def build_export_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    command = [sys.executable, "scripts/feishu_exporter.py", args.mode, args.source, "--out-dir", str(out_dir)]
    if args.mode in {"folder", "wiki"} and args.only_docs:
        command.append("--only-docs")
    if args.mode == "wiki" and args.exclude:
        command.append("--exclude")
        command.extend(args.exclude)
    if args.keep_whiteboard_empty:
        command.append("--keep-whiteboard-empty")
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Feishu materials with the local feishu2md pipeline.")
    parser.add_argument("mode", choices=["single", "folder", "wiki"], help="Source type to export.")
    parser.add_argument("source", help="Doc URL/token, folder token, or wiki space ID.")
    parser.add_argument("--out-dir", required=True, help="Project output directory for exported materials.")
    parser.add_argument("--tool-root", default=str(DEFAULT_TOOL_ROOT), help="Path to the feishu2md repository.")
    parser.add_argument("--only-docs", action="store_true", help="For folder/wiki exports, skip sheets and files.")
    parser.add_argument("--exclude", nargs="+", help="For wiki exports, title substrings to exclude.")
    parser.add_argument("--keep-whiteboard-empty", action="store_true", help="Keep numbered empty whiteboard placeholders.")
    parser.add_argument("--skip-fix-links", action="store_true", help="Skip feishu2md link rewriting.")
    parser.add_argument("--skip-audit", action="store_true", help="Skip export audit report generation.")
    parser.add_argument(
        "--skip-whiteboard-fusion",
        action="store_true",
        help="Skip the post-export whiteboard fusion step (single mode renders boards via the feishu CLI).",
    )
    parser.add_argument("--feishu-bin", default="feishu", help="feishu CLI binary used for whiteboard rendering (default: feishu on PATH).")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tool_root = Path(args.tool_root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    require_toolchain(tool_root)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Whiteboard fusion (single mode): feishu2md's own board export fails with a
    # 99991672 scope error and drops boards, so we keep token-bearing placeholders
    # and render them via the feishu CLI afterwards. Works for ALL modes because the
    # placeholder embeds the board token, so each exported .md is self-describing.
    fuse_enabled = not args.skip_whiteboard_fusion
    if fuse_enabled and not args.keep_whiteboard_empty:
        args.keep_whiteboard_empty = True

    run(build_export_command(args, out_dir), tool_root, args.dry_run)

    if not args.skip_fix_links:
        run([sys.executable, "scripts/fix_links.py", str(out_dir)], tool_root, args.dry_run)

    if not args.skip_audit:
        report_dir = out_dir / "Export_Audit_Report"
        run(
            [
                sys.executable,
                "scripts/audit_staging.py",
                "--dir",
                str(out_dir),
                "--export-to",
                str(report_dir),
            ],
            tool_root,
            args.dry_run,
        )

    if fuse_enabled and not args.dry_run:
        fuse_script = Path(__file__).resolve().parent / "fuse_whiteboards.py"
        md_files = [p for p in sorted(out_dir.rglob("*.md")) if "Export_Audit_Report" not in p.parts]
        if not md_files:
            print("⚠️  whiteboard fusion skipped: no .md found in out-dir.")
        for md in md_files:
            run(
                [
                    sys.executable, str(fuse_script),
                    "--md", str(md),
                    "--feishu-bin", args.feishu_bin,
                ],
                out_dir,
                False,
            )
    elif fuse_enabled and args.dry_run:
        print("(dry-run) would fuse whiteboards via the feishu CLI for every exported .md")

    print(f"\nDone. Export directory: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
