#!/usr/bin/env python3
"""Regression test for Gemini tool-call thought_signature restoration."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path.home() / ".config/xiaomi-gemini/config.json"


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def post(base_url: str, api_key: str, payload: dict[str, object]) -> tuple[int, dict[str, object] | list[object]]:
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def post_raw(base_url: str, api_key: str, payload: dict[str, object]) -> tuple[int, str]:
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def extract_first_stream_tool_call(raw: str) -> dict[str, object]:
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        event_data = line.removeprefix("data:").strip()
        if not event_data or event_data == "[DONE]":
            continue
        chunk = json.loads(event_data)
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            tool_calls = delta.get("tool_calls") or []
            if tool_calls:
                return {"role": "assistant", "tool_calls": tool_calls}
    raise RuntimeError("No streaming tool_call found")

def main() -> int:
    cfg = load_config()
    base_url = f"http://{cfg.get('bind_host', '127.0.0.1')}:{cfg.get('port', 41415)}/v1"
    api_key = str(cfg.get("proxy_api_key") or "anything")
    tool = {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get current time",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    }
    first = {
        "model": "gemini-3.5-flash",
        "user": "xiaomi-gemini-regression",
        "messages": [{"role": "user", "content": "Call get_time once, then summarize the result."}],
        "tools": [tool],
        "tool_choice": "auto",
        "max_tokens": 1024,
    }
    first_status, first_data = post(base_url, api_key, first)
    print(f"FIRST_STATUS={first_status}")
    if first_status != 200 or not isinstance(first_data, dict):
        print(json.dumps(first_data, ensure_ascii=False)[:2000])
        return 1
    assistant = first_data["choices"][0]["message"]
    stripped = json.loads(json.dumps(assistant))
    for tool_call in stripped.get("tool_calls", []):
        tool_call.pop("extra_content", None)
    second = {
        "model": "gemini-3.5-flash",
        "user": "xiaomi-gemini-regression",
        "messages": [
            first["messages"][0],
            stripped,
            {"role": "tool", "tool_call_id": stripped["tool_calls"][0]["id"], "name": "get_time", "content": "2026-06-24 23:03"},
        ],
        "tools": [tool],
        "max_tokens": 1024,
    }
    second_status, second_data = post(base_url, api_key, second)
    print(f"SECOND_STATUS={second_status}")
    if second_status != 200:
        print(json.dumps(second_data, ensure_ascii=False)[:2000])
        return 1
    text = ""
    if isinstance(second_data, dict):
        for choice in second_data.get("choices", []):
            text += choice.get("message", {}).get("content", "") or ""
    print("TEXT=" + text.strip()[:1000])

    stream_first = dict(first)
    stream_first["user"] = "xiaomi-gemini-regression-stream"
    stream_first["stream"] = True
    stream_status, stream_raw = post_raw(base_url, api_key, stream_first)
    print(f"STREAM_FIRST_STATUS={stream_status}")
    if stream_status != 200:
        print(stream_raw[:2000])
        return 1
    stream_assistant = extract_first_stream_tool_call(stream_raw)
    rewritten = json.loads(json.dumps(stream_assistant))
    original_tool_call = rewritten["tool_calls"][0]
    original_tool_call.pop("extra_content", None)
    original_tool_call["id"] = "rewritten-by-responses-bridge"
    original_tool_call["function"]["name"] = "rewritten_exec_command"
    stream_second = {
        "model": "gemini-3.5-flash",
        "user": "xiaomi-gemini-regression-stream",
        "messages": [
            stream_first["messages"][0],
            rewritten,
            {
                "role": "tool",
                "tool_call_id": original_tool_call["id"],
                "name": original_tool_call["function"]["name"],
                "content": "2026-06-24 23:03",
            },
        ],
        "tools": [tool],
        "max_tokens": 1024,
    }
    stream_second_status, stream_second_data = post(base_url, api_key, stream_second)
    print(f"STREAM_SECOND_REWRITTEN_STATUS={stream_second_status}")
    if stream_second_status != 200:
        print(json.dumps(stream_second_data, ensure_ascii=False)[:2000])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
