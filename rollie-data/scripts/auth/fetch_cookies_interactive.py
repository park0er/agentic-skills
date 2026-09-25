#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth.paths import AUTH_DIR, COOKIE_FILE, LEGACY_COOKIE_FILE, ROLLIE_HOME, SKILL_ROOT  # noqa: E402

# Turnilo uses hash-based routing (#DataCubeName) instead of /dashboard/ paths.
TARGET_DOMAINS = [
    {
        "domain": "pivot.olap.srv",
        "urls": [
            "http://pivot.olap.srv/#GuyuDiagnosisLog",
            "http://pivot.olap.srv/#GuyuRecallStat",
            "http://pivot.olap.srv/#ocpxStrategyServiceLog",
            "http://pivot.olap.srv/#emi-diagnosis-log",
            "http://pivot.olap.srv/#RequestInfo",
            "http://pivot.olap.srv/#rtaStat",
            "http://pivot.olap.srv/#OcpxTracking",
        ],
    },
    {
        "domain": "v2.pivot.olap.srv",
        "urls": [
            "http://v2.pivot.olap.srv/#MiuiAdBiMinuteCubeNoExp",
        ],
    },
    {
        "domain": "de.pivot.ad.xiaomi.srv",
        "urls": [
            "http://de.pivot.ad.xiaomi.srv/#DeliveryDiagnosisLog",
        ],
    },
    {
        "domain": "ds.ad.xiaomi.com",
        "urls": [
            "https://ds.ad.xiaomi.com/miui-soil-platform/index.html#/olapMultiQuery/beforeExposure/10",
            "https://ds.ad.xiaomi.com/miui-soil-platform/index.html",
            "https://ds.ad.xiaomi.com/",
        ],
    },
]

MACOS_BROWSER_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _cookie_ready_for_domain(all_cookies: list[dict], domain: str) -> bool:
    for cookie in all_cookies:
        if cookie.get("name") != "_aegis_cas":
            continue
        if len(cookie.get("value", "")) <= 20:
            continue
        if cookie.get("domain", "").lstrip(".") == domain:
            return True
    return False


def _launch_browser(playwright):
    launch_attempts: list[str] = []

    try:
        return playwright.chromium.launch(headless=False)
    except Exception as exc:
        launch_attempts.append(f"bundled chromium: {exc}")

    try:
        return playwright.chromium.launch(channel="chrome", headless=False)
    except Exception as exc:
        launch_attempts.append(f"system Chrome: {exc}")

    for candidate in MACOS_BROWSER_CANDIDATES:
        path = Path(candidate)
        if not path.exists():
            continue
        try:
            return playwright.chromium.launch(executable_path=str(path), headless=False)
        except Exception as exc:
            launch_attempts.append(f"{candidate}: {exc}")

    raise RuntimeError(
        "\n"
        "[auth] 无法启动浏览器，所有回退路径均失败。\n"
        "\n"
        "解决方法（按顺序尝试）：\n"
        "  1. 安装 playwright 内置 Chromium（推荐，一次性）：\n"
        "       python3 -m playwright install chromium\n"
        "  2. 或安装系统 Chrome：https://www.google.com/chrome/\n"
        "  3. 或通过环境变量指定浏览器路径：\n"
        "       PLAYWRIGHT_BROWSERS_PATH=/your/path python3 fetch_cookies_interactive.py\n"
        "\n"
        "各路径详细错误：\n"
        + "\n".join(f"  - {a}" for a in launch_attempts)
    )


def _wait_for_login_cookie(context, page, primary_url: str, domain: str, login_timeout_seconds: int | None) -> bool:
    if login_timeout_seconds and login_timeout_seconds > 0:
        print(f"[auth] waiting for login cookie on {domain} (max {login_timeout_seconds}s)")
        deadline = time.time() + login_timeout_seconds
    else:
        print(f"[auth] waiting for login cookie on {domain} (no timeout, press Ctrl+C to cancel)")
        deadline = None

    last_progress_log = 0.0
    while True:
        try:
            current = context.cookies(urls=[primary_url])
        except Exception as exc:
            print(f"[auth] warning: cookie read failed for {domain}: {exc}")
            return False

        if _cookie_ready_for_domain(current, domain):
            print(f"[auth] login cookie detected on {domain}")
            return True

        now = time.time()
        if deadline and now >= deadline:
            print(f"[auth] error: login cookie missing on {domain}, timeout reached")
            return False

        if now - last_progress_log >= 30:
            if deadline:
                remaining = max(int(deadline - now), 0)
                print(f"[auth] still waiting for {domain} login ({remaining}s remaining)")
            else:
                print(f"[auth] still waiting for {domain} login")
            last_progress_log = now

        page.wait_for_timeout(1000)


def fetch_cookies(login_timeout_seconds: int | None = None) -> int:
    print("[auth] launching browser for interactive login")
    captured: dict[str, dict[str, str]] = {}

    with sync_playwright() as p:
        try:
            browser = _launch_browser(p)
        except Exception as exc:
            print(f"[auth] error: {exc}")
            return 1
        context = browser.new_context()

        for index, target in enumerate(TARGET_DOMAINS, start=1):
            domain = target["domain"]
            urls = target["urls"]
            page = context.new_page()
            primary_url = urls[0]

            print(f"[auth] [{index}/{len(TARGET_DOMAINS)}] open {primary_url}")
            try:
                page.goto(primary_url, timeout=60000)
            except Exception as exc:
                print(f"[auth] warning: open failed for {domain}: {exc}")

            login_ok = _wait_for_login_cookie(
                context=context,
                page=page,
                primary_url=primary_url,
                domain=domain,
                login_timeout_seconds=login_timeout_seconds,
            )

            if not login_ok:
                print(f"[auth] error: login cookie missing on {domain}, skip")
                page.close()
                continue

            if len(urls) > 1:
                print(f"[auth] privilege warmup across {len(urls) - 1} dashboards")
                for url in urls[1:]:
                    try:
                        print(f"[auth] warmup {url}")
                        page.goto(url, timeout=30000)
                        page.wait_for_timeout(1500)
                    except Exception as exc:
                        print(f"[auth] warning: warmup failed: {exc}")

            final_cookies = context.cookies(urls=[primary_url])
            required_cookies = {"uLocale", "AMP_API_KEY", "AMP_MKTG_API_KEY", "_aegis_cas", "cUserId"}
            for cookie in final_cookies:
                if cookie.get("name") not in required_cookies:
                    continue
                if len(cookie.get("value", "")) <= 5:
                    continue
                if cookie.get("domain", "").lstrip(".") != domain:
                    continue

                captured.setdefault(domain, {})[cookie["name"]] = cookie["value"]
                print(f"[auth] saved {cookie['name']} for {domain} (len={len(cookie['value'])})")

            page.close()

        # CAS 根域 cookie 采集(for silent_refresh; 不属于 TARGET_DOMAINS,不受契约测试约束)
        # 业务域登录是 CAS 302 链路的产物,此时 TGC2/DT2/nonce 已经在 context 里
        #
        # 前置条件:**至少一个业务域采到了 _aegis_cas**。CAS cookie 只是 silent refresh 的
        # 伴生数据,没有业务域 cookie 它单独留着没意义(下一次查询照样会炸),因此业务域全
        # 采集失败时直接丢弃 CAS cookie,避免污染 .cookies.json 和 give false sense of success。
        if captured:
            try:
                cas_jar = context.cookies(urls=["https://cas.mioffice.cn/"])
            except Exception as exc:
                print(f"[auth] warning: failed to read cas.mioffice.cn cookies: {exc}")
                cas_jar = []
            cas_bucket: dict[str, str] = {}
            for cookie in cas_jar:
                if cookie.get("domain", "").lstrip(".") != "cas.mioffice.cn":
                    continue
                name = cookie.get("name")
                if name not in {"TGC2", "DT2", "nonce", "cookie.lang"}:
                    continue
                value = cookie.get("value", "")
                if not isinstance(value, str) or not value:
                    continue
                cas_bucket[name] = value
                exp = cookie.get("expires", -1)
                if isinstance(exp, (int, float)) and exp > 0:
                    cas_bucket[f"{name}_expires"] = repr(float(exp))
            if cas_bucket.get("TGC2"):
                captured["cas.mioffice.cn"] = cas_bucket
                print(f"[auth] saved {len(cas_bucket)} CAS cookies for silent refresh "
                      f"(names: {sorted(k for k in cas_bucket if not k.endswith('_expires'))})")
            else:
                print("[auth] warning: TGC2 not seen on cas.mioffice.cn; "
                      "silent refresh will be disabled — users must re-login manually on expiry")

        browser.close()

    required_business_domains = {t["domain"] for t in TARGET_DOMAINS}
    business_domains_captured = {
        d for d in captured
        if d != "cas.mioffice.cn"
        and isinstance(captured.get(d), dict)
        and isinstance(captured[d].get("_aegis_cas"), str)
        and len(captured[d]["_aegis_cas"]) > 20
    }
    missing = required_business_domains - business_domains_captured
    if missing:
        print(f"[auth] incomplete login: missing _aegis_cas for {sorted(missing)}. "
              f"All {len(required_business_domains)} business domains must be logged in.")
        return 1

    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(values) for values in captured.values())
    print(f"[auth] saved {total} cookies for {len(captured)} domains -> {COOKIE_FILE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Xiaomi Ads cookies with an interactive browser session.")
    parser.add_argument(
        "--login-timeout-seconds",
        type=int,
        default=0,
        help="Per-domain login wait timeout. Use 0 to wait indefinitely. Defaults to 0.",
    )
    args = parser.parse_args()

    timeout = args.login_timeout_seconds if args.login_timeout_seconds > 0 else None
    return fetch_cookies(login_timeout_seconds=timeout)


if __name__ == "__main__":
    raise SystemExit(main())
