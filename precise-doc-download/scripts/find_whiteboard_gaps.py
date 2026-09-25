#!/usr/bin/env python3
"""Find likely weak whiteboard/canvas exports in Markdown material folders."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = [
    re.compile(r"white\s*board|whiteboard|board_token|canvas", re.IGNORECASE),
    re.compile(r"白板|画板|思维笔记|mindnote"),
    re.compile(r"keep[-_ ]?whiteboard[-_ ]?empty", re.IGNORECASE),
    re.compile(r"<!--\s*(whiteboard|board|canvas)", re.IGNORECASE),
]

EMPTY_HINTS = [
    re.compile(r"^\s*#+\s*(白板|画板|Whiteboard|Canvas)\b", re.IGNORECASE),
    re.compile(r"^\s*!\[[^\]]*(白板|画板|whiteboard|canvas)[^\]]*\]\(\s*\)\s*$", re.IGNORECASE),
]


def find_matches(root: Path) -> list[tuple[Path, int, str]]:
    matches: list[tuple[Path, int, str]] = []
    for markdown_path in sorted(root.rglob("*.md")):
        try:
            lines = markdown_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = markdown_path.read_text(errors="replace").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if any(pattern.search(line) for pattern in PATTERNS) or any(pattern.search(line) for pattern in EMPTY_HINTS):
                matches.append((markdown_path, line_number, line.strip()))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan exported Markdown for likely whiteboard/canvas gaps.")
    parser.add_argument("root", help="Export directory to scan.")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Directory does not exist: {root}")

    matches = find_matches(root)
    if not matches:
        print("No likely whiteboard/canvas gaps found.")
        return 0

    print("Likely whiteboard/canvas items needing native Feishu fallback:")
    for markdown_path, line_number, line in matches:
        print(f"{markdown_path}:{line_number}: {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
