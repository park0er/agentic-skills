#!/usr/bin/env python3
"""Learnings uploader — 后台上传本地 learnings.md 到 server,恒 exit 0。"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 把 scripts/ 加到 sys.path,以便 import utils.http_client
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from learnings import client_id as _client_id_mod  # noqa: E402
from learnings import config  # noqa: E402
from learnings import cooldown as _cooldown_mod  # noqa: E402
from learnings import hash_cache as _hash_cache_mod  # noqa: E402
from learnings import logger as _logger_mod  # noqa: E402
from utils.http_client import SKILL_VERSION, resolve_base_url  # noqa: E402


def main() -> int:
    try:
        return _run()
    except Exception as exc:  # noqa: BLE001 顶层兜底
        try:
            _logger_mod.append("unexpected_error", error=repr(exc))
        except Exception:
            pass
        return 0


def _run() -> int:
    # 1. 文件存在 + 非空
    if not config.LEARNINGS_FILE.exists():
        return 0
    try:
        size = config.LEARNINGS_FILE.stat().st_size
    except OSError:
        return 0
    if size == 0:
        return 0

    # 2. 冷却
    if _cooldown_mod.in_cooldown():
        return 0

    # 3. oversize
    if size > config.MAX_CONTENT_BYTES:
        _logger_mod.append("oversize", size=size)
        return 0

    # 4. client_id
    cid = _client_id_mod.resolve_client_id()
    if not cid:
        _logger_mod.append("no_cookie")
        return 0

    # 5. hash + content
    try:
        file_bytes = config.LEARNINGS_FILE.read_bytes()
        content = config.LEARNINGS_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        _logger_mod.append("unexpected_error", error=repr(exc))
        return 0
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    # 5.5. hash 缓存命中跳过
    cached = _hash_cache_mod.read_cached_hash()
    if cached == content_hash:
        return 0

    # 6. POST /api/v1/learnings
    url = resolve_base_url().rstrip("/") + config.LEARNINGS_UPLOAD_PATH
    body = json.dumps(
        {
            "skill_id": config.SKILL_ID,
            "skill_version": SKILL_VERSION,
            "client_id": cid,
            "content_hash": content_hash,
            "content": content,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Skill-Id": config.SKILL_ID,
            "X-Skill-Version": SKILL_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.UPLOAD_TIMEOUT_SECONDS) as resp:
            code = resp.status
            resp_body = resp.read()
    except urllib.error.HTTPError as http_err:
        # 非 2xx 走这个分支
        try:
            err_body = http_err.read()[:200]
        except Exception:
            err_body = b""
        _logger_mod.append(
            "http_error",
            http_code=http_err.code,
            body=err_body.decode("utf-8", errors="replace"),
        )
        return 0
    except (urllib.error.URLError, TimeoutError, OSError) as net_err:
        _logger_mod.append("network_error", error=repr(net_err))
        return 0

    # 7. 2xx → 写 ts + 写 hash 缓存
    if 200 <= code < 300:
        _cooldown_mod.write_last_upload_ts(time.time())
        _hash_cache_mod.write_cached_hash(content_hash)
        return 0

    # 理论走不到(非 2xx 会进 HTTPError 分支),保险起见落日志
    body_preview = (
        resp_body[:200] if isinstance(resp_body, (bytes, bytearray)) else b""
    ).decode("utf-8", errors="replace")
    _logger_mod.append("http_error", http_code=code, body=body_preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
