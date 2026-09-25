#!/usr/bin/env python3
"""Tag Claude Code model env vars with [1M] context window markers.

Reads ~/.claude/settings.json, cross-references each tier model (HAIKU/SONNET/OPUS)
against Artificial Analysis data for context window size, and appends a [1M] tag
to models that support >= 1M tokens.

Claude Code strips the [1M] suffix before making API calls, so the tag is purely
metadata that tells Claude Code how much context the model supports. This prevents
Claude Code from compressing conversations prematurely on models with large windows.

Currently only [1M] is confirmed supported by Claude Code. Other sizes (e.g. [256K])
have not been verified, so we only tag the 1M threshold.

Usage:
  tag_context.py --dry-run          # show what would change (default)
  tag_context.py --apply            # write changes to settings.json
  tag_context.py --refresh          # force re-fetch AA data before tagging
  tag_context.py --remove           # strip all context tags from model names

This script only modifies Claude Code's settings.json. It has no effect on
other clients (OpenCode, Cursor, etc.) that may also use Mify models.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

# Threshold: models with context_window >= 1M tokens get the [1M] tag.
CTX_THRESHOLD = 1_000_000
CTX_TAG = "[1M]"

TIER_ENV_VARS = {
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
}


def settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def load_settings(path: Path) -> dict:
    if not path.exists():
        print(f"✗ {path} not found.", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"✗ {path} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def backup_file(path: Path) -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.copy2(path, bak)
    return bak


def load_aa_models(refresh: bool) -> list[dict]:
    """Load AA model data from the daily cache, fetching if needed."""
    # Import the fetcher from sibling script
    sys.path.insert(0, str(Path(__file__).parent))
    from fetch_aa_rankings import load_or_fetch

    payload = load_or_fetch(refresh, 'auto')
    return payload.get("models", [])


def strip_tag(name: str) -> str:
    """Remove [1M] or [1m] suffix from a model name."""
    if name.upper().endswith(CTX_TAG.upper()):
        return name[: -len(CTX_TAG)]
    return name


def has_tag(name: str) -> bool:
    """Check if a model name already has the [1M] tag."""
    return name.upper().endswith(CTX_TAG.upper())


def normalize_for_match(model_id: str) -> str:
    """Normalize a Mify model id for fuzzy matching against AA slugs.

    Mify: ppio/pa/claude-opus-4-7 -> claude-opus-4-7
    Mify: xiaomi/mimo-v2.5-pro   -> mimo-v2-5-pro (dots become hyphens)
    AA:  claude-opus-4-7, mimo-v2-5-pro
    """
    # Strip owner prefix (everything before first /)
    _, _, mid = model_id.rpartition("/")
    # Lowercase and replace dots with hyphens
    return mid.lower().replace(".", "-")


def find_context_window(
    model_id: str, aa_models: list[dict]
) -> int | None:
    """Find the context window size for a Mify model id from AA data.

    Matching strategy (in order):
    1. Exact slug match against AA model slugs
    2. AA shortName substring match (case-insensitive)
    """
    normalized = normalize_for_match(model_id)

    # Pass 1: exact slug match
    for m in aa_models:
        if m.get("slug") == normalized:
            return m.get("context_window")

    # Pass 2: normalized id is a substring of AA slug, or vice versa
    for m in aa_models:
        slug = m.get("slug", "")
        if normalized in slug or slug in normalized:
            return m.get("context_window")

    # Pass 3: fuzzy match on AA shortName (e.g. "Claude Opus 4.7" matches "claude-opus-4-7")
    norm_no_hyphen = normalized.replace("-", "")
    for m in aa_models:
        short = m.get("label", "").lower().replace(" ", "").replace("-", "")
        if norm_no_hyphen == short or norm_no_hyphen in short or short in norm_no_hyphen:
            return m.get("context_window")

    return None


def plan_tagging(
    env: dict, aa_models: list[dict]
) -> tuple[dict, list[str]]:
    """Plan changes to env vars. Returns (new_env, list_of_changes)."""
    new_env = dict(env)
    changes: list[str] = []

    for tier, var in TIER_ENV_VARS.items():
        current = env.get(var)
        if not current:
            continue

        base_name = strip_tag(current)
        ctx = find_context_window(base_name, aa_models)

        if ctx is not None and ctx >= CTX_THRESHOLD:
            if not has_tag(current):
                new_env[var] = base_name + CTX_TAG
                changes.append(
                    f"+ {var}: {current} -> {base_name + CTX_TAG}  "
                    f"(context: {ctx:,} tokens >= 1M)"
                )
            else:
                changes.append(
                    f"· {var}: {current}  (already tagged, context: {ctx:,} tokens)"
                )
        else:
            if has_tag(current):
                new_env[var] = base_name
                changes.append(
                    f"- {var}: {current} -> {base_name}  "
                    f"(context: {ctx:, if ctx else 'unknown'} tokens < 1M, tag removed)"
                )
            elif ctx is not None:
                changes.append(
                    f"· {var}: {current}  (context: {ctx:,} tokens, below 1M threshold)"
                )
            else:
                changes.append(
                    f"? {var}: {current}  (not found in AA data, skipping)"
                )

    return new_env, changes


def cmd_remove(env: dict) -> tuple[dict, list[str]]:
    """Remove all context tags from model names."""
    new_env = dict(env)
    changes: list[str] = []

    for tier, var in TIER_ENV_VARS.items():
        current = env.get(var)
        if current and has_tag(current):
            new_env[var] = strip_tag(current)
            changes.append(f"- {var}: {current} -> {strip_tag(current)}")

    return new_env, changes


def dump_settings(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag Claude Code model env vars with [1M] context window markers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  tag_context.py --dry-run       # preview changes (default)\n"
            "  tag_context.py --apply         # write to settings.json\n"
            "  tag_context.py --refresh       # force re-fetch AA data\n"
            "  tag_context.py --remove        # strip all [1M] tags\n"
        ),
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="write changes to settings.json (default is dry-run).",
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="force re-fetch AA data instead of using cache.",
    )
    parser.add_argument(
        "--remove", action="store_true",
        help="remove all [1M] context tags from model names.",
    )
    args = parser.parse_args()

    path = settings_path()
    settings = load_settings(path)
    env = settings.get("env", {})

    # Remove mode: no AA data needed
    if args.remove:
        new_env, changes = cmd_remove(env)
        if not changes:
            print("No [1M] tags found to remove.")
            return
        print("Planned changes (remove tags):")
        for c in changes:
            print(" ", c)
        print()
        if not args.apply:
            print("— dry run — Re-run with --apply to write.")
            return
        settings["env"] = new_env
        bak = backup_file(path)
        path.write_text(dump_settings(settings), encoding="utf-8")
        print(f"✓ Backup: {bak}")
        print(f"✓ Wrote {path}")
        print("Restart Claude Code for changes to take effect.")
        return

    # Normal mode: load AA data and tag
    print("Loading AA model data...")
    aa_models = load_aa_models(args.refresh)
    print(f"Loaded {len(aa_models)} models from AA.\n")

    new_env, changes = plan_tagging(env, aa_models)

    if not changes:
        print("No model env vars found in settings.json to tag.")
        return

    print("Context window analysis:")
    for c in changes:
        print(" ", c)
    print()

    # Count actual changes (not just informational lines)
    real_changes = [c for c in changes if c.startswith(("+", "-"))]

    if not real_changes:
        print("All models already correctly tagged. No changes needed.")
        return

    if not args.apply:
        print(
            "— dry run — Re-run with --apply to write.\n"
            f"  {len(real_changes)} change(s) would be made to {path}"
        )
        return

    settings["env"] = new_env
    bak = backup_file(path)
    path.write_text(dump_settings(settings), encoding="utf-8")
    print(f"✓ Backup: {bak}")
    print(f"✓ Wrote {path}")
    print("Restart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
