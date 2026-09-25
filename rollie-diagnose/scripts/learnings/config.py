"""Learnings uploader 配置 —— 路径常量、上传窗口、大小上限。"""
from __future__ import annotations

from pathlib import Path

# ── 业务常量 ────────────────────────────────────────────────
SKILL_ID = "rollie-diagnose"
LEARNINGS_UPLOAD_PATH = "/api/v1/learnings"

DEFAULT_LEARNINGS_UPLOAD_COOLDOWN_SECONDS = 21600  # 6 小时
UPLOAD_TIMEOUT_SECONDS = 15
MAX_CONTENT_BYTES = 5_242_880  # 5 MiB

# ── 路径 ────────────────────────────────────────────────────
ROLLIE_HOME = Path.home() / ".rollie"
LEARNINGS_DIR = ROLLIE_HOME / "learnings"
LEARNINGS_FILE = LEARNINGS_DIR / "learnings.md"
LAST_UPLOAD_FILE = LEARNINGS_DIR / ".last_upload.json"
LAST_HASH_FILE = LEARNINGS_DIR / ".last_uploaded_hash"
UPLOAD_LOG_FILE = LEARNINGS_DIR / ".upload.log"

# parents[2] = skill root (scripts/learnings/config.py 向上两级)
SKILL_ROOT = Path(__file__).resolve().parents[2]
COOKIES_FILE = SKILL_ROOT / "state" / ".cookies.json"


__all__ = [
    "SKILL_ID",
    "LEARNINGS_UPLOAD_PATH",
    "DEFAULT_LEARNINGS_UPLOAD_COOLDOWN_SECONDS",
    "UPLOAD_TIMEOUT_SECONDS",
    "MAX_CONTENT_BYTES",
    "ROLLIE_HOME",
    "LEARNINGS_DIR",
    "LEARNINGS_FILE",
    "LAST_UPLOAD_FILE",
    "LAST_HASH_FILE",
    "UPLOAD_LOG_FILE",
    "SKILL_ROOT",
    "COOKIES_FILE",
]
