#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


@dataclass
class ParseResult:
    hints: dict
    confidence: dict[str, float]
    missing: dict[str, bool]


def _to_day_range(dt: datetime) -> tuple[str, str]:
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = dt.replace(hour=23, minute=59, second=59, microsecond=0)
    return start.strftime("%Y-%m-%dT%H:%M:%S+08:00"), end.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _extract_time_window(text: str, now: datetime) -> tuple[str | None, str | None, str | None]:
    abs_date = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?", text)
    hour_range = re.search(r"(\d{1,2})点\s*(?:到|至|\-|~)\s*(\d{1,2})点", text)

    if abs_date:
        year, month, day = map(int, abs_date.groups())
        if hour_range:
            sh, eh = map(int, hour_range.groups())
            start = datetime(year, month, day, sh, 0, 0, tzinfo=TZ)
            end = datetime(year, month, day, eh, 0, 0, tzinfo=TZ)
        else:
            start = datetime(year, month, day, 0, 0, 0, tzinfo=TZ)
            end = datetime(year, month, day, 23, 59, 59, tzinfo=TZ)
        return start.strftime("%Y-%m-%dT%H:%M:%S+08:00"), end.strftime("%Y-%m-%dT%H:%M:%S+08:00"), None

    cn_date = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if cn_date:
        month, day = map(int, cn_date.groups())
        year = now.year
        if hour_range:
            sh, eh = map(int, hour_range.groups())
            start = datetime(year, month, day, sh, 0, 0, tzinfo=TZ)
            end = datetime(year, month, day, eh, 0, 0, tzinfo=TZ)
        else:
            start = datetime(year, month, day, 0, 0, 0, tzinfo=TZ)
            end = datetime(year, month, day, 23, 59, 59, tzinfo=TZ)
        return start.strftime("%Y-%m-%dT%H:%M:%S+08:00"), end.strftime("%Y-%m-%dT%H:%M:%S+08:00"), None

    relative_map = {
        "今天": 0,
        "今日": 0,
        "yesterday": 1,
        "昨天": 1,
        "昨日": 1,
        "前天": 2,
    }
    day_offset = None
    for token, offset in relative_map.items():
        if token.lower() in text.lower():
            day_offset = offset
            break

    if day_offset is not None:
        base = (now - timedelta(days=day_offset)).replace(tzinfo=TZ)
        if hour_range:
            sh, eh = map(int, hour_range.groups())
            start = base.replace(hour=sh, minute=0, second=0, microsecond=0)
            end = base.replace(hour=eh, minute=0, second=0, microsecond=0)
            return start.strftime("%Y-%m-%dT%H:%M:%S+08:00"), end.strftime("%Y-%m-%dT%H:%M:%S+08:00"), f"D-{day_offset}"

        start, end = _to_day_range(base)
        return start, end, f"D-{day_offset}"

    return None, None, None


def parse_nl_hint(text: str, now: datetime | None = None) -> ParseResult:
    if now is None:
        now = datetime.now(TZ)

    campaign_match = re.search(r"(?:计划|campaign)\D{0,6}(\d{5,})", text, flags=re.IGNORECASE)
    account_match = re.search(r"(?:账户|账号|account)\D{0,6}(\d{4,})", text, flags=re.IGNORECASE)
    ad_match = re.search(r"(?:广告|素材|adid|ad)\D{0,6}(\d{5,})", text, flags=re.IGNORECASE)
    tag_match = re.search(r"(\d+\.\d+\.[a-zA-Z]\.\d+)", text)

    start_time, end_time, relative_label = _extract_time_window(text, now)

    hints = {
        "customerId": account_match.group(1) if account_match else None,
        "campaign_id": campaign_match.group(1) if campaign_match else None,
        "ad_id": ad_match.group(1) if ad_match else None,
        "tag_id": tag_match.group(1) if tag_match else None,
        "start_time": start_time,
        "end_time": end_time,
        "relative_day_label": relative_label,
    }

    has_object = any([hints["ad_id"], hints["campaign_id"], hints["customerId"]])
    has_time = bool(hints["start_time"] and hints["end_time"])

    object_conf = 0.9 if has_object else 0.1
    time_conf = 0.9 if has_time else 0.1
    overall = round((object_conf + time_conf) / 2, 2)

    return ParseResult(
        hints=hints,
        confidence={"object": object_conf, "time": time_conf, "overall": overall},
        missing={"object": not has_object, "time": not has_time},
    )


def _resolve_object(hints: dict) -> dict:
    if hints.get("ad_id"):
        return {"type": "ad_id", "value": hints["ad_id"]}
    if hints.get("campaign_id"):
        return {"type": "campaign_id", "value": hints["campaign_id"]}
    if hints.get("customerId"):
        return {"type": "customerId", "value": hints["customerId"]}
    return {"type": None, "value": None}


def _normalize_relative_day(hints: dict) -> dict:
    if hints.get("start_time") and hints.get("end_time"):
        return hints

    label = hints.get("relative_day_label")
    if not label:
        return hints

    try:
        offset = int(label.replace("D-", ""))
    except ValueError:
        return hints

    base = datetime.now(TZ) - timedelta(days=offset)
    start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    end = base.replace(hour=23, minute=59, second=59, microsecond=0)
    hints["start_time"] = start.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    hints["end_time"] = end.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    return hints


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate minimum input for volume-drop diagnosis.")
    parser.add_argument("--text", required=True, help="raw user text")
    parser.add_argument("--hints-json", help="optional parser hints JSON")
    args = parser.parse_args()

    parse_result = parse_nl_hint(args.text)
    hints = dict(parse_result.hints)

    if args.hints_json:
        try:
            external_hints = json.loads(args.hints_json)
            if isinstance(external_hints, dict):
                hints.update({k: v for k, v in external_hints.items() if v is not None})
        except json.JSONDecodeError:
            pass

    hints = _normalize_relative_day(hints)

    resolved_object = _resolve_object(hints)
    has_object = bool(resolved_object["value"])
    has_time = bool(hints.get("start_time") and hints.get("end_time"))

    missing_fields = []
    suggested_questions = []

    if not has_object:
        missing_fields.append("object_id")
        suggested_questions.append("请至少提供一个异常对象ID：账户ID、计划ID或广告ID（任选其一）。")

    if not has_time:
        missing_fields.append("anomaly_time")
        suggested_questions.append("请补充异常时间（如今天、昨天或具体时间段）。")

    output = {
        "passed": has_object and has_time,
        "has_object": has_object,
        "has_time": has_time,
        "resolved_object": resolved_object,
        "resolved_time_window": {
            "start_time": hints.get("start_time"),
            "end_time": hints.get("end_time"),
            "relative_day_label": hints.get("relative_day_label"),
        },
        "parsed_hints": hints,
        "confidence": parse_result.confidence,
        "missing_fields": missing_fields,
        "suggested_questions": suggested_questions,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
