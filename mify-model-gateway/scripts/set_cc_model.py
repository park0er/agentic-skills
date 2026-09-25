#!/usr/bin/env python3
"""Write a Mify model id into Claude Code's user-level settings.json.

Claude Code reads ~/.claude/settings.json. Three env vars map requests by tier:

    ANTHROPIC_DEFAULT_HAIKU_MODEL   (small / cheap)
    ANTHROPIC_DEFAULT_SONNET_MODEL  (default)
    ANTHROPIC_DEFAULT_OPUS_MODEL    (big / expensive)

Mify speaks both OpenAI and Anthropic protocols. At base URL
https://api.llm.mioffice.cn/anthropic Claude Code can talk to it natively; no
claude-code-router or other middleware needed.

Usage:
  set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet
  set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet,haiku
  set_cc_model.py --model xiaomi/kimi-k2.5 --tier all --dry-run
  set_cc_model.py --revert

Safety:
- Pre-checks that model exists on Mify and is type=llm.
- Never overwrites a non-Mify ANTHROPIC_BASE_URL without --force-url.
- Never overwrites an existing ANTHROPIC_AUTH_TOKEN/ANTHROPIC_API_KEY.
- Backs up settings.json to settings.json.bak.YYYYMMDD-HHMMSS before writing.
- Runs a minimal /anthropic/v1/messages smoke test; auto-reverts on failure.
- Idempotent: re-running the same command is a no-op when nothing changes.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY_HOST = "https://api.llm.mioffice.cn"
OPENAI_LIST_URL = f"{GATEWAY_HOST}/v1/models"
MIFY_BASE_URL = f"{GATEWAY_HOST}/anthropic"

# Local proxy hosts that are also valid Mify-compatible endpoints
# (claude_desktop_proxy.py on port 41414, or fallback ports 41415-41514)
LOCAL_PROXY_HOSTS = tuple(f"127.0.0.1:{p}" for p in range(41414, 41515)) + tuple(
    f"localhost:{p}" for p in range(41414, 41515)
)
MIFY_RECOGNIZED_HOSTS = ("api.llm.mioffice.cn", "model.mify.ai.srv", *LOCAL_PROXY_HOSTS)

TIER_ENV_VARS = {
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
}
TIER_ORDER = ["haiku", "sonnet", "opus"]

MODEL_FORMAT = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+$")


# ---------- tiny helpers ----------

def die(msg: str, code: int = 1) -> "None":
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def load_mify_key() -> str:
    """Find the Mify key via shared cascading resolver."""
    from _keyloader import load_mify_key as _load
    return _load()


def parse_tiers(raw: str) -> list[str]:
    if raw == "all":
        return list(TIER_ORDER)
    out: list[str] = []
    for piece in raw.split(","):
        piece = piece.strip().lower()
        if piece not in TIER_ENV_VARS:
            die(f"Unknown tier {piece!r}. Valid: haiku, sonnet, opus, all.")
        if piece not in out:
            out.append(piece)
    if not out:
        die("--tier cannot be empty.")
    return out


# ---------- Mify calls ----------

def fetch_models(api_key: str) -> list[dict]:
    req = urllib.request.Request(
        OPENAI_LIST_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")).get("data", [])
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} from {OPENAI_LIST_URL}: {e.reason}. Key invalid?")
    except urllib.error.URLError as e:
        die(f"Cannot reach {OPENAI_LIST_URL}: {e.reason}. On Xiaomi intranet/VPN?")


def verify_model_usable(models: list[dict], call_as: str) -> None:
    owner, _, mid = call_as.partition("/")
    hits = [m for m in models if m["id"] == mid and m.get("owned_by") == owner]
    if not hits:
        id_hits = [m for m in models if m["id"] == mid]
        if id_hits:
            owners = sorted({m.get("owned_by", "?") for m in id_hits})
            die(
                f"{call_as!r} not found on Mify. "
                f"The id {mid!r} exists under: {', '.join(owners)}. "
                f"Did you mean one of those owners?"
            )
        die(
            f"Model {call_as!r} not found on Mify. "
            "Double-check with list_models.py --grep <part-of-id>."
        )
    model = hits[0]
    mtype = (model.get("model_type") or "").lower()
    if mtype != "llm":
        die(
            f"{call_as!r} has model_type={mtype!r}. Only 'llm' models work as chat tiers. "
            "Embedding / TTS / rerank cannot back Claude Code's Haiku/Sonnet/Opus slots."
        )


def smoke_test_anthropic(base_url: str, token: str, model: str) -> tuple[bool, str]:
    """POST a minimal message to /anthropic/v1/messages. Return (ok, detail)."""
    url = base_url.rstrip("/") + "/v1/messages"
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "hi"}],
        }
    ).encode("utf-8")

    # Mify's Anthropic bridge accepts x-api-key (Anthropic's own header).
    # If the caller has a plain Bearer key (ANTHROPIC_AUTH_TOKEN vs ANTHROPIC_API_KEY),
    # it still wires up because Mify treats both as the same auth secret.
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "x-api-key": token,
            "authorization": f"Bearer {token}",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            content = payload.get("content") or []
            text = ""
            if content and isinstance(content, list):
                text = content[0].get("text", "") if isinstance(content[0], dict) else ""
            preview = text.strip()
            if preview:
                return True, f"HTTP {resp.status}, reply: {preview!r}"
            return True, f"HTTP {resp.status} (empty reply — OK, pipeline works)"
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        return False, f"HTTP {e.code} {e.reason}: {detail}"
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"


# ---------- settings.json surgery ----------

def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}. Fix the file manually first.")


def plan_mutation(
    current: dict,
    call_as: str,
    tiers: list[str],
    mify_key: str,
    force_url: bool,
) -> tuple[dict, list[str]]:
    """Return the new settings dict plus a human-readable list of changes."""
    new = json.loads(json.dumps(current))  # deep copy
    env = new.setdefault("env", {})
    changes: list[str] = []

    existing_url = env.get("ANTHROPIC_BASE_URL")
    if not existing_url:
        env["ANTHROPIC_BASE_URL"] = MIFY_BASE_URL
        changes.append(f"+ ANTHROPIC_BASE_URL = {MIFY_BASE_URL}  (filled: was missing)")
    elif not any(h in existing_url for h in MIFY_RECOGNIZED_HOSTS):
        if not force_url:
            die(
                f"ANTHROPIC_BASE_URL is set to {existing_url!r}, not Mify.\n"
                "Refusing to overwrite. Re-run with --force-url if you really want\n"
                f"to switch this machine's Claude Code over to Mify ({MIFY_BASE_URL})."
            )
        env["ANTHROPIC_BASE_URL"] = MIFY_BASE_URL
        changes.append(
            f"~ ANTHROPIC_BASE_URL: {existing_url} -> {MIFY_BASE_URL}  (--force-url)"
        )

    if not env.get("ANTHROPIC_AUTH_TOKEN") and not env.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_AUTH_TOKEN"] = mify_key
        changes.append("+ ANTHROPIC_AUTH_TOKEN = <mify key>  (filled: was missing)")

    for tier in tiers:
        var = TIER_ENV_VARS[tier]
        before = env.get(var)
        if before == call_as:
            continue  # idempotent: no-op on exact match
        env[var] = call_as
        if before is None:
            changes.append(f"+ {var} = {call_as}  ({tier} tier)")
        else:
            changes.append(f"~ {var}: {before} -> {call_as}  ({tier} tier)")

    return new, changes


def dump_settings(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def backup_file(path: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.copy2(path, bak)
    return bak


def latest_backup(path: Path) -> Path | None:
    backups = sorted(
        path.parent.glob(path.name + ".bak.*"),
        key=lambda p: p.stat().st_mtime,
    )
    return backups[-1] if backups else None


# ---------- command handlers ----------

def cmd_revert(path: Path) -> None:
    bak = latest_backup(path)
    if not bak:
        die(f"No backup found next to {path} (nothing like {path.name}.bak.*).")
    shutil.copy2(bak, path)
    print(f"✓ Restored {path} from {bak.name}")
    print("  Restart Claude Code for changes to pick up.")


def cmd_set(args: argparse.Namespace) -> None:
    if not MODEL_FORMAT.match(args.model):
        die(
            f"--model {args.model!r} does not look like '{{owner}}/{{id}}'. "
            "Mify's Anthropic endpoint rejects bare ids."
        )

    tiers = parse_tiers(args.tier)
    mify_key = load_mify_key()

    models = fetch_models(mify_key)
    verify_model_usable(models, args.model)

    path = settings_path()
    current = load_settings(path)
    new, changes = plan_mutation(current, args.model, tiers, mify_key, args.force_url)

    if not changes:
        print(f"· No change needed: {args.model} already set for tier(s) {', '.join(tiers)}.")
        print(f"· Current settings.json: {path}")
        return

    print("Planned changes to", path)
    for c in changes:
        print(" ", c)
    print()

    if args.dry_run:
        print("— dry run — no files touched. Re-run without --dry-run to apply.")
        return

    had_file = path.exists()
    if had_file:
        bak = backup_file(path)
        print(f"✓ Backup: {bak}")
    else:
        bak = None
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"· No prior {path} — creating fresh.")

    path.write_text(dump_settings(new), encoding="utf-8")
    print(f"✓ Wrote {path}")

    env = new["env"]
    token = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY")
    base_url = env.get("ANTHROPIC_BASE_URL", MIFY_BASE_URL)

    print(f"· Smoke test: POST {base_url}/v1/messages  model={args.model}")
    ok, detail = smoke_test_anthropic(base_url, token, args.model)
    if ok:
        print(f"✓ Smoke test passed. {detail}")
        print()
        print("Done. Restart Claude Code (close and re-open the terminal) so it re-reads settings.json.")
        return

    print(f"✗ Smoke test failed: {detail}", file=sys.stderr)
    if bak is not None:
        shutil.copy2(bak, path)
        print(f"✓ Reverted {path} from {bak.name}", file=sys.stderr)
    else:
        path.unlink(missing_ok=True)
        print(f"✓ Removed {path} (was freshly created).", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set a Mify model as Claude Code's Haiku/Sonnet/Opus tier.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet\n"
            "  set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet,haiku --dry-run\n"
            "  set_cc_model.py --model ppio/pa/claude-opus-4-7 --tier opus\n"
            "  set_cc_model.py --revert\n"
            "\n"
            "Tiers correspond to Claude Code's ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS}_MODEL env vars.\n"
            "Use 'all' to set every tier to the same model.\n"
        ),
    )
    parser.add_argument("--model", help="'{owner}/{id}' on Mify, e.g. xiaomi/kimi-k2.5.")
    parser.add_argument(
        "--tier",
        help="haiku | sonnet | opus | all | comma-separated combo (e.g. 'haiku,sonnet').",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print the planned diff and exit without writing.",
    )
    parser.add_argument(
        "--revert", action="store_true",
        help="restore settings.json from the most recent .bak.* next to it.",
    )
    parser.add_argument(
        "--force-url", action="store_true",
        help="rewrite ANTHROPIC_BASE_URL to Mify even if it currently points elsewhere.",
    )
    args = parser.parse_args()

    path = settings_path()

    if args.revert:
        if args.model or args.tier:
            die("--revert does not take --model/--tier.")
        cmd_revert(path)
        return

    if not args.model or not args.tier:
        parser.error("--model and --tier are both required (unless --revert).")

    cmd_set(args)


if __name__ == "__main__":
    main()
