#!/usr/bin/env python3
"""Query Mify gateway (api.llm.mioffice.cn) for available models.

Reads $MIFY_API_KEY from env. Zero pip deps (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict

GATEWAY_URL = "https://api.llm.mioffice.cn/v1/models"


def fetch_models_with_curl(api_key: str) -> list[dict]:
    """Fallback for macOS Python installs with stale CA bundles.

    We pass the sensitive header via a temporary curl config file so the API key
    is not exposed in argv / process listings.
    """
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(f'url = "{GATEWAY_URL}"\n')
        f.write(f'header = "Authorization: Bearer {api_key}"\n')
        f.write("silent\nshow-error\nfail\nmax-time = 15\n")
        cfg = f.name
    os.chmod(cfg, 0o600)
    try:
        out = subprocess.run(
            ["curl", "--config", cfg],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        payload = json.loads(out.stdout)
        return payload.get("data", [])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        sys.exit(f"Cannot reach {GATEWAY_URL} with urllib or curl fallback: {e}")
    finally:
        try:
            os.unlink(cfg)
        except OSError:
            pass


def fetch_models(api_key: str) -> list[dict]:
    req = urllib.request.Request(
        GATEWAY_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from gateway: {e.reason}. Check $MIFY_API_KEY.")
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "CERTIFICATE_VERIFY_FAILED" in reason:
            print(
                "warn: Python TLS certificate verification failed; retrying with curl",
                file=sys.stderr,
            )
            return fetch_models_with_curl(api_key)
        sys.exit(
            f"Cannot reach {GATEWAY_URL}: {e.reason}. "
            "Are you on Xiaomi intranet / VPN?"
        )
    return payload.get("data", [])


def filter_models(
    models: list[dict],
    grep: str | None,
    model_type: str | None,
    owner: str | None,
) -> list[dict]:
    out = models
    if grep:
        needle = grep.lower()
        out = [m for m in out if needle in m["id"].lower()]
    if model_type:
        out = [m for m in out if m.get("model_type", "").lower() == model_type.lower()]
    if owner:
        out = [m for m in out if m.get("owned_by", "").lower() == owner.lower()]
    return out


def group_by_id(models: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in models:
        grouped[m["id"]].append(m)
    return grouped


def print_summary(models: list[dict]) -> None:
    print(f"Total models: {len(models)}")
    types = Counter(m.get("model_type", "?") for m in models)
    owners = Counter(m.get("owned_by", "?") for m in models)
    print("\nBy model_type:")
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t:<16} {n}")
    print("\nBy owned_by:")
    for o, n in sorted(owners.items(), key=lambda x: -x[1]):
        print(f"  {o:<20} {n}")


def print_table(models: list[dict]) -> None:
    if not models:
        print("No matches.")
        return

    grouped = group_by_id(sorted(models, key=lambda m: m["id"].lower()))

    print("Chat endpoint needs '{owner}/{id}' — copy the CALL AS column verbatim.\n")

    rows_out: list[tuple[str, str, str]] = []
    for mid, rows in grouped.items():
        types = ",".join(sorted({r.get("model_type", "?") for r in rows}))
        call_as = "  ".join(
            f"{r.get('owned_by', '?')}/{mid}"
            for r in sorted(rows, key=lambda r: r.get("owned_by", ""))
        )
        rows_out.append((mid, types, call_as))

    id_w = max(len(r[0]) for r in rows_out) + 2
    type_w = max(max((len(r[1]) for r in rows_out), default=4), 4) + 2
    print(f"{'MODEL ID':<{id_w}} {'TYPE':<{type_w}} CALL AS")
    print("-" * (id_w + type_w + 20))
    for mid, types, call_as in rows_out:
        print(f"{mid:<{id_w}} {types:<{type_w}} {call_as}")

    print(f"\n{len(grouped)} unique id(s), {len(models)} total row(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List / filter models on the Mify gateway.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  list_models.py --grep kimi\n"
            "  list_models.py --type embedding\n"
            "  list_models.py --owner xiaomi --type llm\n"
            "  list_models.py --all --summary\n"
            "  list_models.py --grep gpt --json\n"
        ),
    )
    parser.add_argument("--grep", help="case-insensitive substring match on model id")
    parser.add_argument(
        "--type",
        dest="model_type",
        help="filter by model_type (llm, embedding, tts, speech2text, realtime, ...)",
    )
    parser.add_argument("--owner", help="filter by owned_by (xiaomi, tongyi, ...)")
    parser.add_argument(
        "--all", action="store_true", help="required to dump without any filter"
    )
    parser.add_argument(
        "--summary", action="store_true", help="print aggregate counts only"
    )
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    args = parser.parse_args()

    from _keyloader import load_mify_key
    api_key = load_mify_key()

    models = fetch_models(api_key)

    has_filter = bool(args.grep or args.model_type or args.owner)
    if not has_filter and not args.all:
        sys.exit(
            f"Gateway has {len(models)} models. "
            "Refusing to dump everything without a filter.\n"
            "Use --grep / --type / --owner, or pass --all to force."
        )

    filtered = filter_models(models, args.grep, args.model_type, args.owner)

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
        return

    if args.summary:
        print_summary(filtered)
        return

    print_table(filtered)


if __name__ == "__main__":
    main()
