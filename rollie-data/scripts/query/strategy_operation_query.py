#!/usr/bin/env python3
"""Strategy operation/config query runner for rollie-diagnose server.

POST a UnionOperation query to ``/api/v1/strategy-opsoperation/query``.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.http_client import (  # noqa: E402
    SKILL_ROOT,
    SKILL_VERSION,
    build_url,
    execute_and_emit,
    resolve_base_url,
    safe_identifier,
)
from auth.paths import COOKIE_FILE as COOKIES_FILE  # noqa: E402

__version__ = SKILL_VERSION

STRATEGY_OPERATION_PATH = "/api/v1/strategy-opsoperation/query"
STRATEGY_OPERATION_METHOD = "POST"

_DIMENSION_KEYS = ["adId", "adGroupId", "campaignId", "accountId", "appId", "adReportId"]

_HELP_TEXT = """
用法:strategy_operation_query.py --params '<json>' [选项]

职责
  查询广告信息、广告主操作、内部配置信息和配置记录。

--params '<json>'  (必填)

  {
    "start_time": "2026-06-03T00:00:00+08:00",   // 必须 +08:00 格式
    "end_time":   "2026-06-04T00:00:00+08:00",   // 必须 +08:00 格式
    "campaignId": "401190499",                     // 六选一维度 key
    "category": "emi_opt_records"                  // 必填,见下
  }

  维度 key（六选一，值和类型）:
    adId / adGroupId / campaignId / accountId / appId / adReportId

  category（必填）:
    emi_ad_detail        — 广告信息，必须搭配 adId
    emi_opt_records      — 广告主相关操作
    inside_curr_configs  — 内部配置信息
    inside_opt_records   — 配置记录相关

  --session-id <id>  可选，会话 ID

示例

  # 查询计划 401190499 的广告主相关操作
  bash scripts/query/strategy_operation_query.sh \\
    --params '{"start_time":"2026-06-03T00:00:00+08:00","end_time":"2026-06-04T00:00:00+08:00","campaignId":"401190499","category":"emi_opt_records"}'

  # 查询广告 12345 的广告信息
  bash scripts/query/strategy_operation_query.sh \\
    --params '{"start_time":"2026-06-03T00:00:00+08:00","end_time":"2026-06-04T00:00:00+08:00","adId":"12345","category":"emi_ad_detail"}' \\
    --session-id <id>
""".strip()


def _load_params(params_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(params_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid params json: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit("params must be a JSON object")

    # Validate exactly one dimension key
    dims = [k for k in _DIMENSION_KEYS if k in parsed and parsed[k] is not None]
    if len(dims) == 0:
        raise SystemExit(f"必须传入一个维度 key，可选: {_DIMENSION_KEYS}")
    if len(dims) > 1:
        raise SystemExit(f"只能传入一个维度 key，收到: {dims}")

    if "start_time" not in parsed or "end_time" not in parsed:
        raise SystemExit("start_time 和 end_time 必填")

    if "category" not in parsed:
        raise SystemExit("category 必填，值为 emi_ad_detail / emi_opt_records / inside_curr_configs / inside_opt_records")

    return parsed


def _load_cookies_b64() -> str:
    if not COOKIES_FILE.exists():
        raise SystemExit(
            "missing cookies: ensure ~/.rollie/auth/.cookies.json exists before querying strategy operation"
        )

    raw_json = COOKIES_FILE.read_text(encoding="utf-8")

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid cookies json: {exc}")
    if not isinstance(parsed, dict):
        raise SystemExit("cookies json must be a JSON object")

    return base64.b64encode(
        json.dumps(parsed, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_HELP_TEXT)
        return 0

    parser = argparse.ArgumentParser(
        description="Strategy operation/config query runner for rollie-diagnose server.",
        add_help=False,
    )
    parser.add_argument("--params", default="{}")
    parser.add_argument("--session-id")
    args = parser.parse_args()

    params = _load_params(args.params)

    payload: dict[str, Any] = {
        **params,
        "session_id": args.session_id,
        "cookies_b64": _load_cookies_b64(),
    }

    base_url = resolve_base_url()
    url = build_url(base_url, STRATEGY_OPERATION_PATH)
    identifier = safe_identifier(args.session_id, "strategy_operation", STRATEGY_OPERATION_PATH)

    return execute_and_emit(
        url=url,
        method=STRATEGY_OPERATION_METHOD,
        payload=payload,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
