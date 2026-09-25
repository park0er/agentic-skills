#!/usr/bin/env python3
"""Validate a browser-exported usage snapshot and render the approved HTML."""
import argparse
import csv
import io
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value

def parse_day(value):
    if not isinstance(value, str):
        raise ValueError("date must be a string")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("date must be YYYY-MM-DD")
    return result

def load_input(path):
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv":
        csv.field_size_limit(100_000_000)
        rows = list(csv.DictReader(io.StringIO(raw)))
        if len(rows) != 1 or list(rows[0]) != ["report"]:
            raise ValueError("Expected one CSV row and one report column")
        raw = rows[0]["report"]
    return json.loads(raw)

def validate(data):
    start, end = parse_day(data["start"]), parse_day(data["end"])
    days = (end - start).days + 1
    if not 1 <= days <= 366:
        raise ValueError("Expected 1..366 complete calendar days")
    observed = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
    if observed.tzinfo is None or observed.astimezone(TZ).date() <= end:
        raise ValueError("Snapshot must follow the last complete day, with timezone")
    if integer(data["unmatched"], "unmatched") != 0:
        raise ValueError("Unattributed messages: resolve before publishing")
    integer(data["all_work"], "all_work")
    integer(data["all_issue"], "all_issue")
    if not isinstance(data["users"], list):
        raise ValueError("users must be an array")
    emails, work, issue = set(), 0, 0
    for u in data["users"]:
        email = u["email"]
        if not isinstance(email, str) or email != email.strip().lower() or "@" not in email or email in emails:
            raise ValueError("Emails must be normalized, nonempty and unique")
        emails.add(email)
        if not isinstance(u["name"], str):
            raise ValueError("name must be a string")
        registered = parse_day(u["registered"])
        if registered > end:
            raise ValueError("User registered after reporting period")
        integer(u["accounts"], "accounts", 1)
        integer(u["total"], "total")
        if not isinstance(u["daily"], list):
            raise ValueError("daily must be an array")
        previous, subtotal = -1, 0
        for entry in u["daily"]:
            if not isinstance(entry, list) or len(entry) != 3:
                raise ValueError("daily entry must be [index,work,issue]")
            idx, w, i = entry
            integer(idx, "day index")
            integer(w, "work")
            integer(i, "issue")
            if not previous < idx < days or w+i == 0:
                raise ValueError("daily must contain ordered unique nonzero days")
            if start + timedelta(days=idx) < registered:
                raise ValueError("Message predates user registration; verify source")
            previous = idx
            work += w
            issue += i
            subtotal += w+i
        if subtotal != u["total"]:
            raise ValueError("User total does not equal daily counts")
    if (work, issue) != (data["all_work"], data["all_issue"]):
        raise ValueError("Independent event totals do not match user totals")
    data["users"].sort(key=lambda u: (-u["total"], u["email"]))
    return start, end, days, observed

def render(data):
    start, end, days, observed = validate(data)
    template = (Path(__file__).resolve().parent.parent / "assets" / "report.html").read_text(encoding="utf-8")
    replacements = {
        "__START__": start.isoformat(), "__END__": end.isoformat(),
        "__END_EXCLUSIVE__": (end+timedelta(days=1)).isoformat(),
        "__RECENT_START__": max(start,end-timedelta(days=6)).isoformat(),
        "__DAYS__": str(days), "__GENERATED__": observed.astimezone(TZ).date().isoformat()
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return template.replace("__REPORT_DATA__", serialized)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.window:
        end = datetime.now(TZ).date() - timedelta(days=1)
        print(json.dumps({"start":str(end-timedelta(days=29)), "end":str(end), "timezone":"Asia/Shanghai"}))
        return
    if args.input is None or args.output is None:
        parser.error("--input and --output required")
    data = load_input(args.input)
    html = render(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(html)
    print(json.dumps({"output":str(args.output.resolve()),"users":len(data["users"]),
        "active":sum(u["total"]>0 for u in data["users"]),
        "total":data["all_work"]+data["all_issue"],"start":data["start"],"end":data["end"]},ensure_ascii=False))

if __name__ == "__main__":
    main()
