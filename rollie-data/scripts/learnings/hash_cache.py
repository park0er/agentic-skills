"""读写 .last_uploaded_hash — 上次成功上传的内容 sha256,用于跳过重复上传。"""
from __future__ import annotations

import json

from . import config


def read_cached_hash() -> str | None:
    try:
        data = json.loads(config.LAST_HASH_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    h = data.get("content_hash")
    return h if isinstance(h, str) else None


def write_cached_hash(hash_hex: str) -> None:
    try:
        config.LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        config.LAST_HASH_FILE.write_text(
            json.dumps({"content_hash": hash_hex}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # 写失败只影响下次去重,不阻塞上传流程。
        pass


__all__ = ["read_cached_hash", "write_cached_hash"]
