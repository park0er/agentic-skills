#!/usr/bin/env python3
"""Silent refresh: swap expired _aegis_cas for a fresh one without user interaction.

Flow:
  1. read .cookies.json, verify cas.mioffice.cn.TGC2 is still valid
  2. try a pure HTTP ticket exchange using stored TGC2 + DT2 + nonce:
       biz url -> cas.mioffice.cn/login -> /v2/api/getST -> redirect_to
  3. if the HTTP path fails, fall back to headless Chromium:
       pivot.olap.srv  →  cas.mioffice.cn/login  (CAS validates TGC2)
                       →  p.dun.mioffice.cn/cas/sts  (STS mints ST+ticket)
                       →  pivot.olap.srv/?ticket=...  (biz consumes ticket, sets _aegis_cas)
                       →  pivot.olap.srv
  4. read fresh _aegis_cas from the cookie jar, write it back. Only _aegis_cas.

Fallback semantics: every failure mode returns a structured dict, never raises.
The caller (check_cookies.py) decides whether to escalate to interactive login.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from http.cookiejar import Cookie
from pathlib import Path
from typing import Any, BinaryIO, Iterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from updater.lock import _lock_file, _unlock_file  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parents[2]
COOKIE_FILE = SKILL_ROOT / "state" / ".cookies.json"
LOCK_FILE = SKILL_ROOT / "state" / ".refresh.lock"

CAS_HOST = "cas.mioffice.cn"
CAS_COOKIE_NAMES = ("TGC2", "DT2", "nonce", "cookie.lang")

BIZ_DOMAINS: list[tuple[str, str]] = [
    ("pivot.olap.srv",            "http://pivot.olap.srv/"),
    ("v2.pivot.olap.srv",         "http://v2.pivot.olap.srv/"),
    ("de.pivot.ad.xiaomi.srv",    "http://de.pivot.ad.xiaomi.srv/"),
    ("preview-ds.ad.xiaomi.com",  "https://preview-ds.ad.xiaomi.com/miui-soil-platform/index.html"),
]

# SPA ticket exchange finishes shortly after the `load` event. Measured 2-3s
# in practice; keep the budget a bit loose to absorb network jitter.
SPA_WAIT_MS = 3000
HTTP_TIMEOUT_SECONDS = 45
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# cookie file I/O
# ---------------------------------------------------------------------------
def _load_payload() -> dict[str, Any] | None:
    try:
        return json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _save_payload(payload: dict[str, Any]) -> None:
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = COOKIE_FILE.with_suffix(f".json.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, COOKIE_FILE)


# ---------------------------------------------------------------------------
# TGC2 status probe
# ---------------------------------------------------------------------------
def _cas_status(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return {"ready": bool, "reason": str}.

    Flat-format cookie file:
      payload["cas.mioffice.cn"]["TGC2"]          = "TGT-V2-..."
      payload["cas.mioffice.cn"]["TGC2_expires"]  = "1813052214.57"  (optional)
    """
    if not isinstance(payload, dict):
        return {"ready": False, "reason": "payload_missing"}
    cas = payload.get(CAS_HOST)
    if not isinstance(cas, dict):
        return {"ready": False, "reason": "cas_bucket_missing"}
    tgc2 = cas.get("TGC2")
    if not isinstance(tgc2, str) or not tgc2:
        return {"ready": False, "reason": "tgc2_missing"}
    exp_str = cas.get("TGC2_expires")
    if not exp_str:
        # no expires metadata — trust it (will fail at refresh time if dead)
        return {"ready": True, "reason": "no_expires_treat_as_alive"}
    try:
        if float(exp_str) > time.time():
            return {"ready": True, "reason": "ok"}
        return {"ready": False, "reason": "tgc2_expired"}
    except (TypeError, ValueError):
        return {"ready": False, "reason": "tgc2_expires_malformed"}


# ---------------------------------------------------------------------------
# file lock
# ---------------------------------------------------------------------------
@contextmanager
def _refresh_lock() -> Iterator[bool]:
    """Non-blocking exclusive lock on state/.refresh.lock.

    Yields True if the lock was acquired, False if another process holds it.
    Caller must check the yielded value before proceeding with any write.
    """
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    f: BinaryIO = LOCK_FILE.open("a+b")
    try:
        try:
            _lock_file(f)
        except (BlockingIOError, OSError):
            yield False
            return
        yield True
        try:
            _unlock_file(f)
        except OSError:
            pass
    finally:
        f.close()


# ---------------------------------------------------------------------------
# core refresh
# ---------------------------------------------------------------------------
def _inject_payload(cas_bucket: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Playwright add_cookies payload from the flat cas.mioffice.cn bucket."""
    out: list[dict[str, Any]] = []
    for name in CAS_COOKIE_NAMES:
        value = cas_bucket.get(name)
        if not isinstance(value, str) or not value:
            continue
        item: dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": CAS_HOST,
            "path": "/",
            "secure": name != "cookie.lang",
            "httpOnly": False,
            "sameSite": "Lax",
        }
        exp_str = cas_bucket.get(f"{name}_expires")
        if isinstance(exp_str, str) and exp_str:
            try:
                exp = float(exp_str)
                if exp > 0:
                    item["expires"] = exp
            except ValueError:
                pass
        out.append(item)
    return out


def _make_http_cookie(
    *,
    name: str,
    value: str,
    domain: str,
    expires: str | None = None,
    secure: bool = True,
) -> Cookie:
    expire_value: int | None = None
    if expires:
        try:
            exp = int(float(expires))
            if exp > 0:
                expire_value = exp
        except (TypeError, ValueError):
            expire_value = None

    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=secure,
        expires=expire_value,
        discard=expire_value is None,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def _build_http_cookie_jar(cas_bucket: dict[str, Any]) -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    for name in CAS_COOKIE_NAMES:
        value = cas_bucket.get(name)
        if not isinstance(value, str) or not value:
            continue
        expires = cas_bucket.get(f"{name}_expires")
        jar.set_cookie(
            _make_http_cookie(
                name=name,
                value=value,
                domain=CAS_HOST,
                expires=expires if isinstance(expires, str) else None,
                secure=name != "cookie.lang",
            )
        )
    return jar


def _extract_aegis_from_jar(
    jar: http.cookiejar.CookieJar, domain: str
) -> str | None:
    for cookie in jar:
        if cookie.name != "_aegis_cas":
            continue
        if cookie.domain.lstrip(".") != domain:
            continue
        if isinstance(cookie.value, str) and len(cookie.value) > 20:
            return cookie.value
    return None


def _http_refresh_domain(
    cas_bucket: dict[str, Any], domain: str, url: str
) -> str | None:
    jar = _build_http_cookie_jar(cas_bucket)
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler(),
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with opener.open(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        # Consume a small chunk so urllib finishes response handling while
        # keeping this path cheap for large SPA payloads.
        resp.read(4096)
        final_url = resp.geturl()

    fresh = _extract_aegis_from_jar(jar, domain)
    if fresh:
        return fresh

    service = _service_from_cas_login_url(final_url)
    if not service:
        return None

    redirect_to = _get_st_redirect(opener, service, referer=final_url)
    if not redirect_to:
        return None

    follow_req = urllib.request.Request(
        redirect_to,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": final_url,
        },
    )
    with opener.open(follow_req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        resp.read(4096)
    return _extract_aegis_from_jar(jar, domain)


def _service_from_cas_login_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != CAS_HOST or not parsed.path.startswith("/login"):
        return None
    values = urllib.parse.parse_qs(parsed.query).get("service") or []
    service = values[0] if values else None
    return service if service else None


def _get_st_redirect(
    opener: urllib.request.OpenerDirector,
    service: str,
    *,
    referer: str,
) -> str | None:
    url = "https://cas.mioffice.cn/v2/api/getST?" + urllib.parse.urlencode(
        {"service": service}
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer,
        },
    )
    with opener.open(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not isinstance(data, dict) or data.get("status") != 0:
        return None
    body = data.get("data")
    if not isinstance(body, dict):
        return None
    redirect_to = body.get("redirect_to")
    return redirect_to if isinstance(redirect_to, str) and redirect_to else None


def _refresh_with_http(
    payload: dict[str, Any],
    wanted: list[str],
    url_map: dict[str, str],
) -> dict[str, Any]:
    cas_bucket = payload[CAS_HOST]
    refreshed: list[str] = []
    failed: list[dict[str, str]] = []

    for domain in wanted:
        url = url_map.get(domain)
        if not url:
            failed.append({"domain": domain, "reason": "unknown_domain"})
            continue
        try:
            fresh = _http_refresh_domain(cas_bucket, domain, url)
        except Exception as exc:
            failed.append({"domain": domain, "reason": f"http_error: {exc}"})
            continue
        if fresh:
            payload.setdefault(domain, {})["_aegis_cas"] = fresh
            refreshed.append(domain)
        else:
            failed.append({"domain": domain, "reason": "no_fresh_aegis_cas"})

    ok = len(failed) == 0 and len(refreshed) > 0
    reason = "all_refreshed" if ok else (
        "partial_refresh_failed" if refreshed else "no_domain_refreshed"
    )
    return {
        "ok": ok,
        "method": "http",
        "reason": reason,
        "refreshed": refreshed,
        "failed": failed,
    }


def _refresh_with_browser(
    payload: dict[str, Any],
    wanted: list[str],
    url_map: dict[str, str],
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {"ok": False, "method": "browser",
                "reason": f"playwright_import_error: {exc}",
                "refreshed": [], "failed": []}

    cas_bucket = payload[CAS_HOST]
    inject = _inject_payload(cas_bucket)
    if not any(c["name"] == "TGC2" for c in inject):
        return {"ok": False, "method": "browser", "reason": "tgc2_missing",
                "refreshed": [], "failed": []}

    refreshed: list[str] = []
    failed: list[dict[str, str]] = []

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as exc:
                return {"ok": False, "method": "browser",
                        "reason": f"browser_launch_failed: {exc}",
                        "refreshed": [], "failed": []}
            try:
                ctx = browser.new_context(user_agent=USER_AGENT)
                ctx.add_cookies(inject)

                for domain in wanted:
                    url = url_map.get(domain)
                    if not url:
                        failed.append({"domain": domain, "reason": "unknown_domain"})
                        continue
                    page = ctx.new_page()
                    try:
                        try:
                            page.goto(url, timeout=45000, wait_until="load")
                        except Exception as exc:
                            failed.append({"domain": domain,
                                           "reason": f"goto_error: {exc}"})
                            continue
                        page.wait_for_timeout(SPA_WAIT_MS)

                        jar = ctx.cookies(urls=[url])
                        fresh = next(
                            (c["value"] for c in jar
                             if c.get("name") == "_aegis_cas"
                             and c.get("domain", "").lstrip(".") == domain
                             and isinstance(c.get("value"), str)
                             and len(c["value"]) > 20),
                            None,
                        )
                        if fresh:
                            payload.setdefault(domain, {})["_aegis_cas"] = fresh
                            refreshed.append(domain)
                        else:
                            failed.append({"domain": domain,
                                           "reason": "no_fresh_aegis_cas"})
                    finally:
                        page.close()
            finally:
                browser.close()
    except Exception as exc:
        return {"ok": False, "method": "browser",
                "reason": f"playwright_error: {exc}",
                "refreshed": refreshed, "failed": failed}

    ok = len(failed) == 0 and len(refreshed) > 0
    reason = "all_refreshed" if ok else (
        "partial_refresh_failed" if refreshed else "no_domain_refreshed"
    )
    return {"ok": ok, "method": "browser", "reason": reason,
            "refreshed": refreshed, "failed": failed}


def refresh(targets: list[str] | None = None) -> dict[str, Any]:
    """Attempt silent refresh for the given biz domains (default: all four).

    Returns structured result; never raises.
    """
    payload = _load_payload()
    if payload is None:
        return {"ok": False, "reason": "cookie_file_missing_or_invalid",
                "refreshed": [], "failed": []}

    status = _cas_status(payload)
    if not status["ready"]:
        return {"ok": False, "reason": status["reason"],
                "refreshed": [], "failed": []}

    cas_bucket = payload.get(CAS_HOST)
    if not isinstance(cas_bucket, dict) or not isinstance(cas_bucket.get("TGC2"), str):
        return {"ok": False, "reason": "tgc2_missing",
                "refreshed": [], "failed": []}

    url_map = dict(BIZ_DOMAINS)
    wanted = targets or [d for d, _ in BIZ_DOMAINS]

    with _refresh_lock() as got_lock:
        if not got_lock:
            return {"ok": False, "reason": "lock_busy",
                    "refreshed": [], "failed": []}

        http_result = _refresh_with_http(payload, wanted, url_map)
        if http_result.get("refreshed"):
            try:
                _save_payload(payload)
            except OSError as exc:
                return {"ok": False, "reason": f"save_failed: {exc}",
                        "refreshed": http_result["refreshed"],
                        "failed": http_result["failed"]}
        if http_result.get("ok"):
            return http_result

        browser_result = _refresh_with_browser(payload, wanted, url_map)
        if browser_result.get("refreshed"):
            try:
                _save_payload(payload)
            except OSError as exc:
                return {"ok": False, "reason": f"save_failed: {exc}",
                        "refreshed": browser_result["refreshed"],
                        "failed": browser_result["failed"],
                        "http": http_result}
        browser_result["http"] = http_result
        return browser_result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Silently refresh Xiaomi Ads _aegis_cas using stored TGC2."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print cas_status and exit without refreshing cookies.",
    )
    args = parser.parse_args()

    if args.dry_run:
        status = _cas_status(_load_payload())
        print(json.dumps({"mode": "dry-run", "cas": status},
                         ensure_ascii=False, indent=2))
        return 0 if status["ready"] else 1

    result = refresh()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
