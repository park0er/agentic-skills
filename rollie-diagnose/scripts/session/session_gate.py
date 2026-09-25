#!/usr/bin/env python3
"""Session gate runner for rollie-diagnose server.

GET ``/api/v1/session/<session-id>/validate`` — 漏斗完整性门控,
写最终诊断报告前必须调用。服务端返回 pass / missing_steps /
runtime_hints / report_checklist。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

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

GATE_METHOD = "GET"
_SESSION_PATH_TEMPLATE = "/api/v1/session/{session_id}/validate"

_HELP_TEXT = """
用法:session_gate.py --session-id <id>

职责
  漏斗完整性门控。Agent 在生成最终诊断报告前必须调用本接口,
  用于确认已完成必要的下钻/漏斗查询,并拿到 runtime_hints 与
  report_checklist。
  调用:GET /api/v1/session/<id>/validate

参数
  --session-id <id>   要校验的 session id(必填)
  -h, --help          打印本帮助

示例
  bash scripts/session/session_gate.sh --session-id sess_abc
""".strip()


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_HELP_TEXT)
        return 0

    parser = argparse.ArgumentParser(
        description="Session gate runner for rollie-diagnose server.",
        add_help=False,
    )
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()

    path = _SESSION_PATH_TEMPLATE.format(session_id=args.session_id)
    base_url = resolve_base_url()
    url = build_url(base_url, path)
    identifier = safe_identifier(args.session_id, None, path)

    return execute_and_emit(
        url=url,
        method=GATE_METHOD,
        payload=None,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
