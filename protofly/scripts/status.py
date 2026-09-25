#!/usr/bin/env python3
"""Quick health check: is `protofly` wired up in mcporter and reachable?

Usage:
    status.py            # human output, exits 0 if healthy
    status.py --json     # emits JSON status object

Useful before operating on the user's behalf — surfaces "token expired"
or "not on VPN" *before* a confusing failure mid-workflow.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import subprocess
import sys
import time
from pathlib import Path

CONFIG_PATH = Path.home() / ".mcporter" / "mcporter.json"


def b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def read_token_exp() -> int | None:
    if not CONFIG_PATH.is_file():
        return None
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        return None
    server = (cfg.get("mcpServers") or {}).get("protofly")
    if not server:
        return None
    headers = server.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    token = auth.removeprefix("Bearer ").strip()
    if token.count(".") != 2:
        return None
    try:
        payload = json.loads(b64url_decode(token.split(".")[1]))
    except Exception:  # noqa: BLE001
        return None
    return payload.get("exp")


def main() -> int:
    ap = argparse.ArgumentParser(description="Check protofly mcporter health.")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    out: dict[str, object] = {"config_path": str(CONFIG_PATH)}

    if not CONFIG_PATH.is_file():
        out["state"] = "not_configured"
        out["hint"] = "Run install_token.py with a fresh JWT from https://protofly.v.mitvos.com"
        if args.json_out:
            json.dump(out, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print("✗ not configured — run install_token.py")
        return 1

    exp = read_token_exp()
    if exp is None:
        out["state"] = "config_present_but_no_token"
        out["hint"] = "Reinstall with install_token.py"
    else:
        secs_left = exp - int(time.time())
        out["token_expires_at"] = _dt.datetime.fromtimestamp(exp).isoformat()
        out["token_seconds_left"] = secs_left
        if secs_left <= 0:
            out["state"] = "token_expired"
        elif secs_left < 7 * 86400:
            out["state"] = "token_expiring_soon"
        else:
            out["state"] = "token_ok"

    smoke = subprocess.run(
        ["mcporter", "call", "protofly.list_resources", "page:1", "page_size:1", "--output", "json"],
        check=False, text=True, capture_output=True,
    )
    out["smoke_test_returncode"] = smoke.returncode
    if smoke.returncode == 0:
        try:
            body = json.loads(smoke.stdout)
            out["resources_total"] = body.get("total")
            out["reachable"] = True
        except json.JSONDecodeError:
            out["reachable"] = True
            out["raw"] = smoke.stdout[:200]
    else:
        out["reachable"] = False
        out["error"] = (smoke.stderr or smoke.stdout).strip()[:300]

    if args.json_out:
        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        state = out.get("state", "?")
        if out.get("reachable") and state == "token_ok":
            print(f"✓ protofly healthy. Resources owned: {out.get('resources_total', '?')}")
            print(f"  Token expires: {out.get('token_expires_at')}")
        else:
            print(f"✗ state={state} reachable={out.get('reachable')}")
            if "hint" in out:
                print(f"  hint: {out['hint']}")
            if "error" in out:
                print(f"  error: {out['error']}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
