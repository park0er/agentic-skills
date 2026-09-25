#!/usr/bin/env python3
"""Local OpenAI-compatible model proxy for Mify + Gemini."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONFIG_PATH = Path.home() / ".config/xiaomi-gemini/config.json"
SIGNATURE_CACHE: dict[str, dict[str, dict[str, Any]]] = {}
SIGNATURE_CACHE_LOCK = threading.Lock()
FUNCTION_CALL_MISSING_SIGNATURE = "Function call is missing a thought_signature"

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


@dataclass(frozen=True)
class Upstream:
    name: str
    base_url: str
    api_key: str
    models: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    bind_host: str
    port: int
    proxy_api_key: str
    upstreams: tuple[Upstream, ...]
    default_upstream: str
    verbose: bool

    @property
    def upstream_by_name(self) -> dict[str, Upstream]:
        return {item.name: item for item in self.upstreams}

    @property
    def model_to_upstream(self) -> dict[str, Upstream]:
        index: dict[str, Upstream] = {}
        for upstream in self.upstreams:
            for model in upstream.models:
                index[model] = upstream
        return index


def load_config(path: Path, verbose: bool) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing config: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config {path}: {exc}") from exc

    upstreams = []
    for raw in data.get("upstreams", []):
        name = str(raw.get("name", "")).strip()
        base_url = str(raw.get("base_url", "")).rstrip("/")
        api_key = str(raw.get("api_key", "")).strip()
        models = tuple(str(item).strip() for item in raw.get("models", []) if str(item).strip())
        if not name or not base_url or not api_key or not models:
            raise SystemExit(f"Invalid upstream entry in {path}: name/base_url/api_key/models are required")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"Invalid upstream base_url for {name}: {base_url}")
        upstreams.append(Upstream(name=name, base_url=base_url, api_key=api_key, models=models))

    if not upstreams:
        raise SystemExit(f"No upstreams configured in {path}")

    default_upstream = str(data.get("default_upstream", upstreams[0].name)).strip()
    if default_upstream not in {item.name for item in upstreams}:
        raise SystemExit(f"default_upstream {default_upstream!r} is not in upstreams")

    return Config(
        bind_host=str(data.get("bind_host", "127.0.0.1")),
        port=int(data.get("port", 41415)),
        proxy_api_key=str(data.get("proxy_api_key", "")).strip(),
        upstreams=tuple(upstreams),
        default_upstream=default_upstream,
        verbose=verbose or bool(data.get("verbose", False)),
    )


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "xiaomi-gemini-openai-proxy/0.1"
    config: Config

    def log_message(self, fmt: str, *args: object) -> None:
        if self.config.verbose:
            super().log_message(fmt, *args)

    def _route_path(self) -> str:
        return urlparse(self.path).path.rstrip("/") or "/"

    def do_GET(self) -> None:  # noqa: N802
        if self._route_path() == "/healthz":
            self._send_json(200, self._health_payload())
            return
        if self._route_path() == "/v1/models":
            if not self._authorized():
                return
            self._send_json(200, self._models_payload())
            return
        self._send_json(404, {"error": {"message": "Unknown route", "type": "not_found"}})

    def do_POST(self) -> None:  # noqa: N802
        route_path = self._route_path()
        if route_path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Unknown route", "type": "not_found"}})
            return
        if not self._authorized():
            return

        body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": {"message": f"Invalid JSON: {exc}", "type": "invalid_request_error"}})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": {"message": "Request body must be a JSON object", "type": "invalid_request_error"}})
            return

        model = payload.get("model")
        upstream = self._resolve_upstream(model)
        if upstream is None:
            self._send_json(
                404,
                {
                    "error": {
                        "message": f"Model {model!r} is not configured in this proxy",
                        "type": "model_not_found",
                    }
                },
            )
            return

        if upstream.name == "gemini":
            self._restore_gemini_thought_signatures(payload)

        self._proxy_json(upstream, body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def _authorized(self) -> bool:
        expected = self.config.proxy_api_key
        if not expected:
            return True
        auth = self.headers.get("authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if token == expected:
            return True
        self._send_json(
            401,
            {
                "error": {
                    "message": "Invalid or missing local proxy API key",
                    "type": "authentication_error",
                }
            },
        )
        return False

    def _resolve_upstream(self, model: object) -> Upstream | None:
        if isinstance(model, str) and model in self.config.model_to_upstream:
            return self.config.model_to_upstream[model]
        if not isinstance(model, str) or not model:
            return None
        return self.config.upstream_by_name.get(self.config.default_upstream)

    def _cache_key(self, payload: dict[str, Any]) -> str:
        return str(payload.get("user") or self.client_address[0])

    def _tool_signature_keys(self, tool_call: dict[str, Any]) -> list[str]:
        keys = []
        tool_call_id = str(tool_call.get("id") or "")
        if tool_call_id:
            keys.append(f"id:{tool_call_id}")
        function = tool_call.get("function")
        if isinstance(function, dict):
            name = str(function.get("name") or "")
            if name:
                keys.append(f"name:{name}")
                keys.append(f"name:default_api:{name}")
        return keys

    def _restore_gemini_thought_signatures(self, payload: dict[str, Any]) -> None:
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return
        cache_key = self._cache_key(payload)
        with SIGNATURE_CACHE_LOCK:
            cached = SIGNATURE_CACHE.get(cache_key, {}).copy()
        if not cached:
            return
        fallback_signature = self._latest_cached_signature(cached)
        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                signature_data = None
                for key in self._tool_signature_keys(tool_call):
                    signature_data = cached.get(key)
                    if signature_data:
                        break
                if not signature_data and fallback_signature:
                    signature_data = fallback_signature
                if not signature_data:
                    continue
                google = tool_call.setdefault("extra_content", {}).setdefault("google", {})
                google.setdefault("thought_signature", signature_data["thought_signature"])

    def _remember_gemini_thought_signatures(self, payload: dict[str, Any], response_body: bytes) -> None:
        try:
            response = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._remember_gemini_stream_thought_signatures(payload, response_body)
            return
        if not isinstance(response, dict):
            return
        found: dict[str, dict[str, Any]] = {}
        for tool_call in self._extract_tool_calls_from_response(response):
            signature = self._thought_signature(tool_call)
            if isinstance(signature, str) and signature:
                for key in self._tool_signature_keys(tool_call):
                    found[key] = {"thought_signature": signature}
        if not found:
            return
        cache_key = self._cache_key(payload)
        with SIGNATURE_CACHE_LOCK:
            bucket = SIGNATURE_CACHE.setdefault(cache_key, {})
            bucket.update(found)
            latest = next(iter(found.values()), None)
            if latest:
                bucket["__latest__"] = latest
            if len(bucket) > 256:
                for key in list(bucket)[: len(bucket) - 256]:
                    bucket.pop(key, None)

    def _extract_tool_calls_from_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        tool_calls = []
        for choice in response.get("choices", []):
            if not isinstance(choice, dict):
                continue
            for container_name in ("message", "delta"):
                container = choice.get(container_name)
                if not isinstance(container, dict):
                    continue
                for tool_call in container.get("tool_calls", []) or []:
                    if isinstance(tool_call, dict):
                        tool_calls.append(tool_call)
        return tool_calls

    def _thought_signature(self, tool_call: dict[str, Any]) -> str | None:
        signature = tool_call.get("extra_content", {}).get("google", {}).get("thought_signature")
        return signature if isinstance(signature, str) and signature else None

    def _latest_cached_signature(self, cached: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        latest = cached.get("__latest__")
        if latest:
            return latest
        candidates = [value for key, value in cached.items() if key != "__latest__"]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _remember_gemini_stream_thought_signatures(self, payload: dict[str, Any], response_body: bytes) -> None:
        found: dict[str, dict[str, Any]] = {}
        for raw_line in response_body.decode("utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            event_data = line.removeprefix("data:").strip()
            if not event_data or event_data == "[DONE]":
                continue
            try:
                chunk = json.loads(event_data)
            except json.JSONDecodeError:
                continue
            if not isinstance(chunk, dict):
                continue
            for tool_call in self._extract_tool_calls_from_response(chunk):
                signature = self._thought_signature(tool_call)
                if isinstance(signature, str) and signature:
                    for key in self._tool_signature_keys(tool_call):
                        found[key] = {"thought_signature": signature}
        if not found:
            return
        cache_key = self._cache_key(payload)
        with SIGNATURE_CACHE_LOCK:
            bucket = SIGNATURE_CACHE.setdefault(cache_key, {})
            bucket.update(found)
            latest = next(iter(found.values()), None)
            if latest:
                bucket["__latest__"] = latest
            if len(bucket) > 256:
                for key in list(bucket)[: len(bucket) - 256]:
                    bucket.pop(key, None)

    def _proxy_json(self, upstream: Upstream, body: bytes) -> None:
        request_meta = {"path": self.path, "upstream": upstream.name}
        try:
            target_url = f"{upstream.base_url.rstrip('/')}/chat/completions"
            with tempfile.NamedTemporaryFile() as output_file:
                result = subprocess.run(
                    [
                        "curl",
                        "-sS",
                        "--max-time",
                        "300",
                        "-o",
                        output_file.name,
                        "-w",
                        "%{http_code}",
                        target_url,
                        "-H",
                        f"Authorization: Bearer {upstream.api_key}",
                        "-H",
                        "Content-Type: application/json",
                        "-H",
                        f"Accept: {self.headers.get('accept', 'application/json')}",
                        "--data-binary",
                        "@-",
                    ],
                    input=body,
                    capture_output=True,
                    timeout=310,
                )
                response_body = output_file.read()
            status = int(result.stdout.decode("utf-8", errors="replace")[-3:] or "502") if result.returncode == 0 else 502
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                self._log_event("proxy_error", {**request_meta, "message": stderr or f"curl exited {result.returncode}"})
                self._send_json(502, {"error": {"message": stderr or f"curl exited {result.returncode}", "type": "upstream_error"}})
                return
            if status >= 400:
                self._log_event(
                    "upstream_error",
                    {**request_meta, "status": status, "error_preview": response_body[:2000].decode("utf-8", errors="replace")},
                )
                if upstream.name == "gemini" and FUNCTION_CALL_MISSING_SIGNATURE in response_body.decode("utf-8", errors="replace"):
                    self._log_event(
                        "gemini_missing_thought_signature",
                        {**request_meta, "cache_key": self._cache_key(json.loads(body.decode("utf-8"))) if body else ""},
                    )
            elif self.config.verbose:
                self._log_event("upstream_ok", {**request_meta, "status": status})
            if upstream.name == "gemini" and 200 <= status < 300:
                try:
                    request_payload = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    request_payload = {}
                if isinstance(request_payload, dict):
                    self._remember_gemini_thought_signatures(request_payload, response_body)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(response_body)
            self.wfile.flush()
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._log_event("proxy_error", {**request_meta, "message": str(exc)})
            self._send_json(502, {"error": {"message": str(exc), "type": "upstream_error"}})

    def _health_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "base_url": f"http://{self.config.bind_host}:{self.config.port}/v1",
            "upstreams": [
                {"name": item.name, "base_url": item.base_url, "models": list(item.models)}
                for item in self.config.upstreams
            ],
        }

    def _models_payload(self) -> dict[str, Any]:
        data = []
        for upstream in self.config.upstreams:
            for model in upstream.models:
                data.append({"id": model, "object": "model", "created": 0, "owned_by": upstream.name})
        return {"object": "list", "data": data}

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _log_event(self, event: str, payload: dict[str, object]) -> None:
        print(
            json.dumps(
                {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **payload},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
            flush=True,
        )


def make_handler(config: Config) -> type[ProxyHandler]:
    class ConfiguredProxy(ProxyHandler):
        pass

    ConfiguredProxy.config = config
    return ConfiguredProxy


def serve(config: Config) -> None:
    httpd = ThreadingHTTPServer((config.bind_host, config.port), make_handler(config))

    def shutdown(_signum: int, _frame: object) -> None:
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    print(
        f"xiaomi-gemini proxy listening on http://{config.bind_host}:{config.port}/v1 "
        f"({sum(len(item.models) for item in config.upstreams)} models)",
        file=sys.stderr,
        flush=True,
    )
    httpd.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.environ.get("XIAOMI_GEMINI_CONFIG", str(CONFIG_PATH)))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    serve(load_config(Path(args.config).expanduser(), args.verbose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
