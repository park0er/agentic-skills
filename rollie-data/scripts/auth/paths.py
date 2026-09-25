"""Shared Rollie auth paths."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[2]
ROLLIE_HOME = Path.home() / ".rollie"
AUTH_DIR = ROLLIE_HOME / "auth"
COOKIE_FILE = AUTH_DIR / ".cookies.json"
LEGACY_COOKIE_FILE = SKILL_ROOT / "state" / ".cookies.json"
LOCK_FILE = AUTH_DIR / ".refresh.lock"
AUTH_LOG_DIR = AUTH_DIR / "logs"


def ensure_shared_cookie_file() -> None:
    if COOKIE_FILE.exists() or not LEGACY_COOKIE_FILE.exists():
        return
    try:
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEGACY_COOKIE_FILE, COOKIE_FILE)
        try:
            os.chmod(COOKIE_FILE, 0o600)
        except OSError:
            pass
    except OSError:
        return


def read_cookie_payload() -> dict[str, Any]:
    ensure_shared_cookie_file()
    return json.loads(COOKIE_FILE.read_text(encoding="utf-8"))


__all__ = [
    "SKILL_ROOT",
    "ROLLIE_HOME",
    "AUTH_DIR",
    "COOKIE_FILE",
    "LEGACY_COOKIE_FILE",
    "LOCK_FILE",
    "AUTH_LOG_DIR",
    "ensure_shared_cookie_file",
    "read_cookie_payload",
]
