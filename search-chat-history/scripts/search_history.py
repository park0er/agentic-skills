#!/usr/bin/env python3
"""Search Claude Code conversation history for keywords."""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def get_projects_dir():
    return Path.home() / ".claude" / "projects"


def extract_snippets(text, keyword, context_len):
    """Extract all occurrences of keyword with surrounding context."""
    snippets = []
    lower_text = text.lower()
    lower_kw = keyword.lower()
    start = 0
    while True:
        idx = lower_text.find(lower_kw, start)
        if idx == -1:
            break
        snip_start = max(0, idx - context_len)
        snip_end = min(len(text), idx + len(keyword) + context_len)
        snippet = text[snip_start:snip_end].replace("\n", " ").strip()
        if snip_start > 0:
            snippet = "..." + snippet
        if snip_end < len(text):
            snippet = snippet + "..."
        snippets.append(snippet)
        start = idx + 1
    return snippets


def extract_text_content(message):
    """Extract readable text from a message content field."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "thinking":
                    parts.append(block.get("thinking", ""))
        return "\n".join(parts)
    return ""


def search_file(filepath, keyword, context_len, max_snippets_per_session):
    """Search a single JSONL file for keyword matches."""
    matches = []
    session_id = filepath.stem
    cwd = None
    first_timestamp = None

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if keyword.lower() not in line.lower():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                rec_type = record.get("type", "")
                if rec_type not in ("user", "assistant"):
                    continue

                if not cwd:
                    cwd = record.get("cwd")
                if not first_timestamp:
                    first_timestamp = record.get("timestamp")
                if not session_id or session_id == filepath.stem:
                    session_id = record.get("sessionId", filepath.stem)

                msg = record.get("message", {})
                text = extract_text_content(msg)
                if not text:
                    continue

                snippets = extract_snippets(text, keyword, context_len)
                if not snippets:
                    continue

                role = msg.get("role", rec_type)
                timestamp = record.get("timestamp", "")

                for snip in snippets:
                    if len(matches) >= max_snippets_per_session:
                        break
                    matches.append({
                        "role": role,
                        "timestamp": timestamp,
                        "snippet": snip,
                    })
                if len(matches) >= max_snippets_per_session:
                    break
    except Exception as e:
        print(f"Warning: error reading {filepath}: {e}", file=sys.stderr)
        return None

    if not matches:
        return None

    return {
        "session_id": session_id,
        "project_dir": cwd or "unknown",
        "first_timestamp": first_timestamp or "",
        "file": str(filepath),
        "match_count": len(matches),
        "snippets": matches,
    }


def main():
    parser = argparse.ArgumentParser(description="Search Claude Code chat history")
    parser.add_argument("keyword", help="Keyword to search for")
    parser.add_argument("--context", type=int, default=80,
                        help="Characters of context around each match (default: 80)")
    parser.add_argument("--max", type=int, default=20, dest="max_results",
                        help="Max sessions to return (default: 20)")
    parser.add_argument("--snippets", type=int, default=5,
                        help="Max snippets per session (default: 5)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        print("Error: ~/.claude/projects/ not found", file=sys.stderr)
        sys.exit(1)

    results = []
    jsonl_files = sorted(projects_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

    # Skip subagent files
    jsonl_files = [f for f in jsonl_files if "/subagents/" not in str(f)]

    for filepath in jsonl_files:
        result = search_file(filepath, args.keyword, args.context, args.snippets)
        if result:
            results.append(result)
        if len(results) >= args.max_results:
            break

    if not results:
        print(f'No results found for "{args.keyword}"')
        sys.exit(0)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f'Found {len(results)} session(s) matching "{args.keyword}"\n')
    for i, r in enumerate(results, 1):
        print(f"{'='*60}")
        print(f"[{i}] Session: {r['session_id']}")
        print(f"    Project: {r['project_dir']}")
        print(f"    Time:    {r['first_timestamp']}")
        print(f"    Matches: {r['match_count']}")
        print(f"    Snippets:")
        for s in r["snippets"]:
            role_tag = "user" if s["role"] == "user" else "asst"
            print(f"      [{role_tag}] {s['snippet']}")
        print()


if __name__ == "__main__":
    main()
