"""读写 last_check.json + 判断是否处于冷却窗口。"""
from __future__ import annotations

import json
import time

from . import config


def read_last_check_ts() -> float | None:
    try:
        data = json.loads(config.LAST_CHECK_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    ts = data.get("last_check_ts")
    return float(ts) if isinstance(ts, (int, float)) else None


def write_last_check_ts(ts: float) -> None:
    try:
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        config.LAST_CHECK_FILE.write_text(
            json.dumps({"last_check_ts": ts}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        # 不抛异常,冷却写失败只影响下次探测窗口。
        pass


def in_cooldown() -> bool:
    ts = read_last_check_ts()
    if ts is None:
        return False
    return (time.time() - ts) < config.cooldown_seconds()


__all__ = ["read_last_check_ts", "write_last_check_ts", "in_cooldown"]
