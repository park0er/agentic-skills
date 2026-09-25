#!/usr/bin/env python3
"""Install, check, repair, and test the xiaomi-gemini OpenAI-compatible proxy."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LABEL = "com.local.xiaomi-gemini-openai-proxy"
SKILL_DIR = Path(__file__).resolve().parents[1]
SOURCE_PROXY_SCRIPT = Path(__file__).resolve().parent / "openai_compatible_proxy.py"
APP_DIR = Path.home() / ".local/share/xiaomi-gemini"
RUN_PROXY_SCRIPT = APP_DIR / "openai_compatible_proxy.py"
CONFIG_DIR = Path.home() / ".config/xiaomi-gemini"
CONFIG_PATH = CONFIG_DIR / "config.json"
PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library/Logs/xiaomi-gemini"
DEFAULT_PORT = 41415

DEFAULT_MIFY_BASE_URL = "https://api.llm.mioffice.cn/v1"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MIFY_MODELS = [
    "zhipuai/glm-5.2",
    "minimax/MiniMax-M3",
    "ppio/pa/gpt-5.5",
    "xiaomi/mimo-v2.5-pro",
    "xiaomi/mimo-v2.5",
    "deepseek/deepseek-v4-pro",
]
DEFAULT_GEMINI_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True)
    if check and result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return run(["launchctl", *args], check=False)


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def select_port(preferred: int) -> int:
    if port_available(preferred):
        return preferred
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
        return preferred
    for port in range(preferred + 1, preferred + 101):
        if port_available(port):
            return port
    raise SystemExit(f"No available localhost port found in {preferred}-{preferred + 100}")


def read_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def write_config(config: dict[str, object]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CONFIG_PATH.chmod(0o600)


def base_url(config: dict[str, object] | None = None) -> str:
    cfg = read_config() if config is None else config
    host = str(cfg.get("bind_host", "127.0.0.1"))
    port = int(cfg.get("port", DEFAULT_PORT))
    return f"http://{host}:{port}/v1"


def upstream_by_name(config: dict[str, object], name: str) -> dict[str, object]:
    for upstream in config.get("upstreams", []):
        if isinstance(upstream, dict) and upstream.get("name") == name:
            return upstream
    return {}


def build_config(args: argparse.Namespace, selected_port: int, existing: dict[str, object] | None = None) -> dict[str, object]:
    existing = existing or {}
    existing_mify = upstream_by_name(existing, "mify")
    existing_gemini = upstream_by_name(existing, "gemini")
    proxy_key = args.proxy_key or ""
    mify_key = args.mify_key or str(existing_mify.get("api_key") or "")
    gemini_key = args.gemini_key or str(existing_gemini.get("api_key") or "")
    if not mify_key:
        raise SystemExit("Missing Mify key. Pass --mify-key on install/repair.")
    if not gemini_key:
        raise SystemExit("Missing Gemini key. Pass --gemini-key on install/repair.")
    return {
        "bind_host": "127.0.0.1",
        "port": selected_port,
        "proxy_api_key": proxy_key,
        "default_upstream": "mify",
        "upstreams": [
            {
                "name": "mify",
                "base_url": args.mify_base_url.rstrip("/"),
                "api_key": mify_key,
                "models": DEFAULT_MIFY_MODELS,
            },
            {
                "name": "gemini",
                "base_url": args.gemini_base_url.rstrip("/"),
                "api_key": gemini_key,
                "models": DEFAULT_GEMINI_MODELS,
            },
        ],
    }


def install_runtime_script() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_PROXY_SCRIPT, RUN_PROXY_SCRIPT)
    RUN_PROXY_SCRIPT.chmod(0o755)


def write_plist() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(RUN_PROXY_SCRIPT), "--config", str(CONFIG_PATH)],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(LOG_DIR / "proxy.out.log"),
        "StandardErrorPath": str(LOG_DIR / "proxy.err.log"),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "SSL_CERT_FILE": "/private/etc/ssl/cert.pem",
            "REQUESTS_CA_BUNDLE": "/private/etc/ssl/cert.pem",
        },
        "WorkingDirectory": str(APP_DIR),
    }
    PLIST_PATH.write_bytes(plistlib.dumps(plist, sort_keys=False))


def install(args: argparse.Namespace) -> None:
    selected_port = select_port(args.port)
    config = build_config(args, selected_port)
    install_runtime_script()
    write_config(config)
    write_plist()
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
        stop(quiet=True)
        time.sleep(0.5)
    start()
    print("installed")
    print(f"base_url: {base_url(config)}")
    print("api_key: accepts any non-empty value")
    print(f"config: {CONFIG_PATH}")


def start() -> None:
    if not PLIST_PATH.exists():
        raise SystemExit(f"No plist found at {PLIST_PATH}. Run install first.")
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode != 0:
        result = launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH))
        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
            raise SystemExit(result.returncode)
    result = launchctl("kickstart", "-k", f"gui/{os.getuid()}/{LABEL}")
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    for _ in range(20):
        ok, _detail = health()
        if ok:
            print(f"started: {LABEL}")
            print(f"healthz: ok {base_url().removesuffix('/v1')}/healthz")
            return
        time.sleep(0.5)
    ok, detail = health()
    print(f"started: {LABEL}")
    print(f"healthz: {'ok' if ok else 'failed'} {base_url().removesuffix('/v1')}/healthz")
    if detail.strip():
        print(detail.strip())


def stop(quiet: bool = False) -> None:
    launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH))
    if not quiet:
        print(f"stopped: {LABEL}")


def restart() -> None:
    stop(quiet=True)
    time.sleep(0.5)
    start()


def health() -> tuple[bool, str]:
    try:
        url = f"{base_url().removesuffix('/v1')}/healthz"
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200, response.read().decode("utf-8")
    except Exception as exc:
        return False, str(exc)


def status() -> None:
    cfg = read_config()
    print(f"label: {LABEL}")
    print(f"plist: {PLIST_PATH} ({'exists' if PLIST_PATH.exists() else 'missing'})")
    print(f"runtime_script: {RUN_PROXY_SCRIPT} ({'exists' if RUN_PROXY_SCRIPT.exists() else 'missing'})")
    print(f"config: {CONFIG_PATH} ({'exists' if CONFIG_PATH.exists() else 'missing'})")
    print(f"base_url: {base_url(cfg)}")
    print("api_key: accepts any non-empty value" if not cfg.get("proxy_api_key") else "api_key: configured")
    result = launchctl("print", f"gui/{os.getuid()}/{LABEL}")
    print(f"launchd: {'loaded' if result.returncode == 0 else 'not loaded'}")
    ok, detail = health()
    print(f"healthz: {'ok' if ok else 'failed'} {base_url(cfg).removesuffix('/v1')}/healthz")
    if detail.strip():
        print(detail.strip())


def show_credentials() -> None:
    cfg = read_config()
    if not cfg:
        raise SystemExit(f"Missing config: {CONFIG_PATH}")
    print(f"OPENAI_BASE_URL={base_url(cfg)}")
    print(f"OPENAI_API_KEY={cfg.get('proxy_api_key') or 'anything'}")


def smoke(model: str, prompt: str) -> None:
    cfg = read_config()
    if not cfg:
        raise SystemExit(f"Missing config: {CONFIG_PATH}")
    body = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url(cfg)}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {cfg.get('proxy_api_key') or 'anything'}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            text = ""
            for choice in data.get("choices", []):
                content = choice.get("message", {}).get("content", "")
                if content:
                    text += content
            print(f"HTTP_STATUS={response.status}")
            print(f"TEXT={text.strip()[:1000]}")
    except urllib.error.HTTPError as exc:
        print(f"HTTP_STATUS={exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:2000])
        raise SystemExit(1)


def repair(args: argparse.Namespace) -> None:
    existing = read_config()
    selected_port = int(existing.get("port", args.port)) if existing else select_port(args.port)
    config = build_config(args, selected_port, existing=existing)
    install_runtime_script()
    write_config(config)
    write_plist()
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
        stop(quiet=True)
        time.sleep(0.5)
    start()
    print("repaired")
    print(f"base_url: {base_url(config)}")


def uninstall(args: argparse.Namespace) -> None:
    if PLIST_PATH.exists():
        stop(quiet=True)
        PLIST_PATH.unlink(missing_ok=True)
        print(f"removed: {PLIST_PATH}")
    else:
        print("plist already missing")
    if args.purge:
        shutil.rmtree(APP_DIR, ignore_errors=True)
        shutil.rmtree(CONFIG_DIR, ignore_errors=True)
        print(f"removed: {APP_DIR}")
        print(f"removed: {CONFIG_DIR}")


def add_shared_install_args(parser: argparse.ArgumentParser, *, require_keys: bool) -> None:
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--proxy-key", help="optional local key; omit to accept any client key")
    parser.add_argument("--mify-key", required=require_keys)
    parser.add_argument("--mify-base-url", default=DEFAULT_MIFY_BASE_URL)
    parser.add_argument("--gemini-key", required=require_keys)
    parser.add_argument("--gemini-base-url", default=DEFAULT_GEMINI_BASE_URL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    install_parser = sub.add_parser("install")
    add_shared_install_args(install_parser, require_keys=True)

    repair_parser = sub.add_parser("repair")
    add_shared_install_args(repair_parser, require_keys=False)

    smoke_parser = sub.add_parser("smoke")
    smoke_parser.add_argument("--model", required=True)
    smoke_parser.add_argument("--prompt", default="Reply with exactly: pong")

    uninstall_parser = sub.add_parser("uninstall")
    uninstall_parser.add_argument("--purge", action="store_true", help="also remove runtime files and saved keys")

    sub.add_parser("status")
    sub.add_parser("start")
    sub.add_parser("restart")
    sub.add_parser("stop")
    sub.add_parser("show-credentials")

    args = parser.parse_args()
    if args.command == "install":
        install(args)
    elif args.command == "repair":
        repair(args)
    elif args.command == "status":
        status()
    elif args.command == "start":
        start()
    elif args.command == "restart":
        restart()
    elif args.command == "stop":
        stop()
    elif args.command == "show-credentials":
        show_credentials()
    elif args.command == "smoke":
        smoke(args.model, args.prompt)
    elif args.command == "uninstall":
        uninstall(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
