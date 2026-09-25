"""Shared Mify API key resolver - zero deps, stdlib only.

Resolution order (first hit wins):
  1. $MIFY_API_KEY  env var (already sourced in this shell)
  2. ~/.config/mify/credentials  (parse export line directly)
  3. ~/.claude/settings.json  ->  env.ANTHROPIC_AUTH_TOKEN
     (Parker's Claude Code config often carries the same key)

Call load_mify_key() from any script.  Dies with a clear message only
when all three sources are exhausted.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_CREDENTIALS = Path.home() / ".config" / "mify" / "credentials"
_SETTINGS = Path.home() / ".claude" / "settings.json"

_KEY_RE = re.compile(r"^sk-[A-Za-z0-9_-]{16,196}$")


def _is_valid_key(key: str) -> bool:
    return bool(key) and bool(_KEY_RE.match(key))


def _from_env() -> str | None:
    key = os.environ.get("MIFY_API_KEY", "").strip()
    return key if _is_valid_key(key) else None


def _from_credentials_file() -> str | None:
    if not _CREDENTIALS.is_file():
        return None
    try:
        text = _CREDENTIALS.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        m = re.match(r"\s*export\s+MIFY_API_KEY\s*=\s*(.+?)\s*$", line)
        if m:
            key = m.group(1).strip().strip("'\"")
            if _is_valid_key(key):
                return key
    return None


def _from_settings_json() -> str | None:
    if not _SETTINGS.is_file():
        return None
    try:
        data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    env = data.get("env", {})
    for field in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        key = (env.get(field) or "").strip()
        if _is_valid_key(key):
            return key
    return None


def load_mify_key() -> str:
    """Return a valid Mify API key, or sys.exit with a helpful message."""
    for source_fn, label in [
        (_from_env,            "$MIFY_API_KEY env var"),
        (_from_credentials_file, str(_CREDENTIALS)),
        (_from_settings_json,  str(_SETTINGS)),
    ]:
        key = source_fn()
        if key:
            return key

    sys.exit(
        "Cannot find a Mify API key from any source.\n"
        "  Tried:\n"
        "    1. $MIFY_API_KEY env var\n"
        f"    2. {_CREDENTIALS}\n"
        f"    3. {_SETTINGS} (ANTHROPIC_AUTH_TOKEN)\n\n"
        "Fix: run  install_token.py  once to create the credentials file:\n"
        "  printf '%s' 'sk-YOUR_KEY_HERE' | python3 install_token.py"
    )
