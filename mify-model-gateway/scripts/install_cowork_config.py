#!/usr/bin/env python3
"""Configure Claude Desktop (Cowork 3P) to use the Mify gateway.

Current Claude Desktop releases store local 3P configs under:

  ~/Library/Application Support/Claude-3p/configLibrary/

The active config is selected by configLibrary/_meta.json. This script writes
that local JSON format, not the older user-level plist path.

Important compatibility note:
Claude Desktop 1.6259+ validates gateway inferenceModels as Anthropic/Claude
model routes. Non-Claude Mify models such as Kimi, Qwen, GPT, MiMo, DeepSeek
are valid for Claude Code through Mify, but no longer valid in Claude Desktop
Cowork 3P's model picker.

Default behavior is dry-run: shows what would change, writes nothing. Use
--apply to commit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


# ---- constants --------------------------------------------------------------

DOMAIN = "com.anthropic.claudefordesktop"  # legacy plist domain only

APP_DIR = Path.home() / "Library/Application Support/Claude-3p"
CONFIG_LIBRARY = APP_DIR / "configLibrary"
META_FILE = CONFIG_LIBRARY / "_meta.json"
LEGACY_CONFIG = APP_DIR / "claude_desktop_config.json"

MANAGED_KEYS = [
    "inferenceProvider",
    "inferenceGatewayBaseUrl",
    "inferenceGatewayApiKey",
    "disableDeploymentModeChooser",
    "deploymentOrganizationUuid",
    "coworkEgressAllowedHosts",
    "inferenceModels",
]

DEFAULT_BASE_URL = "https://api.llm.mioffice.cn/anthropic"
DEFAULT_EGRESS_HOSTS = ["*"]
MIMO_TEST_MODEL = "xiaomi/mimo-v2.5-pro"
CREDS_FILE = Path.home() / ".config/mify/credentials"
DEPLOY_UUID_FILE = Path.home() / ".config/mify/cowork-deployment-uuid"

SCRIPT_DIR = Path(__file__).parent
LIST_MODELS = SCRIPT_DIR / "list_models.py"
FETCH_AA = SCRIPT_DIR / "fetch_aa_rankings.py"
CONTEXT_TAG_RE = re.compile(r"\[(?:1m|1M)\]$")
DISPLAY_CONTEXT_TAG = "[1m]"

# Fallback only. auto_generate_models() prefers the live Mify catalog.
FALLBACK_CLAUDE_MODELS: list[dict[str, Any]] = [
    {"name": "ppio/pa/claude-opus-4-7", "supports1m": True},
    {"name": "ppio/pa/claude-opus-4-6", "supports1m": True},
    {"name": "ppio/pa/claude-sonnet-4-6", "supports1m": True},
    {"name": "ppio/pa/claude-haiku-4-5", "supports1m": True},
]


# ---- helpers ----------------------------------------------------------------


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    key = os.environ.get("MIFY_API_KEY")
    if key:
        return key
    if CREDS_FILE.exists():
        for line in CREDS_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("export MIFY_API_KEY="):
                return line.split("=", 1)[1].strip("'\"")
            if line.startswith("MIFY_API_KEY="):
                return line.split("=", 1)[1].strip("'\"")
    die(
        "no MIFY_API_KEY in env or ~/.config/mify/credentials; "
        "pass --api-key or run install_token.py first"
    )


def load_api_key_optional() -> str | None:
    try:
        return load_api_key(None)
    except SystemExit:
        return None


def load_or_create_deployment_uuid() -> str:
    """Persist a UUID across reinstalls so telemetry stays stable."""
    if DEPLOY_UUID_FILE.exists():
        val = DEPLOY_UUID_FILE.read_text().strip()
        if val:
            return val
    DEPLOY_UUID_FILE.parent.mkdir(parents=True, exist_ok=True)
    new = str(uuid.uuid4())
    DEPLOY_UUID_FILE.write_text(new)
    os.chmod(DEPLOY_UUID_FILE, 0o600)
    return new


def run_json_script(path: Path, *args: str) -> dict | list | None:
    """Invoke a sibling script with --json and parse the output."""
    env = os.environ.copy()
    if not env.get("MIFY_API_KEY"):
        key = load_api_key_optional()
        if key:
            env["MIFY_API_KEY"] = key
    try:
        out = subprocess.run(
            [sys.executable, str(path), "--json", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
        )
        return json.loads(out.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(
            f"warn: {path.name} failed ({type(e).__name__}); auto-models may be incomplete",
            file=sys.stderr,
        )
        return None


def fetch_aa_models() -> list[dict]:
    data = run_json_script(FETCH_AA, "--top", "80")
    if isinstance(data, dict) and "models" in data:
        return data["models"]
    return []


def fetch_mify_llms() -> list[dict]:
    data = run_json_script(LIST_MODELS, "--type", "llm", "--all")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("models", [])
    return []


def strip_context_tag(model_name: str) -> str:
    return CONTEXT_TAG_RE.sub("", model_name)


def display_model_name(model_name: str, supports_1m: bool) -> str:
    base = strip_context_tag(model_name)
    return f"{base}{DISPLAY_CONTEXT_TAG}" if supports_1m else base


def is_claude_route(call_as: str) -> bool:
    """Claude Desktop 1.6259+ only accepts Anthropic/Claude gateway routes."""
    s = strip_context_tag(call_as).lower()
    tail = s.split("/")[-1]
    return "claude-" in tail or "/anthropic/claude-" in s or s.startswith("anthropic/claude-")


def call_as_from_row(row: dict) -> str | None:
    model_id = row.get("id") or row.get("model_id") or ""
    owned_by = row.get("owned_by") or row.get("owner") or ""
    if not model_id or not owned_by:
        return None
    return f"{owned_by}/{model_id}"


def aa_context_lookup(aa_models: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in aa_models:
        slug = (m.get("slug") or "").lower().replace(".", "-")
        ctx = m.get("context_window") or 0
        if slug and ctx:
            out[slug] = int(ctx)
    return out


def slug_candidates(call_as: str) -> list[str]:
    tail = strip_context_tag(call_as).split("/")[-1].lower().replace(".", "-")
    return [tail]


def has_1m_context(call_as: str, aa_ctx: dict[str, int]) -> bool:
    known_1m = {
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
    }
    if any(slug in known_1m for slug in slug_candidates(call_as)):
        return True
    return any(aa_ctx.get(slug, 0) >= 1_000_000 for slug in slug_candidates(call_as))


def model_entry(call_as: str, aa_ctx: dict[str, int]) -> dict[str, Any]:
    supports_1m = has_1m_context(call_as, aa_ctx)
    entry: dict[str, Any] = {"name": display_model_name(call_as, supports_1m)}
    if supports_1m:
        entry["supports1m"] = True
    return entry


def model_sort_key(call_as: str) -> tuple[int, str]:
    s = call_as.lower()
    if "opus" in s:
        family = 0
    elif "sonnet" in s:
        family = 1
    elif "haiku" in s:
        family = 2
    else:
        family = 9
    # Desc-ish lexical version ordering inside each family by inverting through
    # a stable reverse later would be fussier than useful; newest Mify aliases
    # already tend to sort after older dated variants.
    return (family, s)


def live_generate_models() -> list[dict[str, Any]]:
    """Generate Claude Desktop-compatible model routes from Mify.

    Since Claude Desktop now rejects non-Anthropic gateway routes in
    inferenceModels, this deliberately filters Mify's catalog down to
    Claude/Anthropic routes only.
    """
    aa_ctx = aa_context_lookup(fetch_aa_models())
    rows = fetch_mify_llms()
    call_as = sorted(
        {c for row in rows if (c := call_as_from_row(row)) and is_claude_route(c)},
        key=model_sort_key,
    )
    if not call_as:
        print(
            "warn: no Claude routes found in Mify catalog; falling back to built-in Claude baseline",
            file=sys.stderr,
        )
        return list(FALLBACK_CLAUDE_MODELS)
    return [model_entry(name, aa_ctx) for name in call_as]


def verified_baseline_models() -> list[dict[str, Any]]:
    return [{**m, "name": display_model_name(m["name"], bool(m.get("supports1m")))} for m in FALLBACK_CLAUDE_MODELS]


def coerce_models(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        die("models JSON must be an array")
    out: list[dict[str, Any]] = []
    rejected: list[str] = []
    for item in raw:
        if isinstance(item, str):
            name = strip_context_tag(item)
            entry: dict[str, Any] = {"name": name}
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            name = strip_context_tag(item["name"])
            entry = dict(item)
            entry["name"] = name
        else:
            die("each model must be a string or an object with a string 'name'")
        if not is_claude_route(name):
            rejected.append(name)
            continue
        entry["name"] = display_model_name(name, bool(entry.get("supports1m")))
        out.append(entry)
    if rejected:
        print(
            "warn: skipping non-Claude model(s); Claude Desktop 1.6259+ rejects them:",
            file=sys.stderr,
        )
        for name in rejected:
            print(f"  - {name}", file=sys.stderr)
    if not out:
        die("no Claude-compatible models remain after filtering")
    return out


def redact(val: Any, keep: int = 10) -> Any:
    if isinstance(val, str) and val.startswith("sk-") and len(val) > keep + 4:
        return val[:keep] + "..." + f"(len={len(val)})"
    return val


def check_claude_running() -> list[str]:
    r = subprocess.run(["pgrep", "-f", "Claude.app"], capture_output=True, text=True)
    return r.stdout.strip().split() if r.stdout.strip() else []


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")


def active_config_id_and_meta() -> tuple[str | None, dict[str, Any]]:
    meta = read_json(META_FILE)
    if not isinstance(meta, dict):
        return None, {}
    applied = meta.get("appliedId")
    return (applied if isinstance(applied, str) and applied else None), meta


def read_active_config() -> tuple[str | None, dict[str, Any], dict[str, Any]]:
    active_id, meta = active_config_id_and_meta()
    if active_id:
        path = CONFIG_LIBRARY / f"{active_id}.json"
        data = read_json(path)
        if isinstance(data, dict):
            return active_id, data, meta

    # Compatibility: older local config stored enterpriseConfig here.
    legacy = read_json(LEGACY_CONFIG)
    if isinstance(legacy, dict) and isinstance(legacy.get("enterpriseConfig"), dict):
        return active_id, dict(legacy["enterpriseConfig"]), meta

    return active_id, {}, meta


def ensure_active_id(meta: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    active_id = meta.get("appliedId")
    entries = meta.get("entries")
    if isinstance(active_id, str) and active_id:
        if not isinstance(entries, list):
            meta["entries"] = [{"id": active_id, "name": "Default"}]
        return active_id, meta

    new_id = str(uuid.uuid4())
    return new_id, {"appliedId": new_id, "entries": [{"id": new_id, "name": "Default"}]}


def read_legacy_plist_keys() -> dict[str, str]:
    out: dict[str, str] = {}
    for key in MANAGED_KEYS:
        r = subprocess.run(["defaults", "read", DOMAIN, key], capture_output=True, text=True)
        if r.returncode == 0:
            out[key] = r.stdout.strip()
    return out


def delete_legacy_plist_keys() -> tuple[int, int]:
    deleted = absent = 0
    for key in MANAGED_KEYS:
        r = subprocess.run(["defaults", "delete", DOMAIN, key], capture_output=True, text=True)
        if r.returncode == 0:
            deleted += 1
        else:
            absent += 1
    return deleted, absent


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak.{stamp}")
    shutil.copy2(path, backup)
    return backup


def write_json_secure(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.chmod(path, 0o600)


def build_target(args, current: dict[str, Any]) -> dict[str, Any]:
    models = build_models_target(args)

    hosts = current.get("coworkEgressAllowedHosts") or DEFAULT_EGRESS_HOSTS
    if isinstance(args.egress_host, list) and args.egress_host:
        hosts = args.egress_host

    target: dict[str, Any] = {
        "inferenceProvider": "gateway",
        "inferenceGatewayBaseUrl": args.base_url,
        "inferenceGatewayApiKey": load_api_key(args.api_key),
        "disableDeploymentModeChooser": True,
        "deploymentOrganizationUuid": load_or_create_deployment_uuid(),
        "coworkEgressAllowedHosts": hosts,
        "inferenceModels": models,
    }
    return target


def summarize_models(models: Any) -> str:
    if not isinstance(models, list):
        return "(unset)"
    lines = []
    for m in models:
        if isinstance(m, dict):
            lines.append(f"  - {m.get('name')}")
        else:
            lines.append(f"  - {m}")
    return f"{len(models)} models:\n" + "\n".join(lines)


def short_value(key: str, val: Any) -> str:
    if val is None:
        return "(unset)"
    if key == "inferenceGatewayApiKey":
        return str(redact(val))
    if key == "inferenceModels":
        return summarize_models(val)
    return json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val


def show_diff(current: dict[str, Any], target: dict[str, Any]) -> None:
    print("== configLibrary diff (current -> target) ==")
    for key in MANAGED_KEYS:
        cur = current.get(key)
        new = target.get(key)
        if key == "inferenceModels":
            if cur == new:
                print(f"  {key}: unchanged")
            else:
                print(f"  {key}:")
                if cur is not None:
                    print(f"    current: {summarize_models(cur).splitlines()[0]}")
                print("    target : " + summarize_models(new).replace("\n", "\n             "))
            continue
        if cur == new:
            print(f"  {key}: unchanged ({short_value(key, new)})")
        else:
            print(f"  {key}: {short_value(key, cur)} -> {short_value(key, new)}")


def show_models_diff(current_models: Any, target_models: list[dict[str, Any]]) -> None:
    print("== inferenceModels diff (current -> target) ==")
    if current_models == target_models:
        print("  inferenceModels: unchanged")
        return
    if current_models is not None:
        print(f"  current: {summarize_models(current_models).splitlines()[0]}")
    else:
        print("  current: (unset)")
    print("  target : " + summarize_models(target_models).replace("\n", "\n           "))


def write_active_config(current: dict[str, Any], target: dict[str, Any], meta: dict[str, Any]) -> Path:
    active_id, new_meta = ensure_active_id(dict(meta))
    path = CONFIG_LIBRARY / f"{active_id}.json"
    merged = dict(current)
    merged.update(target)

    CONFIG_LIBRARY.mkdir(parents=True, exist_ok=True)
    backup_file(path)
    backup_file(META_FILE)
    write_json_secure(path, merged)
    write_json_secure(META_FILE, new_meta)
    return path


def write_models_only(models: list[dict[str, Any]], meta: dict[str, Any]) -> list[Path]:
    active_id, new_meta = ensure_active_id(dict(meta))
    active_path = CONFIG_LIBRARY / f"{active_id}.json"
    active = read_json(active_path)
    if not isinstance(active, dict):
        die(
            "no active config JSON exists to fix; run default provisioning first "
            "or create the configLibrary profile"
        )

    changed: list[Path] = []
    active = dict(active)
    active["inferenceModels"] = models
    CONFIG_LIBRARY.mkdir(parents=True, exist_ok=True)
    backup_file(active_path)
    backup_file(META_FILE)
    write_json_secure(active_path, active)
    write_json_secure(META_FILE, new_meta)
    changed.append(active_path)

    legacy = read_json(LEGACY_CONFIG)
    if isinstance(legacy, dict) and isinstance(legacy.get("enterpriseConfig"), dict):
        backup_file(LEGACY_CONFIG)
        legacy = dict(legacy)
        enterprise = dict(legacy["enterpriseConfig"])
        enterprise["inferenceModels"] = models
        legacy["enterpriseConfig"] = enterprise
        write_json_secure(LEGACY_CONFIG, legacy)
        changed.append(LEGACY_CONFIG)

    return changed


def build_models_target(args) -> list[dict[str, Any]]:
    if args.models_file:
        models = coerce_models(json.loads(Path(args.models_file).read_text()))
    elif args.live_models:
        models = live_generate_models()
    else:
        models = verified_baseline_models()

    if args.include_mimo_test and not any(m.get("name") == MIMO_TEST_MODEL for m in models):
        models.append({"name": display_model_name(MIMO_TEST_MODEL, True), "supports1m": True})
    return models


def validate_model_target(models: list[dict[str, Any]], include_mimo_test: bool) -> None:
    if not models:
        die("target inferenceModels is empty")
    allowed_non_claude = {MIMO_TEST_MODEL} if include_mimo_test else set()
    invalid = [
        m.get("name", "")
        for m in models
        if not is_claude_route(m.get("name", "")) and m.get("name", "") not in allowed_non_claude
    ]
    if invalid:
        die("target contains non-Claude inferenceModels; refusing to write")
    if include_mimo_test:
        print(
            f"warning: including non-Claude test model {MIMO_TEST_MODEL}; "
            "Claude Desktop 1.6259.x may reject this config."
        )
        print()


# ---- commands ---------------------------------------------------------------


def cmd_verify() -> int:
    active_id, current, _meta = read_active_config()
    print("=== Claude Desktop 3P local config ===")
    print(f"configLibrary: {CONFIG_LIBRARY}")
    print(f"active id    : {active_id or '(none)'}")
    if not current:
        print("(no active local 3P config found)")
    else:
        for key in MANAGED_KEYS:
            val = current.get(key)
            marker = "set" if val is not None else "unset"
            if key == "inferenceModels":
                print(f"  {key}: {marker} {summarize_models(val) if val is not None else ''}".rstrip())
            else:
                print(f"  {key}: {marker} {short_value(key, val) if val is not None else ''}".rstrip())

    legacy = read_legacy_plist_keys()
    print()
    if legacy:
        print(f"legacy plist managed keys still present in {DOMAIN}: {', '.join(sorted(legacy))}")
    else:
        print("legacy plist managed keys: none")

    pids = check_claude_running()
    if pids:
        print(f"\nClaude.app is running (PIDs {pids[:3]}). Quit and relaunch to pick up changes.")
    else:
        print("\nClaude.app not running; next launch will read current config.")
    return 0


def cmd_revert() -> int:
    active_id, current, meta = read_active_config()
    if current:
        active_id, new_meta = ensure_active_id(dict(meta))
        path = CONFIG_LIBRARY / f"{active_id}.json"
        cleaned = dict(current)
        for key in MANAGED_KEYS:
            cleaned.pop(key, None)
        backup_file(path)
        write_json_secure(path, cleaned)
        write_json_secure(META_FILE, new_meta)
        print(f"removed managed keys from active config: {path}")
    else:
        print("no active local config found")

    deleted, absent = delete_legacy_plist_keys()
    print(f"legacy plist cleanup: deleted {deleted}, absent {absent}")

    pids = check_claude_running()
    if pids:
        print("Claude.app is running. Quit and relaunch for the revert to take effect.")
    return 0


def cmd_apply(args) -> int:
    active_id, current, meta = read_active_config()
    target = build_target(args, current)
    validate_model_target(target["inferenceModels"], args.include_mimo_test)

    print(f"active config id: {active_id or '(will create)'}")
    show_diff(current, target)
    print()

    legacy = read_legacy_plist_keys()
    if legacy:
        print(
            "note: legacy plist keys are present; --apply will leave them alone, "
            "and --revert will clean them."
        )
        print()

    if not args.apply:
        print("dry-run - nothing written. Re-run with --apply to commit.")
        return 0

    path = write_active_config(current, target, meta)
    print(f"written: {path}")
    if args.include_mimo_test:
        print(f"models : {len(target['inferenceModels'])} routes (includes {MIMO_TEST_MODEL} test route)")
    else:
        print(f"models : {len(target['inferenceModels'])} Claude-compatible routes")

    pids = check_claude_running()
    if pids:
        print(
            "Claude.app is running. Fully quit Claude.app (Cmd+Q) and relaunch "
            "to activate the new config."
        )
    else:
        print("Claude.app not running. Next launch will read the new config.")
    return 0


def cmd_fix_models(args) -> int:
    active_id, current, meta = read_active_config()
    if not active_id:
        die("no active config id found; use install_cowork_config.py --apply for first-time setup")
    if not current:
        die("no active config found; use install_cowork_config.py --apply for first-time setup")

    models = build_models_target(args)
    validate_model_target(models, args.include_mimo_test)

    print(f"active config id: {active_id}")
    print("mode: fix-models (only inferenceModels will be changed)")
    show_models_diff(current.get("inferenceModels"), models)
    print()

    legacy = read_json(LEGACY_CONFIG)
    if isinstance(legacy, dict) and isinstance(legacy.get("enterpriseConfig"), dict):
        print("note: legacy claude_desktop_config.json enterpriseConfig will be kept in sync.")
        print()

    if not args.apply:
        print("dry-run - nothing written. Re-run with --fix-models --apply to commit.")
        return 0

    changed = write_models_only(models, meta)
    print("written:")
    for path in changed:
        print(f"  - {path}")
    if args.include_mimo_test:
        print(f"models : {len(models)} routes (includes {MIMO_TEST_MODEL} test route)")
    else:
        print(f"models : {len(models)} Claude-compatible routes")

    pids = check_claude_running()
    if pids:
        print(
            "Claude.app is running. Fully quit Claude.app (Cmd+Q) and relaunch "
            "to activate the model list."
        )
    else:
        print("Claude.app not running. Next launch will read the fixed model list.")
    return 0


# ---- main -------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Configure Claude Desktop 3P mode via the current configLibrary JSON. "
            "Default is dry-run; pass --apply to commit."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  install_cowork_config.py              # dry-run, verified Claude baseline\n"
            "  install_cowork_config.py --apply      # commit\n"
            "  install_cowork_config.py --fix-models # only repair model list\n"
            "  install_cowork_config.py --verify     # inspect only\n"
            "  install_cowork_config.py --revert     # remove managed keys\n"
            "  install_cowork_config.py --models-file claude_models.json\n"
        ),
    )
    p.add_argument("--apply", action="store_true", help="commit writes (default is dry-run)")
    p.add_argument("--verify", action="store_true", help="show current config and exit")
    p.add_argument("--revert", action="store_true", help="remove managed keys and exit")
    p.add_argument(
        "--fix-models",
        action="store_true",
        help="only replace inferenceModels in the active profile; preserve other config",
    )
    p.add_argument(
        "--models-file",
        help="JSON array of inferenceModels entries; non-Claude routes are skipped",
    )
    p.add_argument(
        "--live-models",
        action="store_true",
        help="use live Mify Claude routes instead of the verified baseline",
    )
    p.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"gateway base URL (default: {DEFAULT_BASE_URL})",
    )
    p.add_argument("--api-key", help="override MIFY_API_KEY from env/credentials file")
    p.add_argument(
        "--include-mimo-test",
        action="store_true",
        help=(
            f"append {MIMO_TEST_MODEL} as an explicit validation test; "
            "not for production default configs"
        ),
    )
    p.add_argument(
        "--egress-host",
        action="append",
        help="allowed egress host for Cowork local access; repeatable",
    )
    args = p.parse_args()

    if sum(bool(x) for x in [args.verify, args.revert, args.fix_models]) > 1:
        die("choose at most one of --verify / --revert / --fix-models")

    if args.verify:
        sys.exit(cmd_verify())
    if args.revert:
        sys.exit(cmd_revert())
    if args.fix_models:
        sys.exit(cmd_fix_models(args))
    sys.exit(cmd_apply(args))


if __name__ == "__main__":
    main()
