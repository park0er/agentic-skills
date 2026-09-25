#!/usr/bin/env python3
"""Load machine-local Rollica QA/dev memory. No secrets are printed."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


SECRET_KEYS = {
    "DATABASE_URL",
    "JWT_SECRET",
    "POSTGRES_PASSWORD",
    "MULTICA_LARK_SECRET_KEY",
    "GOOGLE_CLIENT_SECRET",
    "token",
}


def config_candidates() -> list[Path]:
    homes = []
    if os.environ.get("MULTICA_CONFIG_HOME"):
        homes.append(Path(os.environ["MULTICA_CONFIG_HOME"]).expanduser())
    homes.append(Path.home() / ".rollica")
    homes.append(Path.home() / ".multica")
    seen: set[Path] = set()
    out: list[Path] = []
    for home in homes:
        path = home / "local-dev.yaml"
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out


def resolve_config_path() -> Path | None:
    for path in config_candidates():
        if path.is_file():
            return path
    return None


def expand(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expanduser(os.path.expandvars(value))
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v) for v in value]
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the restricted YAML subset used by local-dev.yaml."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    last_key: str | None = None

    def current_container(indent: int) -> Any:
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        return stack[-1][1]

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        container = current_container(indent)
        if line.startswith("- "):
            item = parse_scalar(line[2:].strip())
            if isinstance(container, dict) and not container and len(stack) > 1:
                parent = stack[-2][1]
                if isinstance(parent, dict) and last_key in parent and parent[last_key] is container:
                    new_list: list[Any] = []
                    parent[last_key] = new_list
                    stack[-1] = (stack[-1][0], new_list)
                    container = new_list
            if not isinstance(container, list):
                if last_key is None or not isinstance(stack[-1][1], dict):
                    raise ValueError(f"list item without a key: {raw}")
                new_list = []
                stack[-1][1][last_key] = new_list
                stack.append((indent, new_list))
                container = new_list
            container.append(item)
            continue
        if ":" not in line:
            raise ValueError(f"cannot parse: {raw}")
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if not isinstance(container, dict):
            raise ValueError(f"map entry under a list: {raw}")
        if rest == "":
            nxt: dict[str, Any] = {}
            container[key] = nxt
            stack.append((indent, nxt))
            last_key = key
            continue
        container[key] = parse_scalar(rest)
        last_key = key
    return root


def parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value
    return out


def load_config() -> tuple[Path, dict[str, Any]]:
    path = resolve_config_path()
    if path is None:
        raise FileNotFoundError(
            "no local-dev.yaml found; expected one of: "
            + ", ".join(str(p) for p in config_candidates())
        )
    data = expand(parse_simple_yaml(path.read_text()))
    return path, data


def redact(key: str, value: Any) -> Any:
    if key in SECRET_KEYS:
        return "***"
    if isinstance(value, dict):
        return {k: redact(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(key, v) for v in value]
    return value


def doctor() -> int:
    try:
        path, data = load_config()
    except FileNotFoundError as err:
        print(f"missing: {err}", file=sys.stderr)
        print("copy templates/local-dev.yaml to ~/.rollica/local-dev.yaml and fill it")
        return 2
    print(f"config: {path}")
    print(f"kind: {data.get('kind', 'unknown')}")
    env_file = data.get("env_file")
    if env_file:
        env_path = Path(str(env_file))
        print(f"env_file: {env_path} ({'ok' if env_path.is_file() else 'MISSING'})")
        env = load_env_file(env_path)
        code_key = ((data.get("account") or {}).get("verification_code_env")
                    or "MULTICA_DEV_VERIFICATION_CODE")
        if code_key in env:
            print(f"{code_key}: set")
        else:
            print(f"{code_key}: MISSING")
    for section in ("checkouts", "desktop", "daemon", "server", "postgres", "account", "production"):
        if section in data:
            print(f"{section}: {redact(section, data[section])}")
    return 0


def get_value(dotted: str) -> int:
    _, data = load_config()
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            print(f"missing key: {dotted}", file=sys.stderr)
            return 1
        cur = cur[part]
    if isinstance(cur, (dict, list)):
        print(redact(dotted.split(".")[-1], cur))
    else:
        print(cur)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "path", "get"])
    parser.add_argument("key", nargs="?")
    args = parser.parse_args()
    if args.command == "path":
        path = resolve_config_path()
        if path is None:
            print("missing", file=sys.stderr)
            return 2
        print(path)
        return 0
    if args.command == "get":
        if not args.key:
            print("get needs a dotted key", file=sys.stderr)
            return 2
        return get_value(args.key)
    return doctor()


if __name__ == "__main__":
    sys.exit(main())
