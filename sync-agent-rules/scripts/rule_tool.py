#!/usr/bin/env python3
"""Mechanical safety rails for sync-agent-rules. Does NOT author content.

The agent edits the rule files itself (placement, heading, wording); this tool
only backs up, locates, and verifies the marker blocks so edits stay idempotent.

Subcommands:
  backup                       back up all targets to <file>.bak-<ts>, print paths
  locate  --topic <slug>       report whether/where each file has the topic block
  verify  --topic <slug>       exit 1 unless every file has exactly one block
Common:
  --targets-file <json>        JSON array of target paths (override defaults; testing)
"""
import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_TARGETS = [
    os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/ClaudeSync/dotclaude/CLAUDE.md"),
    os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/CodexSync/dotcodex/AGENTS.md"),
    os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/GeminiSync/dotgemini/config/GEMINI.md"),
]


def targets(args) -> list[str]:
    if args.targets_file:
        return json.loads(Path(args.targets_file).read_text())
    return DEFAULT_TARGETS


def begin_marker(topic: str) -> str:
    return f"<!-- BEGIN agent-rule:{topic} -->"


def block_re(topic: str):
    return re.compile(
        rf"<!-- BEGIN agent-rule:{re.escape(topic)} -->.*?<!-- END agent-rule:{re.escape(topic)} -->",
        re.DOTALL,
    )


def cmd_backup(args) -> int:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for t in targets(args):
        if not Path(t).exists():
            print(f"  WARN missing: {t}")
            continue
        bak = f"{t}.bak-{ts}"
        shutil.copy2(t, bak)
        print(f"  backup: {bak}")
    return 0


def cmd_locate(args) -> int:
    rx = block_re(args.topic)
    for t in targets(args):
        if not Path(t).exists():
            print(f"  MISSING FILE: {t}")
            continue
        text = Path(t).read_text(encoding="utf-8")
        m = rx.search(text)
        if m:
            start_line = text[: m.start()].count("\n") + 1
            end_line = text[: m.end()].count("\n") + 1
            print(f"  PRESENT  {Path(t).name}: lines {start_line}-{end_line}")
        else:
            print(f"  ABSENT   {Path(t).name}: no block for '{args.topic}'")
    return 0


def cmd_verify(args) -> int:
    ok = True
    for t in targets(args):
        if not Path(t).exists():
            print(f"  WARN missing (skipped): {t}")
            continue
        text = Path(t).read_text(encoding="utf-8")
        n_begin = text.count(begin_marker(args.topic))
        n_block = len(block_re(args.topic).findall(text))
        status = "OK" if (n_begin == 1 and n_block == 1) else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  {status}  {Path(t).name}: begin={n_begin} complete_blocks={n_block}")
    print("verification:", "all OK" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical helper for sync-agent-rules.")
    ap.add_argument("--targets-file", help="JSON array of target paths (testing override).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup")
    lo = sub.add_parser("locate"); lo.add_argument("--topic", required=True)
    ve = sub.add_parser("verify"); ve.add_argument("--topic", required=True)
    args = ap.parse_args()
    return {"backup": cmd_backup, "locate": cmd_locate, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
