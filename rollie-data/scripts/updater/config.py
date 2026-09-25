"""Updater 全局配置 —— 环境变量、路径常量、退出码。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Import 复用 http_client 里的 base URL 解析。
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.http_client import resolve_base_url  # noqa: E402

# ── 业务常量 ────────────────────────────────────────────────
SKILL_ID = "rollie-data"
CHECK_UPDATE_PATH = "/api/v1/check-update"

DEFAULT_COOLDOWN_SECONDS = 21600  # 6 小时
CHECK_TIMEOUT_SECONDS = 3
DOWNLOAD_TIMEOUT_SECONDS = 60

# ── 退出码契约 ──────────────────────────────────────────────
EXIT_CONTINUE = 0
EXIT_UPDATED = 100
EXIT_UPDATE_FAILED = 2

# ── 路径 ────────────────────────────────────────────────────
# SKILL_ROOT:skill 源码根目录,就是要被升级替换的那个目录。
SKILL_ROOT = Path(__file__).resolve().parents[2]

# ROLLIE_HOME / STATE_DIR:updater 运行时状态存放点,必须在 SKILL_ROOT 外部,
# 否则 atomic_replace 第一步会在 rename(SKILL_ROOT, inside_itself) 时抛 EINVAL。
# 与 SKILL.md 里 ~/.rollie/learnings、~/.rollie/reports 的约定对齐。
ROLLIE_HOME = Path.home() / ".rollie"
STATE_DIR = ROLLIE_HOME / "updater" / SKILL_ID
LAST_CHECK_FILE = STATE_DIR / "last_check.json"
LOCK_FILE = STATE_DIR / "update.lock"
DOWNLOAD_DIR = STATE_DIR / "download"
STAGING_DIR = STATE_DIR / "staging"
OLD_DIR = STATE_DIR / "old"


# ── 环境变量 ────────────────────────────────────────────────
def skip_update() -> bool:
    return os.getenv("GENERAL_DATA_SKIP_UPDATE", "") == "1"


def cooldown_seconds() -> int:
    raw = os.getenv("GENERAL_DATA_UPDATE_COOLDOWN")
    if not raw:
        return DEFAULT_COOLDOWN_SECONDS
    try:
        v = int(raw)
        return v if v >= 0 else DEFAULT_COOLDOWN_SECONDS
    except ValueError:
        return DEFAULT_COOLDOWN_SECONDS


__all__ = [
    "SKILL_ID",
    "CHECK_UPDATE_PATH",
    "DEFAULT_COOLDOWN_SECONDS",
    "CHECK_TIMEOUT_SECONDS",
    "DOWNLOAD_TIMEOUT_SECONDS",
    "EXIT_CONTINUE",
    "EXIT_UPDATED",
    "EXIT_UPDATE_FAILED",
    "SKILL_ROOT",
    "ROLLIE_HOME",
    "STATE_DIR",
    "LAST_CHECK_FILE",
    "LOCK_FILE",
    "DOWNLOAD_DIR",
    "STAGING_DIR",
    "OLD_DIR",
    "skip_update",
    "cooldown_seconds",
    "resolve_base_url",
]
