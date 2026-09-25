#!/usr/bin/env python3
"""Register the proto-fly MCP server in ~/.mcporter/mcporter.json.

Usage:
    printf %s '<TOKEN>' | python3 install_token.py

Why stdin: keeps the JWT out of shell history and `ps` listings. Use
`printf %s` (not `echo`) so backslashes / trailing newlines don't get
mangled. Wrap in single quotes so `$`, backticks, and `!` stay literal.

What this does:
    1. Validates the token shape (JWT-ish: three base64url segments).
    2. Decodes the payload to check `exp` (warns if <7 days, errors if expired).
    3. Removes any prior `protofly` entry from mcporter's home config.
    4. Re-adds it with the URL, Authorization header, and description.
    5. Smoke-tests `list_resources` to confirm the token actually works.
"""

from __future__ import annotations

import base64
import datetime as _dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROTOFLY_URL = "https://protofly-mcp.v.mitvos.com/mcp"
DESCRIPTION = "小米内网 HTML 原型托管 (proto-fly)"
WARN_DAYS = 7


def die(msg: str, code: int = 1) -> None:
    print(f"install_token: {msg}", file=sys.stderr)
    sys.exit(code)


def b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def validate_token(token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", token):
        die("token does not look like a JWT (expected 3 base64url segments separated by dots)")
    parts = token.split(".")
    try:
        payload = json.loads(b64url_decode(parts[1]))
    except Exception as exc:  # noqa: BLE001
        die(f"failed to decode JWT payload: {exc}")
    exp = payload.get("exp")
    if not isinstance(exp, int):
        die("JWT payload missing numeric `exp` field — token may be malformed")
    now = int(time.time())
    if exp <= now:
        die(f"token expired at {_dt.datetime.fromtimestamp(exp)} (now {_dt.datetime.fromtimestamp(now)})")
    days_left = (exp - now) / 86400
    if days_left < WARN_DAYS:
        print(f"  warn: token expires in {days_left:.1f} days — refresh soon", file=sys.stderr)
    return payload


def run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def main() -> int:
    token = sys.stdin.read().strip()
    if not token:
        die("expected token on stdin (use: printf %s '<TOKEN>' | install_token.py)")

    print("[1/4] validate token shape and expiry")
    payload = validate_token(token)
    print(f"  ok: open_id={payload.get('open_id', '?')} scopes={payload.get('scopes', [])}")

    print("[2/4] remove any prior protofly entry (ignored if missing)")
    try:
        run(["mcporter", "config", "remove", "protofly"], check=False)
    except FileNotFoundError:
        die("`mcporter` not found in PATH — install via `npm i -g mcporter` first")

    print("[3/4] register protofly in ~/.mcporter/mcporter.json")
    add = run(
        [
            "mcporter", "config", "add", "protofly",
            "--url", PROTOFLY_URL,
            "--header", f"Authorization=Bearer {token}",
            "--description", DESCRIPTION,
            "--scope", "home",
        ],
        check=False,
    )
    if add.returncode != 0:
        die(f"mcporter config add failed:\nstdout: {add.stdout}\nstderr: {add.stderr}")
    print(f"  {add.stdout.strip() or 'added'}")

    print("[4/4] smoke-test: list one resource")
    smoke = run(
        ["mcporter", "call", "protofly.list_resources", "page:1", "page_size:1", "--output", "json"],
        check=False,
    )
    if smoke.returncode != 0:
        die(
            "smoke test failed — token registered but server rejected it.\n"
            f"stdout: {smoke.stdout}\nstderr: {smoke.stderr}\n"
            "Likely causes: (a) you're not on Xiaomi VPN, (b) token revoked, "
            "(c) clock skew. Re-run after fixing."
        )
    try:
        body = json.loads(smoke.stdout)
        total = body.get("total", "?")
        print(f"  ok: server reachable, total resources owned = {total}")
    except json.JSONDecodeError:
        print(f"  ok (raw): {smoke.stdout.strip()[:200]}")

    cfg_path = Path.home() / ".mcporter" / "mcporter.json"
    print()
    print(f"✓ protofly installed. Config: {cfg_path}")
    print("  Try: mcporter call protofly.list_resources page:1 page_size:5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
