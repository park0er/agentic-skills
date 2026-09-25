"""Check-update remote client — GET /api/v1/check-update.

Thin wrapper around ``urllib`` that swallows all failure modes (network,
non-2xx, JSON decode, non-dict body) and returns ``None``. Extracted from
``check_and_update.py`` so it's testable without monkey-patching module-level
SKILL_VERSION.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.http_client import resolve_base_url  # noqa: E402

from scripts.updater.config import CHECK_TIMEOUT_SECONDS, SKILL_ID  # noqa: E402

CHECK_UPDATE_PATH = "/api/v1/check-update"


def _log(msg: str) -> None:
    print(f"[updater] {msg}", file=sys.stderr)


def check_update(current_version: str) -> dict | None:
    """GET /api/v1/check-update?skill_id=...&current_version=...

    Returns the parsed JSON dict on HTTP 2xx with valid JSON object body.
    Returns None for ANY failure: network error (URLError/OSError/TimeoutError),
    non-2xx status, JSON decode error, or non-dict body.
    Never raises.
    """
    base = resolve_base_url()
    query = urllib.parse.urlencode(
        {"skill_id": SKILL_ID, "current_version": current_version}
    )
    url = f"{base.rstrip('/')}{CHECK_UPDATE_PATH}?{query}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT_SECONDS) as resp:
            if not (200 <= resp.status < 300):
                _log(f"check-update status {resp.status}")
                return None
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log(f"check-update network error: {exc}")
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        _log(f"check-update json decode error: {exc}")
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed
