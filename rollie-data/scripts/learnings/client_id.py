"""从共享 ~/.rollie/auth/.cookies.json 中解析 client_id(即 _aegis_cas JWT 的 sub 字段)。

⚠ 耦合点:本文件与 server/skill_core/core/cookie_utils.py 是字节级同形的两份实现,
改这里的解析算法必须同步改 server 侧(详见 docs/coupling-map.md)。
"""
from __future__ import annotations

import base64
import json
import re

from . import config

_SUB_RE = re.compile(r'"sub"\s*:\s*"([^"]+)"')


def parse_username_from_cookie(cookie_value: str | None) -> str | None:
    """从 _aegis_cas JWT cookie 中提取 sub 字段(用户名)。

    仅 base64-decode payload 段,不验证签名。
    cookie_value 为 None、格式错误或无 sub 字段时返回 None,不抛异常。
    """
    if not cookie_value:
        return None
    try:
        parts = cookie_value.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # urlsafe base64, pad to multiple of 4
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded)
        # Use regex to avoid json.loads failure on non-UTF-8 bytes in detail field
        payload_str = payload_bytes.decode("utf-8", errors="replace")
        m = _SUB_RE.search(payload_str)
        if m:
            return m.group(1)
        return None
    except Exception:
        return None


def resolve_client_id() -> str | None:
    """从 ~/.rollie/auth/.cookies.json 中找出任一 domain 的 _aegis_cas cookie 并解析 sub。

    文件结构: {domain: {cookie_name: value, ...}, ...}
    任何 OSError / JSONDecodeError / AttributeError 都返回 None,永不抛出。
    """
    try:
        with open(config.COOKIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    try:
        for _domain, cookies in data.items():
            if not isinstance(cookies, dict):
                continue
            value = cookies.get("_aegis_cas")
            if value:
                sub = parse_username_from_cookie(value)
                if sub:
                    return sub
        return None
    except AttributeError:
        return None


__all__ = ["parse_username_from_cookie", "resolve_client_id"]
