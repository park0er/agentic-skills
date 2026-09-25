#!/usr/bin/env python3
"""Fuse Feishu whiteboards into a feishu2md-exported Markdown file.

WHY: feishu2md's built-in board export (lark_oapi download_as_image) fails with a
99991672 scope error for this app and silently drops whiteboards. The native
`feishu` CLI (@mi/feishu) CAN render boards. So feishu2md is run with
--keep-whiteboard-empty, which (in this patched feishu-docx) leaves placeholders
that embed the board token:

    【白板 序号N】<!--wb:TOKEN-->

This script finds each marker, renders that exact token via the feishu CLI, and
replaces the marker with a local image ref. Mapping is by TOKEN, so it is robust
to ordering / grid-embedded boards / count mismatches.

Usage:
    python3 fuse_whiteboards.py --md <exported.md> [--assets <dir>] [--feishu-bin feishu]
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

# 【白板 序号N】<!--wb:TOKEN-->   (TOKEN may be empty if feishu2md lacked it)
MARKER = re.compile(r"【白板 序号(\d+)】<!--wb:([A-Za-z0-9]*)-->")


def render_whiteboard(token: str, dest: Path, feishu_bin: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [feishu_bin, "fetch", token, "--type", "whiteboard", "--output", str(dest)],
        capture_output=True, text=True,
    )
    return dest.exists() and dest.stat().st_size > 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Fuse Feishu whiteboards into a feishu2md Markdown export.")
    ap.add_argument("--md", required=True, help="The feishu2md-exported .md file to patch.")
    ap.add_argument("--assets", help="Assets dir for rendered PNGs (default: sibling folder named like the .md stem).")
    ap.add_argument("--feishu-bin", default="feishu", help="feishu CLI binary (default: feishu on PATH).")
    args = ap.parse_args()

    md_path = Path(args.md).expanduser().resolve()
    if not md_path.exists():
        raise SystemExit(f"Markdown not found: {md_path}")
    assets = Path(args.assets).expanduser().resolve() if args.assets else md_path.with_suffix("")
    assets_name = assets.name

    text = md_path.read_text(encoding="utf-8")
    markers = MARKER.findall(text)  # list of (seq, token)
    if not markers:
        print("No 【白板 序号N】<!--wb:TOKEN--> markers found — nothing to fuse. "
              "(Export with --keep-whiteboard-empty using the patched feishu-docx.)")
        return 0

    ok = 0
    fail_tokens: list[str] = []
    for seq, token in markers:
        if not token:
            fail_tokens.append(f"序号{seq}(no-token)")
            continue
        if render_whiteboard(token, assets / f"{token}.png", args.feishu_bin):
            ok += 1
            print(f"  rendered {token} -> {assets_name}/{token}.png")
        else:
            fail_tokens.append(token)
            print(f"  FAILED to render {token}")

    def repl(m: re.Match) -> str:
        token = m.group(2)
        if token and (assets / f"{token}.png").exists():
            return f"![whiteboard]({assets_name}/{token}.png)"
        return m.group(0)  # leave marker if not rendered

    md_path.write_text(MARKER.sub(repl, text), encoding="utf-8")
    print(f"Fused {ok}/{len(markers)} whiteboard(s) in {md_path.name}."
          + (f" Unrendered: {fail_tokens}" if fail_tokens else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
