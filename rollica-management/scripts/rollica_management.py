#!/usr/bin/env python3
"""Deterministic wrapper for Rollica CLI as the signed-in human.

Resolves an accessible Workspace to its canonical UUID, loads a human mul_
PAT from the matching Desktop or CLI profile, and invokes the matching CLI
from a neutral directory so stale daemon task markers cannot change auth
semantics. Credentials are never printed.

Two clouds:
- production: company Rollica.app + desktop-rollica.ad.miui.com
- tokyo: Rollica Tokyo.app if present, else ~/.rollica-cli/bin/multica,
  plus a profile whose server_url points at the Tokyo private server
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


PRODUCTION_CLI_PATH = Path(
    "/Applications/Rollica.app/Contents/Resources/"
    "app.asar.unpacked/resources/bin/multica"
)
PRODUCTION_CONFIG_HOME = Path.home() / ".rollica"
PRODUCTION_PROFILE = "desktop-rollica.ad.miui.com"

TOKYO_DESKTOP_CLI = Path(
    "/Applications/Rollica Tokyo.app/Contents/Resources/"
    "app.asar.unpacked/resources/bin/multica"
)
TOKYO_CLI_FALLBACK = Path.home() / ".rollica-cli/bin/multica"
TOKYO_DESKTOP_CONFIG_HOME = Path.home() / ".rollica-tokyo"
TOKYO_CLI_CONFIG_HOME = Path.home() / ".multica"
TOKYO_PREFERRED_PROFILES = ("a1",)
TOKYO_HOST_MARKERS = (
    "141.147.189.28",
    "10.0.0.244",
)
TOKYO_QUERY_RE = re.compile(
    r"^(pko|tokyo|tokyo-private|东京|东京服|东京私服)$",
    re.IGNORECASE,
)
PRODUCTION_QUERY_RE = re.compile(r"^(parko|miads|miadsagent|production|正式|公司)$", re.IGNORECASE)

NEUTRAL_CWD = Path("/private/tmp")
ISSUE_REF_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*)-\d+\b")
HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
TASK_ENV_KEYS = (
    "MULTICA_AGENT_ID",
    "MULTICA_TASK_ID",
    "MULTICA_DAEMON_PORT",
    "MULTICA_LAUNCHED_BY",
    "MULTICA_TASK_SLOT",
    "MULTICA_TASK_CONFIG_ROOT",
)


class RollicaError(RuntimeError):
    """Expected configuration, resolution, or CLI error."""


@dataclass(frozen=True)
class Context:
    env_name: str
    cli_path: Path
    cli_source: str
    install_shape: str
    config_home: Path
    profile: str
    profile_path: Path
    server_url: str
    app_url: str
    token: str


def _executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _read_profile(profile_path: Path) -> dict[str, Any]:
    try:
        body = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RollicaError(f"cannot read Rollica profile {profile_path}: {exc}") from exc
    if not isinstance(body, dict):
        raise RollicaError(f"Rollica profile is not an object: {profile_path}")
    return body


def _human_token(profile_path: Path, body: dict[str, Any]) -> str:
    token = str(body.get("token", "")).strip()
    if not token.startswith("mul_"):
        raise RollicaError(
            f"{profile_path} does not contain a signed-in human mul_ PAT"
        )
    return token


def tokyo_host_markers() -> tuple[str, ...]:
    extra = os.environ.get("ROLLICA_TOKYO_SERVER", "").strip()
    if extra:
        return TOKYO_HOST_MARKERS + (extra,)
    return TOKYO_HOST_MARKERS


def is_tokyo_server_url(url: str) -> bool:
    folded = url.casefold()
    return any(marker.casefold() in folded for marker in tokyo_host_markers())


def infer_env_name(
    explicit: str | None,
    *,
    workspace_query: str = "",
    cli_args: Sequence[str] = (),
) -> str:
    if explicit in {"production", "tokyo"}:
        return explicit
    env_var = os.environ.get("ROLLICA_ENV", "").strip().casefold()
    if env_var in {"production", "tokyo"}:
        return env_var
    query = (workspace_query or "").strip()
    if TOKYO_QUERY_RE.fullmatch(query):
        return "tokyo"
    if PRODUCTION_QUERY_RE.fullmatch(query):
        return "production"
    prefixes = {
        match.group(1).upper()
        for text in (query, *cli_args)
        for match in ISSUE_REF_RE.finditer(text)
    }
    if prefixes == {"PKO"}:
        return "tokyo"
    if "PKO" in prefixes and prefixes - {"PKO"}:
        raise RollicaError(
            "command mixes Tokyo PKO-* identifiers with other Issue prefixes; "
            "pass --env tokyo or --env production explicitly"
        )
    return "production"


def _iter_profile_files(config_home: Path) -> list[tuple[str, Path]]:
    profiles_dir = config_home / "profiles"
    if not profiles_dir.is_dir():
        return []
    found: list[tuple[str, Path]] = []
    for child in sorted(profiles_dir.iterdir()):
        cfg = child / "config.json"
        if child.is_dir() and cfg.is_file():
            found.append((child.name, cfg))
    return found


def _tokyo_cli_candidates() -> list[tuple[str, Path]]:
    return [
        ("tokyo-desktop", TOKYO_DESKTOP_CLI),
        ("rollica-cli", TOKYO_CLI_FALLBACK),
    ]


def resolve_tokyo_cli() -> tuple[Path, str, str]:
    override = os.environ.get("ROLLICA_CLI_PATH", "").strip()
    if override:
        path = Path(override).expanduser()
        if not _executable(path):
            raise RollicaError(f"ROLLICA_CLI_PATH is not an executable CLI: {path}")
        return path, "override", "override"

    desktop_ok = _executable(TOKYO_DESKTOP_CLI)
    cli_ok = _executable(TOKYO_CLI_FALLBACK)
    if desktop_ok:
        shape = "tokyo-desktop"
        if cli_ok:
            shape = "tokyo-desktop+cli"
        return TOKYO_DESKTOP_CLI, "tokyo-desktop", shape
    if cli_ok:
        shape = "cli-only"
        if Path("/Applications/Rollica Tokyo.app").exists() and not desktop_ok:
            shape = "cli-only (Tokyo.app present but bundled CLI missing)"
        return TOKYO_CLI_FALLBACK, "rollica-cli", shape

    hints = [
        "Tokyo Desktop: install /Applications/Rollica Tokyo.app and sign in once",
        "CLI-only: install ~/.rollica-cli/bin/multica, then "
        "`multica setup self-host --server-url <tokyo>` and `multica login --token`",
    ]
    if Path("/Applications/Rollica Tokyo.app").exists():
        hints.insert(
            0,
            "Rollica Tokyo.app is installed but has no unpacked CLI at "
            f"{TOKYO_DESKTOP_CLI}",
        )
    raise RollicaError(
        "no Tokyo Rollica CLI found. "
        + " ".join(hints)
        + ". Do not use /Applications/Rollica.app to talk to Tokyo."
    )


def resolve_tokyo_profile() -> tuple[Path, str, Path, dict[str, Any]]:
    override_home = os.environ.get("ROLLICA_CONFIG_HOME", "").strip()
    override_profile = os.environ.get("ROLLICA_PROFILE", "").strip()
    if override_home:
        home = Path(override_home).expanduser()
        profile = override_profile or "a1"
        path = home / "profiles" / profile / "config.json"
        if not path.is_file():
            raise RollicaError(f"Tokyo profile is missing: {path}")
        return home, profile, path, _read_profile(path)

    search_homes = [
        TOKYO_DESKTOP_CONFIG_HOME,
        TOKYO_CLI_CONFIG_HOME,
        Path.home() / ".rollica",
    ]
    matches: list[tuple[int, Path, str, Path, dict[str, Any]]] = []
    for home in search_homes:
        for name, path in _iter_profile_files(home):
            body = _read_profile(path)
            server = str(body.get("server_url", "")).strip()
            token = str(body.get("token", "")).strip()
            if not is_tokyo_server_url(server) or not token.startswith("mul_"):
                continue
            rank = 2
            if home == TOKYO_DESKTOP_CONFIG_HOME:
                rank = 0
            elif name in TOKYO_PREFERRED_PROFILES:
                rank = 1
            matches.append((rank, home, name, path, body))

    if override_profile:
        named = [row for row in matches if row[2] == override_profile]
        if named:
            matches = named
        else:
            raise RollicaError(
                f'ROLLICA_PROFILE="{override_profile}" is not a signed-in Tokyo profile'
            )

    if not matches:
        raise RollicaError(
            "no signed-in Tokyo profile found. "
            "Desktop: open Rollica Tokyo.app and sign in (config lives in "
            f"{TOKYO_DESKTOP_CONFIG_HOME}). "
            "CLI-only: "
            f"`MULTICA_CONFIG_HOME={TOKYO_CLI_CONFIG_HOME} "
            f"{TOKYO_CLI_FALLBACK} --profile a1 login --token mul_...` "
            "pointing at the Tokyo server_url."
        )
    matches.sort(key=lambda row: (row[0], row[2]))
    _rank, home, name, path, body = matches[0]
    return home, name, path, body


def load_production_context() -> Context:
    config_home = Path(
        os.environ.get("ROLLICA_CONFIG_HOME", str(PRODUCTION_CONFIG_HOME))
    ).expanduser()
    profile = os.environ.get("ROLLICA_PROFILE", PRODUCTION_PROFILE).strip()
    if not profile:
        raise RollicaError("ROLLICA_PROFILE cannot be empty")
    profile_path = config_home / "profiles" / profile / "config.json"
    if not profile_path.is_file():
        raise RollicaError(
            f"Rollica profile is missing: {profile_path}. "
            "Open and sign in to the production Rollica.app first."
        )
    body = _read_profile(profile_path)
    server_url = str(body.get("server_url", "")).strip().rstrip("/")
    if not server_url:
        raise RollicaError(f"server_url is missing from {profile_path}")
    token = _human_token(profile_path, body)
    cli_path = Path(
        os.environ.get("ROLLICA_CLI_PATH", str(PRODUCTION_CLI_PATH))
    ).expanduser()
    if not _executable(cli_path):
        raise RollicaError(
            f"production Rollica CLI is unavailable: {cli_path}. "
            "Install or open /Applications/Rollica.app first."
        )
    app_url = str(body.get("app_url", "")).strip().rstrip("/") or server_url
    return Context(
        env_name="production",
        cli_path=cli_path,
        cli_source="rollica-app",
        install_shape="production-desktop",
        config_home=config_home,
        profile=profile,
        profile_path=profile_path,
        server_url=server_url,
        app_url=app_url,
        token=token,
    )


def load_tokyo_context() -> Context:
    cli_path, cli_source, install_shape = resolve_tokyo_cli()
    config_home, profile, profile_path, body = resolve_tokyo_profile()
    server_url = str(body.get("server_url", "")).strip().rstrip("/")
    if not server_url:
        raise RollicaError(f"server_url is missing from {profile_path}")
    if not is_tokyo_server_url(server_url):
        raise RollicaError(
            f"{profile_path} server_url is not a Tokyo private server: {server_url}"
        )
    token = _human_token(profile_path, body)
    app_url = str(body.get("app_url", "")).strip().rstrip("/") or server_url
    return Context(
        env_name="tokyo",
        cli_path=cli_path,
        cli_source=cli_source,
        install_shape=install_shape,
        config_home=config_home,
        profile=profile,
        profile_path=profile_path,
        server_url=server_url,
        app_url=app_url,
        token=token,
    )


def load_context(env_name: str) -> Context:
    if env_name == "tokyo":
        return load_tokyo_context()
    if env_name == "production":
        return load_production_context()
    raise RollicaError(f"unknown env {env_name}")


def cli_env(ctx: Context, workspace: dict[str, Any] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    for key in TASK_ENV_KEYS:
        env.pop(key, None)
    env.update(
        {
            "MULTICA_CONFIG_HOME": str(ctx.config_home),
            "MULTICA_PROFILE": ctx.profile,
            "MULTICA_SERVER_URL": ctx.server_url,
            "MULTICA_APP_URL": ctx.app_url,
            "MULTICA_TOKEN": ctx.token,
            "MULTICA_TERMINAL_HANDOFF": "1",
            "PATH": f"{ctx.cli_path.parent}:{env.get('PATH', '')}",
        }
    )
    if workspace is None:
        env.pop("MULTICA_WORKSPACE_ID", None)
        env.pop("ROLLICA_WORKSPACE_ID", None)
        env.pop("ROLLICA_WORKSPACE_NAME", None)
        env.pop("ROLLICA_WORKSPACE_SLUG", None)
    else:
        env.update(
            {
                "MULTICA_WORKSPACE_ID": str(workspace["id"]),
                "ROLLICA_WORKSPACE_ID": str(workspace["id"]),
                "ROLLICA_WORKSPACE_NAME": str(workspace["name"]),
                "ROLLICA_WORKSPACE_SLUG": str(workspace["slug"]),
            }
        )
    return env


def invoke_cli(
    ctx: Context,
    args: Sequence[str],
    *,
    workspace: dict[str, Any] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(ctx.cli_path), *args],
        cwd=NEUTRAL_CWD,
        env=cli_env(ctx, workspace),
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if capture and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RollicaError(
            f"Rollica CLI failed ({result.returncode})"
            + (f": {detail}" if detail else "")
        )
    return result


def invoke_json(
    ctx: Context,
    args: Sequence[str],
    *,
    workspace: dict[str, Any] | None = None,
) -> Any:
    result = invoke_cli(ctx, args, workspace=workspace, capture=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RollicaError(
            f"Rollica CLI returned invalid JSON for {' '.join(args)}"
        ) from exc


def accessible_workspaces(ctx: Context) -> list[dict[str, Any]]:
    rows = invoke_json(ctx, ["workspace", "list", "--output", "json"])
    if not isinstance(rows, list):
        raise RollicaError("workspace list returned an unexpected response")

    workspaces: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        workspace_id = str(row.get("id", "")).strip()
        if not workspace_id:
            continue
        details = invoke_json(
            ctx,
            ["workspace", "get", workspace_id, "--output", "json"],
        )
        if not isinstance(details, dict):
            raise RollicaError(f"workspace get {workspace_id} returned invalid data")
        workspaces.append(
            {
                "id": workspace_id,
                "name": str(details.get("name", row.get("name", ""))).strip(),
                "slug": str(details.get("slug", row.get("slug", ""))).strip(),
                "issue_prefix": str(details.get("issue_prefix", "")).strip().upper(),
            }
        )
    return workspaces


def candidate_text(workspace: dict[str, Any]) -> str:
    prefix = workspace.get("issue_prefix") or "—"
    return (
        f"{workspace['name']} "
        f"(slug={workspace['slug']}, issue_prefix={prefix}, id={workspace['id']})"
    )


def unique_or_error(
    query: str,
    matches: list[dict[str, Any]],
    *,
    kind: str,
) -> dict[str, Any]:
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = "\n".join(f"- {candidate_text(row)}" for row in matches)
        raise RollicaError(
            f'ambiguous Workspace {kind} "{query}". Candidates:\n{options}'
        )
    raise RollicaError(f'no Workspace matched {kind} "{query}"')


def resolve_workspace(
    workspaces: list[dict[str, Any]],
    query: str,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        if len(workspaces) == 1:
            return workspaces[0]
        options = "\n".join(f"- {candidate_text(row)}" for row in workspaces)
        raise RollicaError(
            "Workspace is required because more than one is accessible. "
            f"Choose one by name, slug, ID/prefix, keyword, or Issue prefix:\n{options}"
        )

    folded = query.casefold()
    issue_match = ISSUE_REF_RE.search(query)
    issue_prefix = issue_match.group(1).upper() if issue_match else query.upper()

    exact_id = [row for row in workspaces if row["id"].casefold() == folded]
    if exact_id:
        return exact_id[0]

    if len(query) >= 4 and HEX_RE.fullmatch(query):
        id_prefix = [
            row for row in workspaces if row["id"].casefold().startswith(folded)
        ]
        if id_prefix:
            return unique_or_error(query, id_prefix, kind="ID prefix")

    exact_slug = [row for row in workspaces if row["slug"].casefold() == folded]
    if exact_slug:
        return unique_or_error(query, exact_slug, kind="slug")

    exact_name = [row for row in workspaces if row["name"].casefold() == folded]
    if exact_name:
        return unique_or_error(query, exact_name, kind="name")

    exact_issue_prefix = [
        row for row in workspaces if row["issue_prefix"] == issue_prefix
    ]
    if exact_issue_prefix:
        return unique_or_error(query, exact_issue_prefix, kind="Issue prefix")

    keyword = [
        row
        for row in workspaces
        if folded in row["name"].casefold() or folded in row["slug"].casefold()
    ]
    if keyword:
        return unique_or_error(query, keyword, kind="keyword")

    options = "\n".join(f"- {candidate_text(row)}" for row in workspaces)
    raise RollicaError(
        f'no accessible Workspace matched "{query}". Available Workspaces:\n{options}'
    )


def infer_workspace_query(args: Sequence[str]) -> str:
    prefixes = {
        match.group(1).upper()
        for arg in args
        for match in ISSUE_REF_RE.finditer(arg)
    }
    if len(prefixes) == 1:
        return next(iter(prefixes))
    if len(prefixes) > 1:
        raise RollicaError(
            "command contains Issue identifiers from multiple Workspace prefixes: "
            + ", ".join(sorted(prefixes))
        )
    return os.environ.get("ROLLICA_WORKSPACE", "").strip()


def print_json(value: Any) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def command_workspaces(ctx: Context, as_json: bool) -> int:
    rows = accessible_workspaces(ctx)
    if as_json:
        print_json(rows)
        return 0
    for row in rows:
        print(candidate_text(row))
    return 0


def command_resolve(ctx: Context, query: str, output: str) -> int:
    workspace = resolve_workspace(accessible_workspaces(ctx), query)
    if output == "id":
        print(workspace["id"])
    else:
        print_json(workspace)
    return 0


def command_doctor(ctx: Context) -> int:
    rows = accessible_workspaces(ctx)
    print_json(
        {
            "ok": True,
            "env": ctx.env_name,
            "cli_path": str(ctx.cli_path),
            "cli_source": ctx.cli_source,
            "install_shape": ctx.install_shape,
            "profile": ctx.profile,
            "config_home": str(ctx.config_home),
            "server_url": ctx.server_url,
            "token_source": str(ctx.profile_path),
            "token_type": "human mul_ PAT",
            "workspace_count": len(rows),
        }
    )
    return 0


def command_run(
    ctx: Context,
    workspace_query: str,
    cli_args: list[str],
    dry_run: bool,
) -> int:
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    if not cli_args:
        raise RollicaError("pass a multica command after --")

    query = workspace_query.strip() or infer_workspace_query(cli_args)
    workspace = resolve_workspace(accessible_workspaces(ctx), query)
    if dry_run:
        print_json(
            {
                "env": ctx.env_name,
                "cli_path": str(ctx.cli_path),
                "cli_source": ctx.cli_source,
                "install_shape": ctx.install_shape,
                "profile": ctx.profile,
                "server_url": ctx.server_url,
                "token_source": str(ctx.profile_path),
                "token": "<redacted>",
                "workspace": workspace,
                "cwd": str(NEUTRAL_CWD),
                "args": cli_args,
            }
        )
        return 0
    return invoke_cli(ctx, cli_args, workspace=workspace).returncode


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Operate Rollica resources with the signed-in user profile. "
            "Default env is company production; pass --env tokyo for the private server."
        )
    )
    root.add_argument(
        "--env",
        choices=("production", "tokyo"),
        default=None,
        help="Cloud to use. Default: production, or tokyo when the query/Issue prefix is PKO/东京.",
    )
    subcommands = root.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser(
        "doctor", help="Verify CLI, profile, auth, and Workspace discovery"
    )
    doctor.set_defaults(handler=lambda args, ctx: command_doctor(ctx))

    workspaces = subcommands.add_parser(
        "workspaces", help="List accessible Workspaces on the selected env"
    )
    workspaces.add_argument(
        "--output", choices=("table", "json"), default="table"
    )
    workspaces.set_defaults(
        handler=lambda args, ctx: command_workspaces(ctx, args.output == "json")
    )

    resolve = subcommands.add_parser(
        "resolve-workspace",
        help="Resolve name, slug, ID/prefix, keyword, or Issue prefix to a Workspace",
    )
    resolve.add_argument("query")
    resolve.add_argument("--output", choices=("json", "id"), default="json")
    resolve.set_defaults(
        handler=lambda args, ctx: command_resolve(ctx, args.query, args.output)
    )

    run = subcommands.add_parser(
        "run", help="Resolve a Workspace and invoke the matching multica CLI"
    )
    run.add_argument(
        "--workspace",
        default="",
        help="Workspace name, slug, ID/prefix, keyword, or Issue prefix",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print redacted resolved context without invoking the business command",
    )
    run.add_argument(
        "cli_args",
        nargs=argparse.REMAINDER,
        help="multica command and arguments, normally after --",
    )
    run.set_defaults(
        handler=lambda args, ctx: command_run(
            ctx, args.workspace, args.cli_args, args.dry_run
        )
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        workspace_query = getattr(args, "workspace", "") or (
            args.query if args.command == "resolve-workspace" else ""
        )
        cli_args = getattr(args, "cli_args", [])
        env_name = infer_env_name(
            args.env,
            workspace_query=workspace_query,
            cli_args=cli_args,
        )
        context = load_context(env_name)
        return int(args.handler(args, context))
    except RollicaError as exc:
        print(f"rollica-management: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
