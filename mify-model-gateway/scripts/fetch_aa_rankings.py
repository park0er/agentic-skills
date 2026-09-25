#!/usr/bin/env python3
"""Fetch the Artificial Analysis Intelligence Index.

Uses the official Artificial Analysis API when AA_API_KEY or
ARTIFICIAL_ANALYSIS_API_KEY is configured, otherwise scrapes the public
leaderboard page (no auth required), extracts the per-model rows from the
Next.js App Router RSC payload, and caches to disk per day.

Output columns (text mode):
  Rank  Intelligence  R  Vendor       Model Name                AA URL

Where R = 'Y' if it's a reasoning model (thinks before answering → slower
first token), blank otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

AA_PAGE_URL = "https://artificialanalysis.ai/leaderboards/models"
AA_API_URL = "https://artificialanalysis.ai/api/v2/llms/models"
CACHE_DIR = Path.home() / ".cache" / "mify-model-gateway"
USER_AGENT = "Mozilla/5.0 (mify-gateway-skill)"


class FetchError(RuntimeError):
    """Network, auth, or parsing failure from a ranking source."""


def get_aa_api_key() -> str | None:
    for name in ("AA_API_KEY", "ARTIFICIAL_ANALYSIS_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def fetch_aa_html() -> str:
    """Fetch via curl first (uses system cert store / keychain), urllib as fallback.

    The macOS Python framework ships its own SSL store that is often out of
    sync with the system one, causing 'CERTIFICATE_VERIFY_FAILED' on perfectly
    normal HTTPS sites. curl follows the system store and just works.
    """
    curl = shutil.which("curl")
    if curl:
        try:
            out = subprocess.run(
                [curl, "-sSL", "--max-time", "30", "-A", USER_AGENT, AA_PAGE_URL],
                check=True,
                capture_output=True,
                text=True,
            )
            return out.stdout
        except subprocess.CalledProcessError as e:
            last_curl_err = e.stderr.strip() or f"exit {e.returncode}"
    else:
        last_curl_err = "curl not found in PATH"

    # Fallback: urllib with default context
    try:
        req = urllib.request.Request(AA_PAGE_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, ssl.SSLError) as e:
        raise FetchError(f"curl: {last_curl_err}; urllib: {e}") from e


def fetch_aa_api(api_key: str) -> dict:
    req = urllib.request.Request(
        AA_API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace").strip()
        raise FetchError(f"HTTP {e.code} from AA API: {detail}") from e
    except (urllib.error.URLError, ssl.SSLError, TimeoutError) as e:
        raise FetchError(f"AA API request failed: {e}") from e

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"AA API returned non-JSON response: {e}") from e

    rows = payload.get("data")
    if not isinstance(rows, list):
        raise FetchError("AA API JSON did not contain a data[] model list")

    models = normalize_api_models(rows)
    if not models:
        raise FetchError("AA API returned no scored model rows")
    return {
        "fetched_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": AA_API_URL,
        "models": models,
    }


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_api_models(rows: list[dict]) -> list[dict]:
    """Normalize official API rows into the same shape as page-scraped rows."""
    models: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        if row.get("deprecated") is True:
            continue

        evaluations = row.get("evaluations") or {}
        iq = _num(evaluations.get("artificial_analysis_intelligence_index"))
        if iq is None:
            continue

        slug = row.get("slug") or row.get("id")
        if not slug or slug in seen:
            continue
        seen.add(slug)

        creator = row.get("model_creator") or {}
        models.append(
            {
                "id": row.get("id") or slug,
                "slug": slug,
                "name": row.get("name") or slug,
                "label": row.get("short_name") or row.get("shortName") or row.get("name") or slug,
                "vendor": creator.get("name") or row.get("model_creator_name") or "?",
                "country": creator.get("country") or row.get("model_creator_country") or "",
                "release_date": row.get("release_date") or row.get("releaseDate"),
                "reasoning": bool(row.get("reasoning_model") or row.get("reasoningModel")),
                "intelligence": iq,
                "intelligence_estimated": bool(
                    evaluations.get("artificial_analysis_intelligence_index_is_estimated")
                    or row.get("intelligenceIndexIsEstimated")
                ),
                "coding": _num(evaluations.get("artificial_analysis_coding_index")),
                "agentic": _num(evaluations.get("artificial_analysis_agentic_index")),
                "context_window": row.get("context_window_tokens") or row.get("contextWindowTokens"),
                "url": f"https://artificialanalysis.ai/models/{slug}",
            }
        )

    return sorted(models, key=lambda x: -x["intelligence"])


def extract_models(html: str) -> list[dict]:
    """Pull full benchmark records out of the leaderboard RSC payload."""
    chunks = re.findall(r'self\.__next_f\.push\(\[\d+,\s*"(.+?)"\]\)', html, re.S)
    big = "".join(
        c.encode("utf-8").decode("unicode_escape", errors="ignore") for c in chunks
    )

    # Benchmark data record (leaderboard row). intelligenceIndex may be null for
    # models that haven't been scored yet — we drop those.
    pattern = re.compile(
        r'"id":"(?P<id>[^"]+)",'
        r'"name":"(?P<name>[^"]+)",'
        r'"shortName":"(?P<short>[^"]+)",'
        r'"slug":"(?P<slug>[^"]+)",'
        r'"releaseDate":"?(?P<release>[^",]*)"?,'
        r'"reasoningModel":(?P<reasoning>true|false),'
        r'"deprecated":(?P<deprecated>true|false),'
        r'"modelCreatorId":"[^"]+",'
        r'"modelCreatorName":"(?P<vendor>[^"]+)",'
        r'"modelCreatorSlug":"[^"]+",'
        r'"modelCreatorCountry":"(?P<country>[^"]*)",'
        r'"modelCreatorColor":"[^"]+",'
        r'"modelCreatorLogo":"[^"]+",'
        r'"intelligenceIndex":(?P<iq>null|[\d.]+),'
        r'"intelligenceIndexIsEstimated":(?P<estimated>true|false)'
    )

    # Optional extras that may or may not follow (contextWindowTokens is ~1100
    # chars after intelligenceIndexIsEstimated, so we need a generous lookahead).
    extras_pat = re.compile(
        r'"codingIndex":(?P<coding>null|[\d.]+),'
        r'"agenticIndex":(?P<agentic>null|[\d.]+)'
    )
    ctx_pat = re.compile(r'"contextWindowTokens":(?P<ctx>\d+)')

    seen: dict[str, dict] = {}
    for m in pattern.finditer(big):
        if m.group("deprecated") == "true":
            continue
        if m.group("iq") == "null":
            continue

        mid = m.group("id")
        if mid in seen:
            continue

        # Look ahead up to 1500 chars for coding/agentic indexes and context window
        tail = big[m.end() : m.end() + 1500]
        extras = extras_pat.search(tail)
        ctx_m = ctx_pat.search(tail)

        seen[mid] = {
            "id": mid,
            "slug": m.group("slug"),
            "name": m.group("name"),
            "label": m.group("short"),
            "vendor": m.group("vendor"),
            "country": m.group("country"),
            "release_date": m.group("release") or None,
            "reasoning": m.group("reasoning") == "true",
            "intelligence": float(m.group("iq")),
            "intelligence_estimated": m.group("estimated") == "true",
            "coding": (
                float(extras.group("coding"))
                if extras and extras.group("coding") != "null"
                else None
            ),
            "agentic": (
                float(extras.group("agentic"))
                if extras and extras.group("agentic") != "null"
                else None
            ),
            "context_window": int(ctx_m.group("ctx")) if ctx_m else None,
            "url": f"https://artificialanalysis.ai/models/{m.group('slug')}",
        }

    return sorted(seen.values(), key=lambda x: -x["intelligence"])


def cache_file(d: date) -> Path:
    return CACHE_DIR / f"aa-{d.isoformat()}.json"


def fetch_from_page() -> dict:
    html = fetch_aa_html()
    models = extract_models(html)
    if not models:
        raise FetchError(
            "Fetched the page but could not extract any model rows.\n"
            "The page HTML structure may have changed — update the regex in extract_models()."
        )
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": AA_PAGE_URL,
        "models": models,
    }


def load_or_fetch(refresh: bool, source: str = "auto") -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    cf = cache_file(today)

    if cf.exists() and not refresh:
        return json.loads(cf.read_text(encoding="utf-8"))

    api_key = get_aa_api_key()
    errors: list[str] = []
    payload: dict | None = None

    if source in ("auto", "api"):
        if api_key:
            try:
                payload = fetch_aa_api(api_key)
            except FetchError as e:
                errors.append(f"api: {e}")
                if source == "api":
                    sys.exit(f"Cannot fetch {AA_API_URL}: {e}")
                print(f"⚠ AA API failed ({e}); falling back to public leaderboard page", file=sys.stderr)
        elif source == "api":
            sys.exit(
                "AA API source selected, but no API key is configured.\n"
                "Set AA_API_KEY or ARTIFICIAL_ANALYSIS_API_KEY and retry."
            )

    if payload is None and source in ("auto", "page"):
        try:
            payload = fetch_from_page()
        except FetchError as e:
            errors.append(f"page: {e}")

    if payload is None:
        yesterday = cache_file(today - timedelta(days=1))
        if yesterday.exists():
            print(
                f"⚠ fetch failed ({'; '.join(errors)}); using yesterday's cache",
                file=sys.stderr,
            )
            return json.loads(yesterday.read_text(encoding="utf-8"))
        sys.exit(
            f"Cannot fetch Artificial Analysis rankings: {'; '.join(errors)}\n"
            "If you're behind a corporate proxy, set HTTP_PROXY / HTTPS_PROXY and retry.\n"
            "No cached copy from yesterday either."
        )
    cf.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def _fmt_ctx(tokens: int | None) -> str:
    """Format context window tokens for display."""
    if tokens is None:
        return "?"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1000:
        return f"{tokens / 1000:.0f}K"
    return str(tokens)


def print_table(models: list[dict], show_ctx: bool = False) -> None:
    if not models:
        print("No matches.")
        return

    vendor_w = max(len(m["vendor"]) for m in models) + 1
    name_w = max(len(m["label"]) for m in models) + 1

    ctx_header = "  Ctx" if show_ctx else ""
    print(
        f"{'#':>3}  {'IQ':>5}  R  {'Cty':<3}  "
        f"{'Vendor':<{vendor_w}}  {'Model':<{name_w}}  Released{ctx_header}"
    )
    print("-" * (10 + 3 + vendor_w + name_w + 20 + (6 if show_ctx else 0)))
    for i, m in enumerate(models, 1):
        r_flag = "Y" if m["reasoning"] else " "
        iq_str = f"{m['intelligence']:>5.1f}"
        if m["intelligence_estimated"]:
            iq_str = f"~{m['intelligence']:>4.1f}"
        country = (m.get("country") or "?").upper()[:3]
        release = (m.get("release_date") or "")[:10]
        ctx_col = f"  {_fmt_ctx(m.get('context_window')):>4}" if show_ctx else ""
        print(
            f"{i:>3}  {iq_str}  {r_flag}  {country:<3}  "
            f"{m['vendor']:<{vendor_w}}  {m['label']:<{name_w}}  {release}{ctx_col}"
        )


def main() -> None:
    p = argparse.ArgumentParser(
        description="Fetch Artificial Analysis Intelligence Index (cached daily).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  fetch_aa_rankings.py --top 10               # today's top 10\n"
            "  fetch_aa_rankings.py --no-reasoning --top 5  # fastest first-token models\n"
            "  fetch_aa_rankings.py --json                 # raw JSON for programmatic use\n"
            "  fetch_aa_rankings.py --refresh              # bypass today's cache\n"
        ),
    )
    p.add_argument("--top", type=int, default=20, help="number of rows (default 20)")
    p.add_argument(
        "--no-reasoning",
        action="store_true",
        help="drop reasoning models (they think before replying → slower TTFT)",
    )
    p.add_argument(
        "--vendor",
        help="substring filter on vendor (Anthropic, OpenAI, Moonshot, ...)",
    )
    p.add_argument(
        "--country",
        help="filter by model creator country code (us, cn, fr, ...)",
    )
    p.add_argument("--refresh", action="store_true", help="bypass today's cache")
    p.add_argument(
        "--source",
        choices=("auto", "api", "page"),
        default="auto",
        help="ranking source: API with AA_API_KEY when available, public page scrape, or auto (default)",
    )
    p.add_argument("--context", action="store_true", help="show context window column")
    p.add_argument("--json", action="store_true", help="emit raw JSON")
    args = p.parse_args()

    payload = load_or_fetch(args.refresh, args.source)
    models = payload["models"]

    if args.no_reasoning:
        models = [m for m in models if not m["reasoning"]]
    if args.vendor:
        v = args.vendor.lower()
        models = [m for m in models if v in m["vendor"].lower()]
    if args.country:
        c = args.country.lower()
        models = [m for m in models if (m.get("country") or "").lower() == c]

    models = models[: args.top]

    if args.json:
        print(json.dumps(
            {
                "fetched_at": payload["fetched_at"],
                "source": payload["source"],
                "models": models,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return

    print(f"Source: {payload['source']}  Fetched: {payload['fetched_at']}\n")
    print_table(models, show_ctx=args.context)
    print(f"\n(Showing {len(models)} rows. R=Y means reasoning model — slower first token.)")


if __name__ == "__main__":
    main()
