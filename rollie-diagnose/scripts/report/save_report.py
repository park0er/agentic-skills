#!/usr/bin/env python3
"""Report save runner for rollie-diagnose server.

Sole responsibility: POST a local markdown report file to
``/api/v1/report/save`` so the diagnosis session's final report is persisted
server-side.
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

REPORT_PATH = "/api/v1/report/save"
REPORT_METHOD = "POST"

_HELP_TEXT = """
用法:save_report.py --report-file <md> --session-id <id>

职责
  把本地 Markdown 诊断报告保存到 server。
  调用:POST /api/v1/report/save

参数
  --report-file <path>   本地 md 文件路径(必填)。支持绝对路径,或以当前
                         工作目录(CWD)为基准的相对路径
  --session-id <id>      所属 session 的 id(必填)
  -h, --help             打印本帮助

payload 结构
  {
    "content":     <md 文件的文本内容>,
    "session_id":  <id>,
    "report_file": <md 文件的 basename>
  }

示例
  bash scripts/report/save_report.sh \\
    --report-file state/reports/diag_20260424.md \\
    --session-id sess_abc
""".strip()


def main() -> int:
    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        print(_HELP_TEXT)
        return 0

    parser = argparse.ArgumentParser(
        description="Report save runner for rollie-diagnose server.",
        add_help=False,
    )
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()

    report_path = Path(args.report_file)
    if not report_path.exists():
        raise SystemExit(
            f"report file not found: {report_path}, check ~/.rollie/reports/"
        )

    payload = {
        "content": report_path.read_text(encoding="utf-8"),
        "session_id": args.session_id,
        "report_file": report_path.name,
    }

    base_url = resolve_base_url()
    url = build_url(base_url, REPORT_PATH)
    identifier = safe_identifier(args.session_id, None, REPORT_PATH)

    return execute_and_emit(
        url=url,
        method=REPORT_METHOD,
        payload=payload,
        identifier=identifier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
