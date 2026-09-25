"""读写 .last_upload.json + 判断是否处于 learnings 上传冷却窗口。"""
from __future__ import annotations

import json
import time

from . import config


def read_last_upload_ts() -> float | None:
    try:
        data = json.loads(config.LAST_UPLOAD_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    ts = data.get("last_upload_ts")
    return float(ts) if isinstance(ts, (int, float)) else None


def write_last_upload_ts(ts: float) -> None:
    try:
        config.LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        config.LAST_UPLOAD_FILE.write_text(
            json.dumps({"last_upload_ts": ts}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # 不抛异常,冷却写失败只影响下次上传窗口。
        pass


def in_cooldown() -> bool:
    ts = read_last_upload_ts()
    if ts is None:
        return False
    return (time.time() - ts) < config.DEFAULT_LEARNINGS_UPLOAD_COOLDOWN_SECONDS


__all__ = ["read_last_upload_ts", "write_last_upload_ts", "in_cooldown"]
