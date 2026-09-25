#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import os
import re
import sys
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SKILL_ROOT = Path(__file__).resolve().parents[2]
COOKIE_FILE = SKILL_ROOT / "state" / ".cookies.json"
AUTH_LOG_DIR = SKILL_ROOT / "state" / "auth_logs"
REQUIRED_DOMAINS = [
    "pivot.olap.srv",
    "v2.pivot.olap.srv",
    "de.pivot.ad.xiaomi.srv",
    "preview-ds.ad.xiaomi.com",
]

PROBE_TARGETS = [
    {
        "domain": "pivot.olap.srv",
        "url": "http://pivot.olap.srv/",
    },
    {
        "domain": "v2.pivot.olap.srv",
        "url": "http://v2.pivot.olap.srv/",
    },
    {
        "domain": "de.pivot.ad.xiaomi.srv",
        "url": "http://de.pivot.ad.xiaomi.srv/",
    },
    {
        "domain": "preview-ds.ad.xiaomi.com",
        "url": "https://preview-ds.ad.xiaomi.com/miui-soil-platform/index.html",
    },
]

BODY_SUCCESS_MARKERS = {
    "pivot.olap.srv": ["Data Explorer", "Imply"],
    "v2.pivot.olap.srv": ["Data Explorer", "Imply"],
    "de.pivot.ad.xiaomi.srv": ["Data Explorer", "Imply"],
    "preview-ds.ad.xiaomi.com": ["息壤业务洞察诊断平台", "miui-soil-platform", "xirang"],
}

PERMISSION_DENIED_REASONS = {
    "midun_unauthorized",
    "xirang_dashboard_unauthorized",
}

XIRANG_DASHBOARD_PERMISSION_MARKERS = [
    "无该看板权限，请联系息壤产品",
]


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _cas_status(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Probe TGC2 liveness for silent refresh eligibility.

    Flat-format bucket:
      payload["cas.mioffice.cn"]["TGC2"]         = "TGT-V2-..."
      payload["cas.mioffice.cn"]["TGC2_expires"] = "1813052214.57"  (optional)
    """
    if not isinstance(payload, dict):
        return {"ready": False, "reason": "payload_missing"}
    cas = payload.get("cas.mioffice.cn")
    if not isinstance(cas, dict):
        return {"ready": False, "reason": "cas_bucket_missing"}
    tgc2 = cas.get("TGC2")
    if not isinstance(tgc2, str) or not tgc2:
        return {"ready": False, "reason": "tgc2_missing"}
    exp_str = cas.get("TGC2_expires")
    if not exp_str:
        return {"ready": True, "reason": "no_expires_treat_as_alive"}
    try:
        if float(exp_str) > time.time():
            return {"ready": True, "reason": "ok"}
        return {"ready": False, "reason": "tgc2_expired"}
    except (TypeError, ValueError):
        return {"ready": False, "reason": "tgc2_expires_malformed"}


def _load_cookie_payload() -> dict[str, Any]:
    try:
        return json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"cookie_file_invalid_json: {exc}") from exc


def _static_check() -> dict[str, Any]:
    if not COOKIE_FILE.exists():
        return {
            "ok": False,
            "reason": "cookie_file_missing",
            "cookie_file": str(COOKIE_FILE),
            "domains": {},
            "missing_domains": REQUIRED_DOMAINS,
        }

    try:
        payload = _load_cookie_payload()
    except ValueError:
        return {
            "ok": False,
            "reason": "cookie_file_invalid_json",
            "cookie_file": str(COOKIE_FILE),
            "domains": {},
            "missing_domains": REQUIRED_DOMAINS,
        }

    missing_domains = []
    summary = {}
    for domain in REQUIRED_DOMAINS:
        value = payload.get(domain, {}).get("_aegis_cas") if isinstance(payload.get(domain), dict) else None
        ready = isinstance(value, str) and len(value) > 20
        summary[domain] = "ready" if ready else "missing"
        if not ready:
            missing_domains.append(domain)

    return {
        "ok": len(missing_domains) == 0,
        "reason": "static_check_passed" if not missing_domains else "cookie_domain_missing",
        "cookie_file": str(COOKIE_FILE),
        "domains": summary,
        "missing_domains": missing_domains,
    }


def _cookie_header_for_domain(payload: dict[str, Any], domain: str) -> str | None:
    cookies = payload.get(domain)
    if not isinstance(cookies, dict) or not cookies:
        return None
    parts = [f"{key}={value}" for key, value in cookies.items() if isinstance(value, str) and value]
    return "; ".join(parts) if parts else None


def _body_matches_markers(body: str, markers: list[str]) -> bool:
    body_lower = body.lower()
    return any(marker.lower() in body_lower for marker in markers if marker)


def _html_attr_value(tag: str, attr_name: str) -> str | None:
    for match in re.finditer(
        r"([a-zA-Z_:][a-zA-Z0-9_:.-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
        tag,
    ):
        name = match.group(1).lower()
        if name != attr_name.lower():
            continue
        value = next(group for group in match.groups()[1:] if group is not None)
        return html.unescape(value).strip()
    return None


def _extract_authority_domain(body: str) -> str | None:
    for match in re.finditer(r"<input\b[^>]*>", body, flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        if (_html_attr_value(tag, "name") or "").lower() == "domain":
            return _html_attr_value(tag, "value")
    return None


def _detect_midun_unauthorized(
    body: str,
    domain: str,
    url: str,
    final_url: str,
) -> dict[str, Any] | None:
    final_url = final_url or url
    body_text = body or ""
    decoded_body = html.unescape(body_text)
    normalized_final_url = final_url.lower()
    body_has_unauthorized = (
        "[midun]用户未授权" in decoded_body or "用户未授权" in decoded_body
    )
    body_has_permission_action = (
        "申请权限" in decoded_body
        or "p.dun.mioffice.cn/cas/authority" in decoded_body.lower()
        or "p.dun.mioffice.cn" in decoded_body.lower()
    )
    final_url_has_midun = "p.dun.mioffice.cn/cas" in normalized_final_url

    if not (
        body_has_unauthorized and (body_has_permission_action or final_url_has_midun)
        or final_url_has_midun and body_has_permission_action
    ):
        return None

    user_match = re.search(r"\[midun\]\s*用户未授权\s*:\s*([^<\s]+)", decoded_body)
    form_match = re.search(r"<form\b[^>]*>", body_text, flags=re.IGNORECASE | re.DOTALL)
    authority_url = _html_attr_value(form_match.group(0), "action") if form_match else None
    authority_domain = _extract_authority_domain(body_text)
    target_domain = authority_domain or domain

    message = (
        f"当前账号未授权访问 {target_domain}。原始探测页面: {url}。"
        f"最终跳转页面: {final_url}。这不是 cookie 过期或登录失败,"
        "不要继续查询该看板,也不要反复刷新 cookie。"
        "请先打开失败页面点击「申请权限」或联系管理员开通权限,"
        "权限开通后再重新执行 check_cookies。"
    )

    return {
        "domain": domain,
        "url": url,
        "final_url": final_url,
        "ok": False,
        "reason": "midun_unauthorized",
        "permission_required": True,
        "unauthorized_user": user_match.group(1) if user_match else None,
        "authority_domain": authority_domain,
        "authority_url": authority_url,
        "message": message,
        "body_excerpt": body_text[:300],
    }


def _detect_xirang_dashboard_unauthorized(
    rendered_text: str,
    domain: str,
    url: str,
    final_url: str,
) -> dict[str, Any] | None:
    body_text = rendered_text or ""
    decoded_text = html.unescape(body_text)
    marker = next(
        (
            marker
            for marker in XIRANG_DASHBOARD_PERMISSION_MARKERS
            if marker in decoded_text
        ),
        None,
    )
    if marker is None:
        return None

    message = (
        f"当前账号没有息壤看板权限。原始探测页面: {url}。"
        f"最终页面: {final_url or url}。页面提示: {marker}。"
        "这不是 cookie 过期或登录失败,不要继续查询该看板,"
        "也不要反复刷新 cookie。请先联系息壤产品开通看板权限,"
        "权限开通后再重新执行 check_cookies。"
    )

    return {
        "domain": domain,
        "url": url,
        "final_url": final_url or url,
        "ok": False,
        "reason": "xirang_dashboard_unauthorized",
        "permission_required": True,
        "unauthorized_user": None,
        "authority_domain": domain,
        "authority_url": None,
        "message": message,
        "body_excerpt": decoded_text[:300],
    }


def _playwright_cookies_for_domain(payload: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    cookies = payload.get(domain)
    if not isinstance(cookies, dict):
        return []
    return [
        {
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "Lax",
        }
        for name, value in cookies.items()
        if isinstance(name, str) and isinstance(value, str) and value
    ]


def _probe_xirang_rendered_permission(
    payload: dict[str, Any],
    domain: str,
    url: str,
) -> dict[str, Any] | None:
    if domain != "preview-ds.ad.xiaomi.com":
        return None
    if "/miui-soil-platform/index.html" not in url:
        return None

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(ignore_https_errors=True)
                cookies = _playwright_cookies_for_domain(payload, domain)
                if cookies:
                    context.add_cookies(cookies)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
                rendered_text = page.locator("body").inner_text(timeout=10000)
                return _detect_xirang_dashboard_unauthorized(
                    rendered_text=rendered_text,
                    domain=domain,
                    url=url,
                    final_url=page.url,
                )
            finally:
                browser.close()
    except Exception:
        return None


def _probe_domain(payload: dict[str, Any], domain: str, url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    cookie_header = _cookie_header_for_domain(payload, domain)
    if cookie_header:
        req.add_header("Cookie", cookie_header)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {
            "domain": domain,
            "url": url,
            "ok": False,
            "reason": "probe_error",
            "error": str(exc),
        }

    if "cas.mioffice.cn/login" in final_url:
        return {
            "domain": domain,
            "url": url,
            "ok": False,
            "reason": "redirected_to_cas",
            "final_url": final_url,
        }

    unauthorized = _detect_midun_unauthorized(body, domain, url, final_url)
    if unauthorized is not None:
        return unauthorized

    rendered_unauthorized = _probe_xirang_rendered_permission(payload, domain, url)
    if rendered_unauthorized is not None:
        return rendered_unauthorized

    markers = BODY_SUCCESS_MARKERS.get(domain) or BODY_SUCCESS_MARKERS["pivot.olap.srv"]
    if not _body_matches_markers(body, markers):
        return {
            "domain": domain,
            "url": url,
            "ok": False,
            "reason": "unexpected_page_content",
            "final_url": final_url,
            "body_excerpt": body[:300],
        }

    return {
        "domain": domain,
        "url": url,
        "ok": True,
        "reason": "probe_ok",
        "final_url": final_url,
    }


def _probe_all_domains(payload: dict[str, Any]) -> dict[str, Any]:
    probes = [
        _probe_domain(payload=payload, domain=spec["domain"], url=spec["url"])
        for spec in PROBE_TARGETS
    ]
    failed = [item["domain"] for item in probes if not item.get("ok")]
    permission_errors = [
        item for item in probes if item.get("reason") in PERMISSION_DENIED_REASONS
    ]
    if permission_errors:
        return {
            "ok": False,
            "mode": "page_probe",
            "reason": "permission_denied",
            "probes": probes,
            "failed_domains": failed,
            "permission_errors": permission_errors,
            "agent_instruction": (
                "不要继续查询这些看板/域名;不要反复刷新 cookie 或重新登录。"
                "先根据 permission_errors 中的 message 提示用户申请权限"
                "或联系息壤产品开通权限,"
                "权限开通后再重新执行 check_cookies。"
            ),
        }
    return {
        "ok": len(failed) == 0,
        "mode": "page_probe",
        "reason": "probe_ok" if not failed else "probe_failed",
        "probes": probes,
        "failed_domains": failed,
    }


def _run_validation(probe_hours: int) -> dict[str, Any]:
    static_result = _static_check()

    # `_cas_status` inspects the same cookie file the static check does.
    # We read the payload once (if the file parses) so the cas block is
    # available in every outcome — both ok and not-ok paths use it.
    try:
        cas_payload: dict[str, Any] | None = _load_cookie_payload() if COOKIE_FILE.exists() else None
    except ValueError:
        cas_payload = None
    cas_block = _cas_status(cas_payload)

    if not static_result["ok"]:
        return {
            "ok": False,
            "reason": static_result["reason"],
            "cookie_file": static_result["cookie_file"],
            "domains": static_result["domains"],
            "missing_domains": static_result["missing_domains"],
            "probe": None,
            "cas": cas_block,
        }

    payload = cas_payload if cas_payload is not None else _load_cookie_payload()
    probe_result = _probe_all_domains(payload)
    result = {
        "ok": probe_result["ok"],
        "reason": (
            "permission_denied"
            if probe_result.get("reason") == "permission_denied"
            else "cookie_probe_passed"
            if probe_result["ok"]
            else "cookie_probe_failed"
        ),
        "cookie_file": static_result["cookie_file"],
        "domains": static_result["domains"],
        "missing_domains": [],
        "probe": probe_result,
        "cas": cas_block,
    }
    if probe_result.get("reason") == "permission_denied":
        result["permission_errors"] = probe_result.get("permission_errors", [])
        result["agent_instruction"] = probe_result.get("agent_instruction")
    return result


def _auth_log_path() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return AUTH_LOG_DIR / f"check_cookies-{stamp}-{os.getpid()}.log"


def _write_auth_log(text: str) -> Path | None:
    if not text.strip():
        return None
    AUTH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _auth_log_path()
    path.write_text(text, encoding="utf-8")
    return path


def _run_fetch_cookies(fetch_cookies) -> tuple[int, str]:
    if _env_enabled("DIAGNOSE_AUTH_VERBOSE"):
        return fetch_cookies(), ""

    output = io.StringIO()
    exit_code = 1
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            exit_code = fetch_cookies()
        except Exception:
            traceback.print_exc()
    return exit_code, output.getvalue()


def _do_interactive_login(probe_hours: int, base_refresh: dict[str, Any]) -> dict[str, Any]:
    """Fetch cookies interactively, then re-validate. Shared by two fallback branches."""
    from fetch_cookies_interactive import fetch_cookies

    fetch_exit, auth_log = _run_fetch_cookies(fetch_cookies)
    result = _run_validation(probe_hours)
    result["refresh"] = {**base_refresh, "fetch_exit_code": fetch_exit}
    if not result.get("ok") or fetch_exit != 0:
        auth_log_file = _write_auth_log(auth_log)
        if auth_log_file is not None:
            result["auth_log_file"] = str(auth_log_file)
            result["refresh"]["auth_log_file"] = str(auth_log_file)
    return result


def _refresh_path(result: dict[str, Any]) -> str | None:
    refresh = result.get("refresh")
    if isinstance(refresh, dict):
        path = refresh.get("path")
        return path if isinstance(path, str) else None
    return None


def _fetch_exit_code(result: dict[str, Any]) -> int | None:
    refresh = result.get("refresh")
    if isinstance(refresh, dict) and isinstance(refresh.get("fetch_exit_code"), int):
        return refresh["fetch_exit_code"]
    return None


def _failed_domains(result: dict[str, Any]) -> list[str]:
    probe = result.get("probe")
    if isinstance(probe, dict) and isinstance(probe.get("failed_domains"), list):
        return [domain for domain in probe["failed_domains"] if isinstance(domain, str)]
    missing = result.get("missing_domains")
    if isinstance(missing, list):
        return [domain for domain in missing if isinstance(domain, str)]
    return []


def _permission_errors(result: dict[str, Any]) -> list[dict[str, Any]]:
    errors = result.get("permission_errors")
    if not isinstance(errors, list):
        return []
    compact = []
    for item in errors:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                key: item[key]
                for key in (
                    "domain",
                    "reason",
                    "message",
                    "authority_domain",
                    "authority_url",
                )
                if key in item
            }
        )
    return compact


def _summary_for(result: dict[str, Any]) -> str:
    if result.get("ok"):
        return "Cookie 已就绪,所有必要域探测通过"

    reason = str(result.get("reason", "unknown"))
    if reason == "permission_denied":
        failed = _failed_domains(result)
        if failed:
            return "权限不足: " + ", ".join(failed)
        return "权限不足"

    fetch_exit = _fetch_exit_code(result)
    if fetch_exit is not None:
        return "交互登录后仍未拿齐必要 Cookie"

    missing = result.get("missing_domains")
    if isinstance(missing, list) and missing:
        return "缺少必要 Cookie: " + ", ".join(str(domain) for domain in missing)

    failed = _failed_domains(result)
    if failed:
        return "Cookie 页面探测失败: " + ", ".join(failed)

    return f"Cookie 检查失败: {reason}"


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    domains = result.get("domains") if isinstance(result.get("domains"), dict) else {}
    compact: dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "reason": str(result.get("reason", "unknown")),
        "summary": _summary_for(result),
    }

    ready = [domain for domain in REQUIRED_DOMAINS if domains.get(domain) == "ready"]
    if ready:
        compact["domains_ready"] = ready

    missing = result.get("missing_domains")
    if isinstance(missing, list) and missing:
        compact["missing_domains"] = missing

    failed = _failed_domains(result)
    if failed:
        compact["failed_domains"] = failed

    refresh_path = _refresh_path(result)
    if refresh_path is not None:
        compact["refresh_path"] = refresh_path

    fetch_exit = _fetch_exit_code(result)
    if fetch_exit is not None:
        compact["fetch_exit_code"] = fetch_exit

    auth_log_file = result.get("auth_log_file")
    if isinstance(auth_log_file, str):
        compact["auth_log_file"] = auth_log_file

    permission_errors = _permission_errors(result)
    if permission_errors:
        compact["permission_errors"] = permission_errors

    instruction = result.get("agent_instruction")
    if isinstance(instruction, str):
        compact["agent_instruction"] = instruction

    return compact


def _emit_result(result: dict[str, Any]) -> None:
    compact = _compact_result(result)
    if _env_enabled("DIAGNOSE_AUTH_FULL_JSON"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(compact, ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Xiaomi Ads cookies with live query probes."
    )
    parser.add_argument(
        "--probe-hours",
        type=int,
        default=24,
        help="Probe query time window in hours. Defaults to 24.",
    )
    parser.add_argument(
        "--refresh-if-invalid",
        action="store_true",
        help="[deprecated] three-tier fallback is now the default; flag kept for backward compat.",
    )
    args = parser.parse_args()
    _ = args.refresh_if_invalid  # kept only to accept the flag from legacy scripts

    result = _run_validation(args.probe_hours)

    if not result["ok"]:
        if result.get("reason") == "permission_denied":
            result["refresh"] = {"path": "none", "reason": "permission_denied"}
            _emit_result(result)
            return 1

        cas = result.get("cas") or {}
        if cas.get("ready"):
            # Tier 1: silent refresh via TGC2. On success short-circuit; on failure fall
            # through to interactive login (tier 2).
            from silent_refresh import refresh as silent_refresh_fn

            silent_result = silent_refresh_fn()
            if silent_result.get("ok"):
                result = _run_validation(args.probe_hours)
                result["refresh"] = {"path": "silent", **silent_result}
            else:
                result = _do_interactive_login(
                    args.probe_hours,
                    {"path": "silent_then_interactive", "silent": silent_result},
                )
        else:
            # Tier 3: TGC2 dead or missing — interactive login is the only option.
            result = _do_interactive_login(
                args.probe_hours,
                {
                    "path": "interactive_only",
                    "reason": cas.get("reason", "no_cas_status"),
                },
            )
    else:
        result["refresh"] = {"path": "none", "reason": "validation_passed"}

    _emit_result(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
