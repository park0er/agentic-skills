#!/usr/bin/env python3
"""Smoke-test an LLM on the Mify gateway via /v1/chat/completions.

Reads $MIFY_API_KEY. Only handles model_type=llm; embedding / TTS / ASR
need different endpoints and are intentionally out of scope.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

CHAT_URL = "https://api.llm.mioffice.cn/v1/chat/completions"


def chat(api_key: str, model: str, prompt: str, max_tokens: int) -> tuple[int, float, dict | str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        CHAT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, time.perf_counter() - t0, data
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            body_text = json.dumps(json.loads(body_text), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
        return e.code, time.perf_counter() - t0, body_text
    except urllib.error.URLError as e:
        sys.exit(
            f"Cannot reach {CHAT_URL}: {e.reason}. "
            "Are you on Xiaomi intranet / VPN?"
        )


def describe_error(code: int, payload: dict | str, model: str) -> str:
    body_str = payload if isinstance(payload, str) else json.dumps(payload)

    if code == 400 and "Not supported model" in body_str:
        has_slash = "/" in model
        if not has_slash:
            return (
                "Mify's chat endpoint REQUIRES the '{owner}/{id}' format.\n"
                f"You passed a bare id '{model}'. Re-run with e.g.:\n"
                f"  --model xiaomi/{model}     (Xiaomi self-hosted)\n"
                f"  --model tongyi/{model}     (Aliyun Bailian)\n"
                "Use list_models.py --grep <id> to see which owners carry it."
            )
        return (
            f"'{model}' is not a valid model id on the gateway, even with a\n"
            "non-bare format. Verify with list_models.py --grep <id>. If the id\n"
            "is correct, your key may lack access to this specific owner channel."
        )
    return {
        401: "Token is invalid or expired. Re-issue $MIFY_API_KEY.",
        403: "Forbidden. Your key may not have access to this owner channel.",
        404: "Endpoint not found. Check the gateway URL.",
        429: "Rate-limited. The upstream provider is throttling this key.",
        500: "Gateway / upstream internal error.",
        503: "Upstream unavailable. Try another owner channel.",
    }.get(code, "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke test a chat model on the Mify gateway.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Mify's chat endpoint REQUIRES '{owner}/{id}' format. Bare ids get 400.\n"
            "\n"
            "Examples:\n"
            "  test_model.py --model xiaomi/kimi-k2.5\n"
            "  test_model.py --model tongyi/DeepSeek-R1-0528\n"
            "  test_model.py --model azure_openai/gpt-5 --prompt 'one-line hello'\n"
            "  test_model.py --model siliconflow/moonshotai/Kimi-K2-Thinking\n"
        ),
    )
    parser.add_argument(
        "--model",
        required=True,
        help="'{owner}/{id}' format (e.g. xiaomi/kimi-k2.5). Bare ids are rejected.",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly the three characters: hi!",
        help="user message content",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=128,
        help="default 128; thinking models need more or reply is empty",
    )
    args = parser.parse_args()

    from _keyloader import load_mify_key
    api_key = load_mify_key()

    status, elapsed, payload = chat(api_key, args.model, args.prompt, args.max_tokens)

    print(f"HTTP {status}  ({elapsed * 1000:.0f} ms)")

    if status != 200:
        hint = describe_error(status, payload, args.model)
        if hint:
            print(f"Hint: {hint}")
        print()
        if isinstance(payload, str):
            print(payload)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

    assert isinstance(payload, dict)
    usage = payload.get("usage") or {}
    choices = payload.get("choices") or []
    content = ""
    reasoning = ""
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""

    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    print(
        "tokens: prompt={} completion={} total={}{}".format(
            usage.get("prompt_tokens", "?"),
            usage.get("completion_tokens", "?"),
            usage.get("total_tokens", "?"),
            f" (reasoning={reasoning_tokens})" if reasoning_tokens else "",
        )
    )

    if reasoning:
        print()
        print("--- reasoning ---")
        print(reasoning.strip())

    print()
    print("--- reply ---")
    if content.strip():
        print(content.strip())
    elif reasoning:
        print("(no user-facing content — only reasoning; raise --max-tokens to see reply)")
    else:
        print("(empty response)")


if __name__ == "__main__":
    main()
