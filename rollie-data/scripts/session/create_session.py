#!/usr/bin/env python3
"""Session create runner for rollie-data skill.

POST ``/api/v1/session/create`` with body ``{"context": {...}}``。
session_id 用于把同一次对话里的多次查询串联起来，便于日志追溯与问题定位。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.http_client import (  # noqa: E402
    SKILL_VERSION,
    build_url,
    execute_and_emit,
    resolve_base_url,
    safe_identifier,
)

__version__ = SKILL_VERSION

CREATE_PATH = "/api/v1/session/create"
CREATE_METHOD = "POST"

_HELP_TEXT = """
用法:create_session.py --context '<json>'

职责
  创建一次查询会话,返回 session_id。同一次对话里的多次查询都应携带同一个
  session_id,便于串联日志与问题定位。
  调用:POST /api/v1/session/create

参数
  --context <json>   会话上下文 JSON,默认 "{}";请求体格式为
                     {"context": <parsed>}
  -h, --help         打印本帮助

示例
  bash scripts/session/create_session.sh --context '{"user_query":"查一下昨天的消耗"}'
""".strip()


def _load_context(context_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(context_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid context json: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit("context must be a JSON object")
    return parsed


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_HELP_TEXT)
        return 0

    parser = argparse.ArgumentParser(
        description="Session create runner for rollie-data skill.",
        add_help=False,
    )
    parser.add_argument("--context", default="{}")
    args = parser.parse_args()

    payload = {"context": _load_context(args.context)}

    base_url = resolve_base_url()
    url = build_url(base_url, CREATE_PATH)
    identifier = safe_identifier(None, None, CREATE_PATH)

    return execute_and_emit(
        url=url,
        method=CREATE_METHOD,
        payload=payload,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
