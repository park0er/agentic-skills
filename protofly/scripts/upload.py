#!/usr/bin/env python3
"""Upload an HTML file to proto-fly via mcporter.

Why a wrapper: `mcporter call protofly.create_resource` accepts `key:value`
flags, but a 10 MB base64 string blows up shell argument parsing — long
runs of `+`/`/`/`=` get mangled and the server replies "file_content is
required". Routing the call through `--args <json>` is the only reliable
path for binary-ish payloads, and base64-encoding the file in Python keeps
us away from `base64`/`xxd` differences across macOS/Linux.

Usage:
    upload.py <html-path> [--description TEXT] [--resource-id ID]
              [--private | --draft] [--json]

Default behaviour (no visibility flag):
    publish + set_visibility public — anyone inside the Xiaomi network with
    the `view` link can open it. Optimised for the dominant use case
    "发给同事看一眼". Flip with `--private` for sensitive content; use
    `--draft` to skip publishing entirely (owner-only preview).

Visibility flags (mutually exclusive):
    --private   publish the new version, then `set_visibility private`
                (only authorised users in the protofly web console can view)
    --draft     do NOT publish; resource stays as a draft, owner-only
                preview link
    (none)      publish + `set_visibility public` — the new default

Legacy flags (kept for backwards compat, no-op since they match the new
default):
    --public, --publish
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024  # proto-fly hard limit per docs


def die(msg: str, code: int = 1) -> None:
    print(f"upload: {msg}", file=sys.stderr)
    sys.exit(code)


def mcp_call(tool: str, payload: dict) -> dict:
    """Call protofly.<tool> with --args JSON, return parsed response."""
    proc = subprocess.run(
        ["mcporter", "call", f"protofly.{tool}", "--args", json.dumps(payload), "--output", "json"],
        check=False, text=True, capture_output=True,
    )
    if proc.returncode != 0:
        die(f"protofly.{tool} failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        die(f"protofly.{tool} returned non-JSON:\n{proc.stdout[:500]}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Upload HTML to proto-fly via mcporter (default: publish + public).",
    )
    ap.add_argument("path", help="path to a local .html file")
    ap.add_argument("--description", default=None, help="resource description (only used on first create)")
    ap.add_argument("--resource-id", default=None, help="append a new version to an existing resource")
    ap.add_argument("--json", dest="json_out", action="store_true", help="emit merged JSON instead of human text")

    visibility = ap.add_mutually_exclusive_group()
    visibility.add_argument(
        "--private", dest="visibility_private", action="store_true",
        help="publish but set visibility=private (authorised users only)",
    )
    visibility.add_argument(
        "--draft", dest="visibility_draft", action="store_true",
        help="do NOT publish; resource stays draft, owner-only preview link",
    )
    # Legacy aliases — kept so older callers/docs don't break. They map to
    # the new default (publish + public) and silently no-op.
    visibility.add_argument(
        "--public", dest="legacy_public", action="store_true",
        help="(legacy, default) publish + set_visibility public",
    )
    visibility.add_argument(
        "--publish", dest="legacy_publish", action="store_true",
        help="(legacy alias of default) publish + set_visibility public",
    )

    args = ap.parse_args()

    src = Path(args.path).expanduser().resolve()
    if not src.is_file():
        die(f"not a file: {src}")
    if src.suffix.lower() != ".html":
        die(f"expected .html, got {src.suffix or '<no extension>'}")
    raw = src.read_bytes()
    if len(raw) > MAX_BYTES:
        die(f"file is {len(raw)/1024/1024:.1f} MB, proto-fly limit is 10 MB")

    payload: dict[str, object] = {
        "filename": src.name,
        "file_content": base64.b64encode(raw).decode("ascii"),
    }
    if args.resource_id:
        payload["resource_id"] = args.resource_id
    if args.description:
        payload["description"] = args.description

    create = mcp_call("create_resource", payload)
    rid = create.get("resource_id") or args.resource_id
    if not rid:
        die(f"create_resource returned no resource_id: {create}")

    merged: dict[str, object] = {"create": create}

    # Resolve target visibility. Default = public. --private flips to
    # private. --draft skips publish entirely. Legacy --public/--publish are
    # no-op aliases for the default.
    if args.visibility_draft:
        target_visibility = None  # don't publish
    elif args.visibility_private:
        target_visibility = "private"
    else:
        target_visibility = "public"

    if target_visibility is not None:
        pub_payload: dict[str, object] = {"resource_id": rid}
        if "version" in create:
            pub_payload["version"] = create["version"]
        merged["publish"] = mcp_call("publish_resource", pub_payload)

        merged["visibility"] = mcp_call(
            "set_visibility",
            {"resource_id": rid, "visibility": target_visibility},
        )

    if args.json_out:
        json.dump(merged, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    # Human-friendly summary.
    version = create.get("version", "?")
    print(f"resource_id : {rid}")
    print(f"version     : {version}")
    print(f"size        : {len(raw)/1024:.1f} KB")
    if "publish" in merged:
        publish_block = merged["publish"]
        assert isinstance(publish_block, dict)
        view_url = publish_block.get("published_url", f"https://protofly.v.mitvos.com/view/{rid}")
        print(f"published   : v{publish_block.get('published_version', version)}")
        print(f"view url    : {view_url}")
    else:
        preview = create.get("preview_url", f"https://protofly.v.mitvos.com/preview/{rid}")
        print(f"preview url : {preview}  (draft, owner-only)")
    if "visibility" in merged:
        vis_block = merged["visibility"]
        assert isinstance(vis_block, dict)
        vis = vis_block.get("visibility", "?")
        if vis == "public":
            print(f"visibility  : public  (anyone in Xiaomi network with the link can view)")
        elif vis == "private":
            print(f"visibility  : private  (authorised users only — manage in protofly web console)")
        else:
            print(f"visibility  : {vis}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
