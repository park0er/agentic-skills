#!/usr/bin/env python3
"""Install and operate the local Claude Desktop proxy for non-Claude Mify models."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


LABEL = "com.local.mify-claude-desktop-proxy"
SCRIPT_DIR = Path(__file__).resolve().parent
PROXY_SCRIPT = SCRIPT_DIR / "claude_desktop_proxy.py"
INSTALL_COWORK = SCRIPT_DIR / "install_cowork_config.py"
PYTHON_ORG = Path("/Library/Frameworks/Python.framework/Versions/3.14/bin/python3")
LAUNCHD_PYTHON = str(PYTHON_ORG if PYTHON_ORG.exists() else Path(sys.executable))
LAUNCHD_SSL_CERT_FILE = "/private/etc/ssl/cert.pem"
LOCAL_AGENT_SKILL_DIR = Path.home() / ".agents/skills/mify-model-gateway/scripts"
CONFIG_DIR = Path.home() / ".config/mify/claude-desktop-proxy"
TLS_DIR = CONFIG_DIR / "tls"
MODELS_FILE = CONFIG_DIR / "models.json"
STATE_FILE = CONFIG_DIR / "state.json"
PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library/Logs/mify-claude-desktop-proxy"
DEFAULT_PORT = 41414
DEFAULT_SCHEME = "http"
GATEWAY_PLACEHOLDER_KEY = "local-proxy-placeholder"
DISPLAY_CONTEXT_TAG = "[1m]"


def mark_1m(model_name: str) -> str:
    return f"{model_name}{DISPLAY_CONTEXT_TAG}"

PUBLIC_MODELS = [
    {"name": mark_1m("ppio/pa/claude-opus-4-8"), "supports1m": True},
    {"name": mark_1m("ppio/pa/claude-opus-4-6"), "supports1m": True},
    {"name": mark_1m("ppio/pa/claude-sonnet-4-6"), "supports1m": True},
    {"name": mark_1m("ppio/pa/claude-haiku-4-5"), "supports1m": True},
    {"name": mark_1m("xisheng/claude-opus-4-8"), "supports1m": True},
    {"name": mark_1m("xisheng/claude-opus-4-7"), "supports1m": True},
    {"name": mark_1m("xisheng/claude-sonnet-4-6"), "supports1m": True},
    {"name": mark_1m("xisheng/claude-haiku-4-5"), "supports1m": True},
    {"name": mark_1m("xisheng/claude-fable-5"), "supports1m": True},
]
PARKO_MODELS = [
    {"name": mark_1m("parko/claude-opus-4-8"), "supports1m": True},
    {"name": mark_1m("parko/claude-sonnet-4-6"), "supports1m": True},
]
KIRO_MODELS = [
    {"name": mark_1m("kiro/claude-opus-4-8"), "supports1m": True},
    {"name": mark_1m("kiro/claude-sonnet-4-6"), "supports1m": True},
    {"name": mark_1m("kiro/claude-haiku-4-5"), "supports1m": True},
]
OPENROUTER_MODELS = [
    {"name": mark_1m("openrouter/stealth/ox-alpha"), "supports1m": True},
]
DEFAULT_TRAE_UPSTREAM = "http://127.0.0.1:8000"
DEFAULT_KIRO_UPSTREAM = "http://127.0.0.1:8001"
DEFAULT_KIRO_API_KEY = "kiro-gateway-local-key-2026"
DEFAULT_OPENROUTER_UPSTREAM = "https://openrouter.ai/api/v1"
OPENROUTER_CREDENTIALS_FILE = Path.home() / ".config/mify/openrouter-credentials"
TRAE_SKILL_CANDIDATES = (
    Path.home() / ".agents" / "skills" / "trae-api-proxy",
    Path.home() / ".claude" / "skills" / "trae-api-proxy",
)
KIRO_SKILL_CANDIDATES = (
    Path.home() / ".agents" / "skills" / "kiro-gateway-proxy",
    Path.home() / ".claude" / "skills" / "kiro-gateway-proxy",
)
TRAE_CONFIG_FILE = Path.home() / ".config" / "trae-api-proxy" / "config.env"


def public_model_names(
    model_maps: list[str] | None = None,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> list[str]:
    base = list(PUBLIC_MODELS) + (list(PARKO_MODELS) if enable_parko else []) + (list(KIRO_MODELS) if enable_kiro else [])
    if enable_openrouter:
        base = base + list(OPENROUTER_MODELS)
    names = [item["name"] for item in base]
    for item in model_maps or []:
        if "=" not in item:
            raise SystemExit(f"Invalid --model-map {item!r}; expected external=upstream")
        external = item.split("=", 1)[0].strip()
        if external and external not in names:
            names.append(external)
    return names


def public_model_entries(
    model_maps: list[str] | None = None,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> list[dict[str, object]]:
    base = list(PUBLIC_MODELS) + (list(PARKO_MODELS) if enable_parko else []) + (list(KIRO_MODELS) if enable_kiro else [])
    if enable_openrouter:
        base = base + list(OPENROUTER_MODELS)
    by_name = {item["name"]: dict(item) for item in base}
    for name in public_model_names(model_maps, enable_parko, enable_kiro, enable_openrouter):
        by_name.setdefault(name, {"name": name, "supports1m": True})
    return [by_name[name] for name in public_model_names(model_maps, enable_parko, enable_kiro, enable_openrouter)]


def run(cmd: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if check and result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("MIFY_API_KEY", None)
    return run(["launchctl", *args], check=False, env=env)


def base_url(port: int, scheme: str = DEFAULT_SCHEME) -> str:
    return f"{scheme}://localhost:{port}"


def read_state_port(default: int = DEFAULT_PORT) -> int:
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        port = int(data.get("port", default))
        if 1 <= port <= 65535:
            return port
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return default


def read_state_scheme(default: str = DEFAULT_SCHEME) -> str:
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        scheme = data.get("scheme")
        if scheme in {"http", "https"}:
            return scheme
    except (OSError, TypeError, json.JSONDecodeError):
        pass

    # Legacy state files only stored base_url. Prefer the actual LaunchAgent
    # args when present so a manual HTTP migration is not masked by stale state.
    try:
        if PLIST_PATH.exists():
            plist = plistlib.loads(PLIST_PATH.read_bytes())
            program = plist.get("ProgramArguments", [])
            if isinstance(program, list):
                if "--cert-file" in program or "--key-file" in program:
                    return "https"
                if any(str(item).endswith("claude_desktop_proxy.py") for item in program):
                    return "http"
    except (OSError, plistlib.InvalidFileException, TypeError):
        pass

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        url = str(data.get("base_url", ""))
        if url.startswith("http://"):
            return "http"
        if url.startswith("https://"):
            return "https"
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return default


def read_state_bool(key: str, default: bool = False) -> bool:
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return bool(data.get(key, default))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return default


def read_state_parko(default: bool = False) -> bool:
    return read_state_bool("enable_parko", default)


def read_state_kiro(default: bool = False) -> bool:
    return read_state_bool("enable_kiro", default)


def read_state_openrouter(default: bool = False) -> bool:
    return read_state_bool("enable_openrouter", default)


def write_state(
    port: int,
    scheme: str,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "port": port,
                "scheme": scheme,
                "enable_parko": enable_parko,
                "enable_kiro": enable_kiro,
                "enable_openrouter": enable_openrouter,
                "base_url": base_url(port, scheme),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    STATE_FILE.chmod(0o600)


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
    for port in range(preferred + 1, preferred + 101):
        if port_available(port):
            return port
    raise SystemExit(f"No available localhost port found in {preferred}-{preferred + 100}")


def ensure_tls(trust: bool) -> None:
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    ca_key = TLS_DIR / "ca.key"
    ca_crt = TLS_DIR / "ca.crt"
    server_key = TLS_DIR / "server.key"
    server_csr = TLS_DIR / "server.csr"
    server_crt = TLS_DIR / "server.crt"
    ca_conf = TLS_DIR / "ca.cnf"
    server_conf = TLS_DIR / "server.cnf"
    ext = TLS_DIR / "server.ext"

    def verifies(cert: Path) -> bool:
        if not ca_crt.exists() or not cert.exists():
            return False
        return run(["openssl", "verify", "-CAfile", str(ca_crt), str(cert)], check=False).returncode == 0

    regenerate_server = False
    if not ca_key.exists() or not verifies(ca_crt):
        ca_conf.write_text(
            "[ req ]\n"
            "prompt = no\n"
            "distinguished_name = dn\n"
            "x509_extensions = v3_ca\n"
            "\n"
            "[ dn ]\n"
            "CN = Mify Claude Desktop Local Proxy CA\n"
            "\n"
            "[ v3_ca ]\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid:always,issuer\n"
            "basicConstraints = critical, CA:true, pathlen:0\n"
            "keyUsage = critical, keyCertSign, cRLSign\n",
            encoding="utf-8",
        )
        run(["openssl", "genrsa", "-out", str(ca_key), "4096"])
        run(
            [
                "openssl",
                "req",
                "-x509",
                "-new",
                "-nodes",
                "-key",
                str(ca_key),
                "-sha256",
                "-days",
                "3650",
                "-config",
                str(ca_conf),
                "-out",
                str(ca_crt),
            ]
        )
        regenerate_server = True

    if regenerate_server or not verifies(server_crt):
        server_conf.write_text(
            "[ req ]\n"
            "prompt = no\n"
            "distinguished_name = dn\n"
            "req_extensions = v3_req\n"
            "\n"
            "[ dn ]\n"
            "CN = localhost\n"
            "\n"
            "[ v3_req ]\n"
            "subjectAltName = @alt_names\n"
            "\n"
            "[ alt_names ]\n"
            "DNS.1 = localhost\n"
            "IP.1 = 127.0.0.1\n",
            encoding="utf-8",
        )
        ext.write_text(
            "authorityKeyIdentifier=keyid,issuer\n"
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            "subjectAltName=DNS:localhost,IP:127.0.0.1\n",
            encoding="utf-8",
        )
        run(["openssl", "genrsa", "-out", str(server_key), "2048"])
        run(["openssl", "req", "-new", "-key", str(server_key), "-config", str(server_conf), "-out", str(server_csr)])
        run(
            [
                "openssl",
                "x509",
                "-req",
                "-in",
                str(server_csr),
                "-CA",
                str(ca_crt),
                "-CAkey",
                str(ca_key),
                "-CAcreateserial",
                "-out",
                str(server_crt),
                "-days",
                "825",
                "-sha256",
                "-extfile",
                str(ext),
            ]
        )
        if not verifies(server_crt):
            raise SystemExit("Generated localhost TLS certificate failed verification")
    ca_key.chmod(0o600)
    server_key.chmod(0o600)

    if trust:
        run(
            [
                "security",
                "add-trusted-cert",
                "-d",
                "-r",
                "trustRoot",
                "-k",
                str(Path.home() / "Library/Keychains/login.keychain-db"),
                str(ca_crt),
            ]
        )


def write_models_file(
    model_maps: list[str] | None = None,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_FILE.write_text(
        json.dumps(public_model_entries(model_maps, enable_parko, enable_kiro, enable_openrouter), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MODELS_FILE.chmod(0o600)


def trae_proxy_running() -> bool:
    """Liveness check: is the local Trae API proxy responding on port 8000?"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_trae_skill() -> Path | None:
    """Locate the installed trae-api-proxy skill (agents or claude install dir)."""
    for candidate in TRAE_SKILL_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def kiro_proxy_running() -> bool:
    """Liveness check: is the local Kiro Gateway proxy responding on port 8001?"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_kiro_skill() -> Path | None:
    """Locate the installed kiro-gateway-proxy skill (agents or claude install dir)."""
    for candidate in KIRO_SKILL_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def ensure_trae_proxy() -> tuple[bool, str]:
    """Ensure the local Trae API proxy is running on port 8000 (opt-in parko flow).

    If already running, return OK. Otherwise locate the trae-api-proxy skill and
    drive its setup: extract_credentials.py (if config.env missing) then
    manage_service.py install. If the skill is absent, guide the user to ask
    zhaoxisheng — the skill is not publicly distributable.

    Returns (ok, message).
    """
    if trae_proxy_running():
        return True, "Trae API proxy is already running on port 8000."

    skill_dir = find_trae_skill()
    if skill_dir is None:
        return False, (
            "Trae API proxy skill (trae-api-proxy) is NOT installed.\n"
            "  parko/* models route to localhost:8000 which requires this skill.\n"
            "  This skill is not publicly distributable — ask zhaoxisheng for it,\n"
            "  install it, then re-run: manage_claude_desktop_proxy.py install --apply --enable-parko"
        )

    trae_scripts = skill_dir / "scripts" / "trae-api-proxy"
    extract_script = trae_scripts / "extract_credentials.py"
    manage_script = trae_scripts / "manage_service.py"
    if not extract_script.exists() or not manage_script.exists():
        return False, (
            f"trae-api-proxy skill found at {skill_dir} but its setup scripts are missing.\n"
            "  Ask zhaoxisheng for a complete trae-api-proxy skill."
        )

    if not TRAE_CONFIG_FILE.exists():
        print("Trae credentials not extracted yet. Running extract_credentials.py ...", file=sys.stderr)
        result = subprocess.run([sys.executable, str(extract_script)], text=True, capture_output=True, timeout=120)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        if result.returncode != 0:
            return False, (
                "Trae credential extraction failed (see output above).\n"
                "  Make sure Trae SOLO CN IDE is installed and logged in at least once, then re-run.\n"
                "  Troubleshooting: trae-api-proxy skill references/token-extraction.md"
            )

    print("Installing Trae API proxy LaunchAgent ...", file=sys.stderr)
    result = subprocess.run([sys.executable, str(manage_script), "install"], text=True, capture_output=True, timeout=120)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        return False, (
            "Trae proxy service install failed (see output above).\n"
            "  Logs: ~/.config/trae-api-proxy/service.err.log"
        )

    if trae_proxy_running():
        return True, "Trae API proxy is now running on port 8000."
    return False, (
        "Trae proxy install completed but port 8000 is still not responding.\n"
        "  Check logs: ~/.config/trae-api-proxy/service.err.log\n"
        f"  Or run: python {manage_script} status"
    )


def ensure_kiro_proxy() -> tuple[bool, str]:
    """Ensure the local Kiro Gateway proxy is running on port 8001 (opt-in kiro flow)."""
    if kiro_proxy_running():
        return True, "Kiro Gateway proxy is already running on port 8001."

    skill_dir = find_kiro_skill()
    if skill_dir is None:
        return False, (
            "Kiro Gateway skill (kiro-gateway-proxy) is NOT installed.\n"
            "  kiro/* models route to localhost:8001 which requires this skill.\n"
            "  Install/release that skill, then re-run: manage_claude_desktop_proxy.py install --apply --enable-kiro"
        )

    manage_script = skill_dir / "scripts" / "kiro-gateway-proxy" / "manage_service.py"
    if not manage_script.exists():
        return False, (
            f"kiro-gateway-proxy skill found at {skill_dir} but manage_service.py is missing.\n"
            "  Reinstall/release a complete kiro-gateway-proxy skill."
        )

    print("Installing Kiro Gateway proxy lifecycle service ...", file=sys.stderr)
    result = subprocess.run([sys.executable, str(manage_script), "setup"], text=True, capture_output=True, timeout=240)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        return False, (
            "Kiro Gateway setup failed (see output above).\n"
            "  Make sure Kiro is installed and logged in, then re-run.\n"
            "  Logs: ~/.config/kiro-gateway-proxy/service.err.log"
        )

    if kiro_proxy_running():
        return True, "Kiro Gateway proxy is now running on port 8001."
    return False, (
        "Kiro Gateway setup completed but port 8001 is still not responding.\n"
        "  Check logs: ~/.config/kiro-gateway-proxy/service.err.log\n"
        f"  Or run: python {manage_script} status"
    )


def write_plist(
    port: int,
    scheme: str,
    model_maps: list[str] | None = None,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    proxy_script = LOCAL_AGENT_SKILL_DIR / PROXY_SCRIPT.name
    working_directory = LOCAL_AGENT_SKILL_DIR if proxy_script.exists() else SCRIPT_DIR
    program = [
        "/usr/bin/env",
        "-u",
        "MIFY_API_KEY",
        LAUNCHD_PYTHON,
        str(proxy_script if proxy_script.exists() else PROXY_SCRIPT),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if scheme == "https":
        program.extend(["--cert-file", str(TLS_DIR / "server.crt"), "--key-file", str(TLS_DIR / "server.key")])
    for model_name in public_model_names(model_maps, enable_parko, enable_kiro, enable_openrouter):
        program.extend(["--public-model", model_name])
    for item in model_maps or []:
        program.extend(["--model-map", item])
    if enable_parko:
        program.extend(["--trae-upstream", DEFAULT_TRAE_UPSTREAM])
    if enable_kiro:
        program.extend([
            "--kiro-upstream",
            DEFAULT_KIRO_UPSTREAM,
            "--kiro-api-key",
            DEFAULT_KIRO_API_KEY,
        ])
    if enable_openrouter:
        program.extend(["--openrouter-upstream", DEFAULT_OPENROUTER_UPSTREAM])

    plist = {
        "Label": LABEL,
        "ProgramArguments": program,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(LOG_DIR / "proxy.out.log"),
        "StandardErrorPath": str(LOG_DIR / "proxy.err.log"),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            "SSL_CERT_FILE": LAUNCHD_SSL_CERT_FILE,
        },
        "WorkingDirectory": str(working_directory),
    }
    PLIST_PATH.write_bytes(plistlib.dumps(plist, sort_keys=False))


def configure_desktop(
    apply: bool,
    port: int,
    scheme: str,
    model_maps: list[str] | None = None,
    enable_parko: bool = False,
    enable_kiro: bool = False,
    enable_openrouter: bool = False,
) -> None:
    write_models_file(model_maps, enable_parko, enable_kiro, enable_openrouter)
    cmd = [
        sys.executable,
        str(INSTALL_COWORK),
        "--base-url",
        base_url(port, scheme),
        "--api-key",
        GATEWAY_PLACEHOLDER_KEY,
        "--models-file",
        str(MODELS_FILE),
    ]
    if apply:
        cmd.append("--apply")
    result = run(cmd, check=False)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def health(port: int, scheme: str) -> tuple[bool, str]:
    # Liveness check only: the proxy is loopback-only, and older generated CA
    # certs may be trusted by Keychain/curl but rejected by Python's stricter
    # key-usage validation.
    context = ssl._create_unverified_context()
    try:
        url = f"{base_url(port, scheme)}/healthz"
        if scheme == "https":
            response_ctx = {"context": context}
        else:
            response_ctx = {}
        with urllib.request.urlopen(url, timeout=3, **response_ctx) as response:
            return True, response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def start(port: int | None = None, scheme: str | None = None) -> None:
    port = read_state_port() if port is None else port
    scheme = read_state_scheme() if scheme is None else scheme
    if not PLIST_PATH.exists():
        raise SystemExit(f"No plist found at {PLIST_PATH}. Run install --apply first.")
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode != 0:
        result = launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH))
        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
            raise SystemExit(result.returncode)
    result = launchctl("kickstart", "-k", f"gui/{os.getuid()}/{LABEL}")
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    for _ in range(10):
        ok, _detail = health(port, scheme)
        if ok:
            print(f"started: {LABEL}")
            print(f"healthz: ok {base_url(port, scheme)}/healthz")
            return
        time.sleep(0.5)
    ok, detail = health(port, scheme)
    print(f"started: {LABEL}")
    print(f"healthz: {'ok' if ok else 'failed'} {base_url(port, scheme)}/healthz")
    if detail.strip():
        print(detail.strip())


def stop() -> None:
    launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH))
    print(f"stopped: {LABEL}")


def restart(port: int | None = None, scheme: str | None = None) -> None:
    stop()
    time.sleep(0.5)
    start(port, scheme)


def status(port: int | None = None, scheme: str | None = None) -> None:
    port = read_state_port() if port is None else port
    scheme = read_state_scheme() if scheme is None else scheme
    print(f"label: {LABEL}")
    print(f"plist: {PLIST_PATH} ({'exists' if PLIST_PATH.exists() else 'missing'})")
    print(f"base_url: {base_url(port, scheme)}")
    parko = read_state_parko()
    print(f"parko: {'enabled' if parko else 'disabled'}")
    if parko:
        print(f"  trae proxy (:8000): {'running' if trae_proxy_running() else 'NOT running — parko/* models will fail'}")
    kiro = read_state_kiro()
    print(f"kiro: {'enabled' if kiro else 'disabled'}")
    if kiro:
        print(f"  kiro gateway (:8001): {'running' if kiro_proxy_running() else 'NOT running — kiro/* models will fail'}")
    openrouter = read_state_openrouter()
    print(f"openrouter: {'enabled' if openrouter else 'disabled'}")
    if openrouter:
        has_key = OPENROUTER_CREDENTIALS_FILE.exists()
        print(f"  openrouter key file: {'present' if has_key else 'MISSING — proxy may fail to start'}")
    result = launchctl("print", f"gui/{os.getuid()}/{LABEL}")
    if result.returncode == 0:
        print("launchd: loaded")
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith(("path =", "state =", "pid =", "job state =")):
                print(f"  {stripped}")
    else:
        print("launchd: not loaded")
    ok, detail = health(port, scheme)
    print(f"healthz: {'ok' if ok else 'failed'} {base_url(port, scheme)}/healthz")
    if ok and result.returncode != 0:
        print("note: this port responds, but this LaunchAgent label is not loaded; it may be another local proxy.")
    if detail.strip():
        print(detail.strip())


def install(args: argparse.Namespace) -> None:
    preferred_port = args.port or read_state_port()
    scheme = args.scheme or read_state_scheme()
    enable_parko = read_state_parko() if args.enable_parko is None else args.enable_parko
    enable_kiro = read_state_kiro() if args.enable_kiro is None else args.enable_kiro
    enable_openrouter = read_state_openrouter() if args.enable_openrouter is None else args.enable_openrouter
    if not args.apply:
        print("dry-run: would write LaunchAgent, start proxy, and write Claude Desktop config")
        if scheme == "https":
            print("dry-run: would also generate/trust localhost TLS certs")
        if enable_parko:
            running = trae_proxy_running()
            print(f"dry-run: parko/* models {'WOULD' if running else 'would NOT'} be included (trae proxy on :8000 {'running' if running else 'NOT running'})")
            if not running:
                skill = find_trae_skill()
                if skill:
                    print(f"dry-run: trae-api-proxy skill found at {skill}; install --apply would auto-set it up")
                else:
                    print("dry-run: trae-api-proxy skill NOT installed; ask zhaoxisheng for it (not publicly distributable)")
        if enable_kiro:
            running = kiro_proxy_running()
            print(f"dry-run: kiro/* models {'WOULD' if running else 'would NOT'} be included (kiro gateway on :8001 {'running' if running else 'NOT running'})")
            if not running:
                skill = find_kiro_skill()
                if skill:
                    print(f"dry-run: kiro-gateway-proxy skill found at {skill}; install --apply would auto-set it up")
                else:
                    print("dry-run: kiro-gateway-proxy skill NOT installed; install/release it before enabling kiro/* models")
        if enable_openrouter:
            has_key = OPENROUTER_CREDENTIALS_FILE.exists()
            print(f"dry-run: openrouter/* models WOULD be included (openrouter key file {'present' if has_key else 'MISSING — run install --apply after writing ~/.config/mify/openrouter-credentials'})")
        selected_port = preferred_port
        if not port_available(preferred_port):
            if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
                print(f"note: localhost:{preferred_port} is occupied by the current {LABEL}; install --apply will restart it and try to reuse this port.")
            else:
                selected_port = select_port(preferred_port)
                print(f"note: localhost:{preferred_port} is occupied; install --apply would use localhost:{selected_port}")
        configure_desktop(
            apply=False,
            port=selected_port,
            scheme=scheme,
            model_maps=args.model_map,
            enable_parko=enable_parko,
            enable_kiro=enable_kiro,
            enable_openrouter=enable_openrouter,
        )
        print("\nRe-run with: manage_claude_desktop_proxy.py install --apply")
        return
    if enable_parko:
        ok, msg = ensure_trae_proxy()
        print(msg)
        if not ok:
            print("WARNING: proceeding WITHOUT parko/* models (trae proxy unavailable).", file=sys.stderr)
            enable_parko = False
    if enable_kiro:
        ok, msg = ensure_kiro_proxy()
        print(msg)
        if not ok:
            print("WARNING: proceeding WITHOUT kiro/* models (Kiro Gateway unavailable).", file=sys.stderr)
            enable_kiro = False
    if enable_openrouter:
        if not OPENROUTER_CREDENTIALS_FILE.exists():
            raise SystemExit(
                "OpenRouter key file missing. Write the key to "
                f"{OPENROUTER_CREDENTIALS_FILE} (chmod 600) and re-run install --apply."
            )
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
        stop()
        time.sleep(0.5)
    selected_port = select_port(preferred_port)
    if scheme == "https":
        ensure_tls(trust=not args.no_trust_ca)
    write_plist(selected_port, scheme, args.model_map, enable_parko, enable_kiro, enable_openrouter)
    write_state(selected_port, scheme, enable_parko, enable_kiro, enable_openrouter)
    start(selected_port, scheme)
    configure_desktop(
        apply=True,
        port=selected_port,
        scheme=scheme,
        model_maps=args.model_map,
        enable_parko=enable_parko,
        enable_kiro=enable_kiro,
        enable_openrouter=enable_openrouter,
    )


def uninstall() -> None:
    stop()
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        print(f"removed: {PLIST_PATH}")
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print(f"removed: {STATE_FILE}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--apply", action="store_true", help="write files and mutate Claude Desktop config")
    install_parser.add_argument("--no-trust-ca", action="store_true", help="generate certs but do not trust CA")
    install_parser.add_argument("--port", type=int, help="preferred localhost port; defaults to 41414 or prior state")
    install_parser.add_argument(
        "--scheme",
        choices=("http", "https"),
        help="localhost proxy scheme; defaults to prior state or http to avoid Electron localhost CA warnings",
    )
    install_parser.add_argument(
        "--model-map",
        action="append",
        help="optional custom map external=upstream, e.g. xisheng/claude-sonnet-4-6=xiaomi/mimo-v2.5-pro",
    )
    install_parser.add_argument(
        "--enable-parko",
        action="store_true",
        help="opt-in: expose parko/* models routed to the local Trae API proxy (port 8000); auto-sets-up the trae-api-proxy skill if present",
    )
    install_parser.add_argument(
        "--disable-parko",
        action="store_false",
        dest="enable_parko",
        help="turn off parko/* models while preserving other proxy channels",
    )
    install_parser.set_defaults(enable_parko=None)
    install_parser.add_argument(
        "--enable-kiro",
        action="store_true",
        help="opt-in: expose kiro/* models routed to the local Kiro Gateway proxy (port 8001); auto-sets-up the kiro-gateway-proxy skill if present",
    )
    install_parser.add_argument(
        "--disable-kiro",
        action="store_false",
        dest="enable_kiro",
        help="turn off kiro/* models while preserving other proxy channels",
    )
    install_parser.set_defaults(enable_kiro=None)
    install_parser.add_argument(
        "--enable-openrouter",
        action="store_true",
        help="opt-in: expose openrouter/* models routed to https://openrouter.ai/api/v1; requires ~/.config/mify/openrouter-credentials",
    )
    install_parser.add_argument(
        "--disable-openrouter",
        action="store_false",
        dest="enable_openrouter",
        help="turn off openrouter/* models while preserving other proxy channels",
    )
    install_parser.set_defaults(enable_openrouter=None)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--port", type=int, help="override health-check port")
    status_parser.add_argument("--scheme", choices=("http", "https"), help="override health-check scheme")
    sub.add_parser("start")
    sub.add_parser("restart")
    sub.add_parser("stop")
    sub.add_parser("uninstall")
    sub.add_parser("configure-desktop")
    args = parser.parse_args()

    if args.command == "install":
        install(args)
    elif args.command == "status":
        status(args.port, args.scheme)
    elif args.command == "start":
        start()
    elif args.command == "restart":
        restart()
    elif args.command == "stop":
        stop()
    elif args.command == "uninstall":
        uninstall()
    elif args.command == "configure-desktop":
        configure_desktop(
            apply=True,
            port=read_state_port(),
            scheme=read_state_scheme(),
            enable_parko=read_state_parko(),
            enable_kiro=read_state_kiro(),
            enable_openrouter=read_state_openrouter(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
