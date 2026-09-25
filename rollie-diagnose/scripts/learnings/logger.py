"""Learnings uploader 本地日志 — 仅当 skip / 失败时追加一行 JSON 到 .upload.log。

日志写失败必须吞掉,不能把 uploader 搞崩。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config


def append(reason: str, **kwargs: object) -> None:
    """追加一条上传结果日志。

    写入 JSON-lines 格式:{"ts": iso8601, "reason": ..., **kwargs}\\n
    任何 OSError 都吞掉。
    """
    try:
        config.LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
        record: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        record.update(kwargs)
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(config.UPLOAD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        # 日志失败不能阻塞上传主流程。
        pass


__all__ = ["append"]
