#!/usr/bin/env python3
"""Shared HTTP client for rollie-data runner scripts.

Single network-implementation point for all runners under ``scripts/``:

- ``scripts/query/dashboard_query.py``  — dashboard query runner
- ``scripts/session/create_session.py`` — session create runner

All URL building, HTTP requests, failure logging, redaction, and exit-code
mapping live here. Each runner only does argparse + payload assembly and then
calls ``execute_and_emit(...)``.

Base URL and request timeout are runner-internal configuration and MUST NOT be
exposed as CLI flags to the Agent. Base URL resolves from the
``DIAGNOSE_API_BASE_URL`` environment variable (kept under the ``DIAGNOSE_``
prefix so ops/CI configuration is shared with the rollie-diagnose skill —
both skills target the same backend) and falls back to ``DEFAULT_BASE_URL``.
Timeout is a module-level constant (``DEFAULT_TIMEOUT_SECONDS``) that ops
adjusts by editing this file.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Single source of truth for runner version. Keep in sync with the
# SKILL.md at the repository root when it introduces a ``version`` field.
# For now the project has no SKILL.md version; we maintain it here so all
# runners share one string.
SKILL_ID = "rollie-data"
SKILL_VERSION = "1.3.0"

DEFAULT_BASE_URL = "http://rollie-agents.ad.xiaomi.srv"
DEFAULT_TIMEOUT_SECONDS = 180

_FAILURE_LOG_RETENTION_DAYS = 15
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(cookie|token|authorization|secret|password)", re.IGNORECASE
)

# ``scripts/`` directory — ``utils/http_client.py`` lives at
# ``scripts/utils/http_client.py``, so ``parents[1]`` is ``scripts/`` and
# ``parents[2]`` is the skill root.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(__file__).resolve().parents[2]


class RequestNetworkError(Exception):
    """Raised for ``urllib.error.URLError`` (DNS / TCP / TLS / timeout)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def resolve_base_url() -> str:
    """Return the base URL, preferring ``DIAGNOSE_API_BASE_URL`` env var."""
    return os.getenv("DIAGNOSE_API_BASE_URL", DEFAULT_BASE_URL)


def build_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def with_skill_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    enriched.setdefault("skill_id", SKILL_ID)
    enriched.setdefault("skill_version", SKILL_VERSION)
    return enriched


def redact_for_log(obj: Any) -> Any:
    if isinstance(obj, dict):
        redacted: dict[str, Any] = {}
        for k, v in obj.items():
            if _SENSITIVE_KEY_PATTERN.search(str(k)):
                redacted[k] = "<redacted>"
            else:
                redacted[k] = redact_for_log(v)
        return redacted
    if isinstance(obj, list):
        return [redact_for_log(v) for v in obj]
    return obj


def safe_identifier(session_id: str | None, dashboard: str | None, path: str) -> str:
    if session_id:
        raw = f"session_{session_id}"
    elif dashboard:
        raw = f"dashboard_{dashboard}"
    else:
        raw = f"path_{path}"

    slug = re.sub(r"[^0-9A-Za-z._-]+", "_", raw).strip("_")
    if not slug:
        slug = "unknown"
    if len(slug) > 96:
        slug = slug[:96]
    return slug


def _failure_log_dir() -> Path:
    return SKILL_ROOT / "state" / "query_execute_runner_logs"


def _prune_old_failure_logs(log_dir: Path) -> None:
    if not log_dir.exists():
        return
    cutoff_ts = datetime.now(timezone.utc).timestamp() - (
        _FAILURE_LOG_RETENTION_DAYS * 86400
    )
    for p in log_dir.glob("*.json"):
        try:
            if p.stat().st_mtime < cutoff_ts:
                p.unlink(missing_ok=True)
        except OSError:
            continue


def write_failure_log(
    *,
    identifier: str,
    url: str,
    method: str,
    request_body: dict[str, Any] | str | None,
    response_status: int | None,
    response_text: str | None,
    error: str | None,
) -> Path | None:
    log_dir = _failure_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _prune_old_failure_logs(log_dir)
        now = datetime.now(timezone.utc).astimezone()
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{identifier}_{os.getpid()}.json"
        log_path = log_dir / filename
        record = {
            "timestamp": now.isoformat(),
            "identifier": identifier,
            "url": url,
            "method": method,
            "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "request_body": redact_for_log(request_body),
            "response_status": response_status,
            "response_text": response_text,
            "error": error,
        }
        log_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return log_path
    except OSError:
        return None


def request(
    url: str,
    method: str,
    body: dict[str, Any] | str | None,
) -> tuple[int, str, str | None]:
    """Send an HTTP request and return ``(status, text, request_id)``.

    ``request_id`` is extracted from the ``X-Request-Id`` response header when
    present, otherwise ``None``. Raises ``RequestNetworkError`` on
    ``URLError``.
    """
    if body is None:
        data = None
    elif isinstance(body, str):
        data = body.encode("utf-8")
    else:
        data = json.dumps(with_skill_metadata(body), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Accept", "application/json")
    req.add_header("X-Skill-Id", SKILL_ID)
    req.add_header("X-Skill-Version", SKILL_VERSION)
    if data is not None:
        req.add_header(
            "Content-Type",
            "application/json" if not isinstance(body, str) else "text/plain; charset=utf-8",
        )

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as resp:
            request_id = resp.headers.get("X-Request-Id")
            return resp.status, resp.read().decode("utf-8", errors="replace"), request_id
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        request_id = exc.headers.get("X-Request-Id") if exc.headers is not None else None
        return exc.code, payload, request_id
    except urllib.error.URLError as exc:
        raise RequestNetworkError(str(exc.reason)) from exc


def _parse_body(text: str | None) -> Any:
    """Return parsed JSON object if possible, else raw string (or None)."""
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def execute_and_emit(
    *,
    url: str,
    method: str,
    payload: dict[str, Any] | str | None,
    identifier: str,
) -> int:
    """Send the request, emit structured stdout JSON, return exit code.

    Exit-code mapping (see spec ``进程退出码映射`` Requirement):

    - 0   — HTTP 2xx
    - 2   — HTTP 4xx/5xx
    - 3   — network error (``URLError``, timeout before response)
    - 130 — ``KeyboardInterrupt``

    ``SystemExit`` from argparse / validation (exit 1) is raised by the runner
    itself before reaching this function.
    """
    request_payload = with_skill_metadata(payload) if isinstance(payload, dict) else payload
    start = time.monotonic()
    try:
        try:
            status, text, request_id = request(url, method, request_payload)
        except RequestNetworkError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            write_failure_log(
                identifier=identifier,
                url=url,
                method=method.upper(),
                request_body=request_payload,
                response_status=None,
                response_text=None,
                error=f"network_error: {exc.reason}",
            )
            print(
                json.dumps(
                    {
                        "request_id": None,
                        "status_code": None,
                        "body": None,
                        "duration_ms": duration_ms,
                    },
                    ensure_ascii=False,
                )
            )
            print(f"[runner] request failed: {exc.reason}", file=sys.stderr)
            return 3
    except KeyboardInterrupt:
        print("[runner] interrupted", file=sys.stderr)
        return 130

    duration_ms = int((time.monotonic() - start) * 1000)

    if not (200 <= status < 300):
        write_failure_log(
            identifier=identifier,
            url=url,
            method=method.upper(),
            request_body=request_payload,
            response_status=status,
            response_text=text,
            error="http_error",
        )

    print(
        json.dumps(
            {
                "request_id": request_id,
                "status_code": status,
                "body": _parse_body(text),
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
        )
    )

    return 0 if 200 <= status < 300 else 2
