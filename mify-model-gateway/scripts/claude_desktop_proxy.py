#!/usr/bin/env python3
"""Local Anthropic-compatible proxy for Claude Desktop non-Claude Mify models."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import signal
import ssl
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


DEFAULT_UPSTREAM = "https://api.llm.mioffice.cn/anthropic"
DEFAULT_TRAE_UPSTREAM = "http://127.0.0.1:8000"
DEFAULT_KIRO_UPSTREAM = "http://127.0.0.1:8001"
DEFAULT_KIRO_API_KEY = "kiro-gateway-local-key-2026"
DEFAULT_OPENROUTER_UPSTREAM = "https://openrouter.ai/api/v1"
DISPLAY_CONTEXT_TAG = "[1m]"


def mark_1m(model_name: str) -> str:
    return f"{model_name}{DISPLAY_CONTEXT_TAG}"


DEFAULT_PUBLIC_MODELS = (
    mark_1m("ppio/pa/claude-opus-4-7"),
    mark_1m("ppio/pa/claude-opus-4-6"),
    mark_1m("ppio/pa/claude-sonnet-4-6"),
    mark_1m("ppio/pa/claude-haiku-4-5"),
    mark_1m("xisheng/claude-opus-4-8"),
    mark_1m("xisheng/claude-opus-4-7"),
    mark_1m("xisheng/claude-sonnet-4-6"),
    mark_1m("xisheng/claude-haiku-4-5"),
    mark_1m("xisheng/claude-fable-5"),
    mark_1m("openrouter/stealth/ox-alpha"),
)
DEFAULT_MODEL_MAP = {
    # Bare Claude model names used by tools like Paseo that hardcode slugs
    "claude-haiku-4-5": "xiaomi/mimo-v2.5-pro",
    "xisheng/claude-opus-4-8": "minimax/MiniMax-M3",
    "xisheng/claude-opus-4-7": "deepseek/deepseek-v4-pro",
    "xisheng/claude-sonnet-4-6": "xiaomi/mimo-v2.5-pro",
    "xisheng/claude-haiku-4-5": "xiaomi/mimo-v2.5",
    "xisheng/claude-fable-5": "zhipuai/glm-5.2",
    "claude-haiku-4-5-20251001": "ppio/pa/claude-haiku-4-5",
    "openrouter/stealth/ox-alpha": "stealth/ox-alpha",
}
PARKO_PREFIX = "parko/"
KIRO_PREFIX = "kiro/"
OPENROUTER_PREFIX = "openrouter/"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}
CONTEXT_TAG_RE = re.compile(r"\[(?:1m|1M)\]$")
ONE_M_CONTEXT_TOKENS = 1_000_000


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_mify_key() -> str | None:
    if os.environ.get("MIFY_API_KEY"):
        return os.environ["MIFY_API_KEY"].strip()
    credentials = Path.home() / ".config/mify/credentials"
    if not credentials.exists():
        return None
    for raw_line in credentials.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if line.startswith("MIFY_API_KEY="):
            value = line.split("=", 1)[1].strip().strip("'\"")
            if value:
                return value
    return None


def load_openrouter_key() -> str | None:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"].strip()
    credentials = Path.home() / ".config/mify/openrouter-credentials"
    if not credentials.exists():
        return None
    for raw_line in credentials.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if line.startswith("OPENROUTER_API_KEY="):
            value = line.split("=", 1)[1].strip().strip("'\"")
            if value:
                return value
        # Accept a bare key line too (no variable name).
        if line.startswith("sk-or-") and not line.startswith("="):
            return line
    return None


@dataclass(frozen=True)
class UpstreamTarget:
    host: str
    port: int
    prefix: str
    scheme: str
    api_key: str


@dataclass(frozen=True)
class ProxyConfig:
    upstream_host: str
    upstream_port: int
    upstream_prefix: str
    upstream_scheme: str
    upstream_base: str
    public_models: tuple[str, ...]
    model_map: dict[str, str]
    api_key: str
    verbose: bool
    trae_upstream: UpstreamTarget | None = None
    kiro_upstream: UpstreamTarget | None = None
    openrouter_upstream: UpstreamTarget | None = None


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "mify-claude-desktop-proxy/0.1"
    config: ProxyConfig

    def log_message(self, fmt: str, *args: object) -> None:
        if self.config.verbose:
            super().log_message(fmt, *args)

    def _route_path(self) -> str:
        return urlparse(self.path).path.rstrip("/")

    def do_GET(self) -> None:  # noqa: N802
        route_path = self._route_path()
        if route_path == "/healthz":
            self._send_json(
                200,
                {
                    "ok": True,
                    "upstream_base": self.config.upstream_base,
                    "public_models": list(self.config.public_models),
                    "model_map": self.config.model_map,
                },
            )
            return
        if route_path == "/v1/models":
            self._send_json(200, self._models_payload())
            return
        self._send_json(404, {"error": {"type": "not_found", "message": "Unknown route"}})

    def do_POST(self) -> None:  # noqa: N802
        route_path = self._route_path()
        if not route_path.startswith("/v1/"):
            self._send_json(404, {"error": {"type": "not_found", "message": "Unknown route"}})
            return

        body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
        original_model = None
        upstream_model = None
        upstream_kind = "mify"
        payload = None

        if body:
            try:
                maybe_payload = json.loads(body.decode("utf-8"))
                if isinstance(maybe_payload, dict):
                    payload = maybe_payload
                    original_model = payload.get("model")
                    upstream_model, upstream_kind = self._resolve_model(original_model)
                    if upstream_model and upstream_model != original_model:
                        payload["model"] = upstream_model
                        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            except Exception as exc:
                if route_path.startswith("/v1/messages"):
                    self._send_json(
                        400,
                        {"error": {"type": "invalid_request_error", "message": f"Could not parse JSON: {exc}"}},
                    )
                    return

        if route_path.endswith("/count_tokens"):
            self._send_json(200, {"input_tokens": self._estimate_input_tokens(payload)})
            return

        request_meta = {
            "path": self.path,
            "original_model": original_model,
            "upstream_model": upstream_model,
            "upstream_kind": upstream_kind,
            "request_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "has_anthropic_beta": bool(self.headers.get("anthropic-beta")),
            "anthropic_beta": self.headers.get("anthropic-beta"),
        }

        if self.config.verbose and original_model:
            self._log_event("request", request_meta)

        self._proxy_to_upstream(body, request_meta, upstream_kind)

    def _resolve_model(self, model: object) -> tuple[str | None, str]:
        if not isinstance(model, str) or not model:
            return None, "mify"
        normalized = CONTEXT_TAG_RE.sub("", model)
        if normalized.startswith(PARKO_PREFIX):
            upstream_kind = "trae"
        elif normalized.startswith(KIRO_PREFIX):
            upstream_kind = "kiro"
        elif normalized.startswith(OPENROUTER_PREFIX):
            upstream_kind = "openrouter"
        else:
            upstream_kind = "mify"
        mapped = self.config.model_map.get(normalized, normalized)
        return mapped, upstream_kind

    def _upstream_model(self, model: object) -> str | None:
        mapped, _upstream_kind = self._resolve_model(model)
        return mapped

    def _estimate_input_tokens(self, payload: object) -> int:
        if not isinstance(payload, dict):
            return 1
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return max(1, len(text) // 4)

    def _proxy_to_upstream(self, body: bytes, request_meta: dict[str, object], upstream_kind: str = "mify") -> None:
        if upstream_kind == "trae" and self.config.trae_upstream is not None:
            target = self.config.trae_upstream
        elif upstream_kind == "kiro" and self.config.kiro_upstream is not None:
            target = self.config.kiro_upstream
        elif upstream_kind == "openrouter" and self.config.openrouter_upstream is not None:
            target = self.config.openrouter_upstream
        else:
            target = UpstreamTarget(
                host=self.config.upstream_host,
                port=self.config.upstream_port,
                prefix=self.config.upstream_prefix,
                scheme=self.config.upstream_scheme,
                api_key=self.config.api_key,
            )

        headers = {
            "Content-Type": self.headers.get("content-type", "application/json"),
            "Content-Length": str(len(body)),
            "Accept": self.headers.get("accept", "application/json"),
            "User-Agent": self.headers.get("user-agent", self.server_version),
            "Authorization": f"Bearer {target.api_key}",
        }
        for name in ("anthropic-version", "anthropic-beta"):
            value = self.headers.get(name)
            if value:
                headers[name] = value

        conn_cls = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(target.host, target.port, timeout=300)
        try:
            conn.request(self.command, f"{target.prefix}{self.path}", body=body, headers=headers)
            response = conn.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP_HEADERS:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()

            if response.status >= 400:
                response_body = response.read()
                self._log_event(
                    "upstream_error",
                    {
                        **request_meta,
                        "status": response.status,
                        "reason": response.reason,
                        "error_preview": response_body[:2000].decode("utf-8", errors="replace"),
                    },
                )
                self.wfile.write(response_body)
                self.wfile.flush()
                return

            if self.config.verbose:
                self._log_event("upstream_ok", {**request_meta, "status": response.status, "reason": response.reason})

            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._log_event("proxy_error", {**request_meta, "message": str(exc)})
            self._send_json(502, {"error": {"type": "upstream_error", "message": str(exc)}})
        finally:
            conn.close()

    def _log_event(self, event: str, payload: dict[str, object]) -> None:
        print(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "event": event,
                    **payload,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )

    def _models_payload(self) -> dict[str, object]:
        data = [
            {
                "id": model,
                "type": "model",
                "display_name": model,
                "created_at": "2026-05-01T00:00:00Z",
                "supports1m": True,
                "context_window": ONE_M_CONTEXT_TOKENS,
                "contextWindow": ONE_M_CONTEXT_TOKENS,
                "context_window_tokens": ONE_M_CONTEXT_TOKENS,
                "contextWindowTokens": ONE_M_CONTEXT_TOKENS,
                "max_context_window": ONE_M_CONTEXT_TOKENS,
                "maxContextWindow": ONE_M_CONTEXT_TOKENS,
            }
            for model in self.config.public_models
        ]
        return {
            "model_map": self.config.model_map,
            "data": data,
            "has_more": False,
            "first_id": data[0]["id"] if data else None,
            "last_id": data[-1]["id"] if data else None,
        }

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)


def build_config(args: argparse.Namespace) -> ProxyConfig:
    parsed = urlparse(args.upstream_base.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(f"Invalid upstream URL: {args.upstream_base}")

    api_key = args.api_key or load_mify_key()

    trae_upstream: UpstreamTarget | None = None
    if args.trae_upstream:
        trae_parsed = urlparse(args.trae_upstream.rstrip("/"))
        if trae_parsed.scheme not in {"http", "https"} or not trae_parsed.netloc:
            raise SystemExit(f"Invalid trae upstream URL: {args.trae_upstream}")
        trae_upstream = UpstreamTarget(
            host=trae_parsed.hostname or "",
            port=trae_parsed.port or (443 if trae_parsed.scheme == "https" else 80),
            prefix=trae_parsed.path.rstrip("/"),
            scheme=trae_parsed.scheme,
            api_key=args.trae_api_key or "sk-trae",
        )

    kiro_upstream: UpstreamTarget | None = None
    if args.kiro_upstream:
        kiro_parsed = urlparse(args.kiro_upstream.rstrip("/"))
        if kiro_parsed.scheme not in {"http", "https"} or not kiro_parsed.netloc:
            raise SystemExit(f"Invalid kiro upstream URL: {args.kiro_upstream}")
        kiro_upstream = UpstreamTarget(
            host=kiro_parsed.hostname or "",
            port=kiro_parsed.port or (443 if kiro_parsed.scheme == "https" else 80),
            prefix=kiro_parsed.path.rstrip("/"),
            scheme=kiro_parsed.scheme,
            api_key=args.kiro_api_key or DEFAULT_KIRO_API_KEY,
        )

    openrouter_upstream: UpstreamTarget | None = None
    if args.openrouter_upstream:
        openrouter_parsed = urlparse(args.openrouter_upstream.rstrip("/"))
        if openrouter_parsed.scheme not in {"http", "https"} or not openrouter_parsed.netloc:
            raise SystemExit(f"Invalid openrouter upstream URL: {args.openrouter_upstream}")
        openrouter_api_key = args.openrouter_api_key or load_openrouter_key()
        if not openrouter_api_key:
            raise SystemExit(
                "Missing OpenRouter key for openrouter/* models. Set OPENROUTER_API_KEY "
                "or install ~/.config/mify/openrouter-credentials."
            )
        # OpenRouter base URL is https://openrouter.ai/api/v1 and inbound proxy
        # paths already carry the /v1 prefix (e.g. /v1/messages). Strip the
        # trailing /v1 so the forwarded path becomes /api/v1/messages instead
        # of /api/v1/v1/messages.
        openrouter_prefix = openrouter_parsed.path.rstrip("/")
        if openrouter_prefix.endswith("/v1"):
            openrouter_prefix = openrouter_prefix[: -len("/v1")]
        openrouter_upstream = UpstreamTarget(
            host=openrouter_parsed.hostname or "",
            port=openrouter_parsed.port or (443 if openrouter_parsed.scheme == "https" else 80),
            prefix=openrouter_prefix,
            scheme=openrouter_parsed.scheme,
            api_key=openrouter_api_key,
        )

    if not api_key and trae_upstream is None and kiro_upstream is None and openrouter_upstream is None:
        raise SystemExit("Missing Mify token. Set MIFY_API_KEY or install ~/.config/mify/credentials.")

    public_models = tuple(args.public_model or split_csv(os.environ.get("MIFY_DESKTOP_PROXY_PUBLIC_MODELS")))
    if not public_models:
        public_models = DEFAULT_PUBLIC_MODELS

    model_map = dict(DEFAULT_MODEL_MAP)
    for item in args.model_map or split_csv(os.environ.get("MIFY_DESKTOP_PROXY_MODEL_MAP")):
        if "=" not in item:
            raise SystemExit(f"Invalid --model-map {item!r}; expected external=upstream")
        external, upstream = [part.strip() for part in item.split("=", 1)]
        if not external or not upstream:
            raise SystemExit(f"Invalid --model-map {item!r}; expected external=upstream")
        model_map[external] = upstream

    return ProxyConfig(
        upstream_host=parsed.hostname or "",
        upstream_port=parsed.port or (443 if parsed.scheme == "https" else 80),
        upstream_prefix=parsed.path.rstrip("/"),
        upstream_scheme=parsed.scheme,
        upstream_base=args.upstream_base.rstrip("/"),
        public_models=public_models,
        model_map=model_map,
        api_key=api_key or "",
        verbose=args.verbose,
        trae_upstream=trae_upstream,
        kiro_upstream=kiro_upstream,
        openrouter_upstream=openrouter_upstream,
    )


def make_handler(config: ProxyConfig) -> type[Proxy]:
    class ConfiguredProxy(Proxy):
        pass

    ConfiguredProxy.config = config
    return ConfiguredProxy


def serve(args: argparse.Namespace) -> None:
    config = build_config(args)
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(config))

    if args.cert_file or args.key_file:
        if not args.cert_file or not args.key_file:
            raise SystemExit("--cert-file and --key-file must be provided together")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.cert_file, args.key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    else:
        scheme = "http"

    def shutdown(_signum: int, _frame: object) -> None:
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    print(
        f"mify-claude-desktop-proxy listening on {scheme}://{args.host}:{args.port} "
        f"({len(config.public_models)} public models, {len(config.model_map)} mapped)",
        file=sys.stderr,
        flush=True,
    )
    httpd.serve_forever()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default=os.environ.get("MIFY_DESKTOP_PROXY_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MIFY_DESKTOP_PROXY_PORT", "41414")))
    p.add_argument("--upstream-base", default=os.environ.get("MIFY_DESKTOP_PROXY_UPSTREAM", DEFAULT_UPSTREAM))
    p.add_argument("--trae-upstream", default=os.environ.get("MIFY_DESKTOP_PROXY_TRAE_UPSTREAM", DEFAULT_TRAE_UPSTREAM), help="Trae API proxy upstream for parko/* models")
    p.add_argument("--trae-api-key", default=os.environ.get("MIFY_DESKTOP_PROXY_TRAE_API_KEY", ""), help="API key for trae upstream (any value works)")
    p.add_argument("--kiro-upstream", default=os.environ.get("MIFY_DESKTOP_PROXY_KIRO_UPSTREAM", DEFAULT_KIRO_UPSTREAM), help="Kiro Gateway upstream for kiro/* models")
    p.add_argument("--kiro-api-key", default=os.environ.get("MIFY_DESKTOP_PROXY_KIRO_API_KEY", DEFAULT_KIRO_API_KEY), help="API key for Kiro Gateway upstream")
    p.add_argument("--openrouter-upstream", default=os.environ.get("MIFY_DESKTOP_PROXY_OPENROUTER_UPSTREAM", DEFAULT_OPENROUTER_UPSTREAM), help="OpenRouter upstream for openrouter/* models")
    p.add_argument("--openrouter-api-key", default=os.environ.get("MIFY_DESKTOP_PROXY_OPENROUTER_API_KEY", ""), help="API key for OpenRouter upstream; prefers ~/.config/mify/openrouter-credentials")
    p.add_argument("--public-model", action="append", help="Model exposed to Claude Desktop")
    p.add_argument("--model-map", action="append", help="Map external model to upstream, as external=upstream")
    p.add_argument("--api-key", help="Mify API key. Prefer ~/.config/mify/credentials.")
    p.add_argument("--cert-file")
    p.add_argument("--key-file")
    p.add_argument("--verbose", action="store_true")
    return p


def main(argv: Iterable[str] | None = None) -> int:
    serve(parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
