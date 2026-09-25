#!/usr/bin/env python3
"""Filter-rule query runner for rollie-diagnose server.

POST a filter-name lookup to ``/api/v1/query/filter-rule``.
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

FILTER_RULE_PATH = "/api/v1/query/filter-rule"
FILTER_RULE_METHOD = "POST"

_HELP_TEXT = """
用法:filter_rule_query.py --filter-name <FILTER>

职责
  查询过滤码(filterReason / filter_name)的含义说明。
  调用:POST /api/v1/query/filter-rule

参数
  --filter-name <name>   过滤码名称(必填),如 OCPX_STRATEGY_FILTER
  -h, --help             打印本帮助

payload 结构
  {"filter_name": "<name>"}

示例
  bash scripts/query/filter_rule_query.sh --filter-name OCPX_STRATEGY_FILTER
""".strip()


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_HELP_TEXT)
        return 0

    parser = argparse.ArgumentParser(
        description="Filter-rule query runner for rollie-diagnose server.",
        add_help=False,
    )
    parser.add_argument("--filter-name", required=True)
    args = parser.parse_args()

    payload = {"filter_name": args.filter_name}

    base_url = resolve_base_url()
    url = build_url(base_url, FILTER_RULE_PATH)
    identifier = safe_identifier(None, args.filter_name, FILTER_RULE_PATH)

    return execute_and_emit(
        url=url,
        method=FILTER_RULE_METHOD,
        payload=payload,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
