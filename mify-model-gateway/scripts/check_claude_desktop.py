#!/usr/bin/env python3
"""Detect (and optionally install) Anthropic's Claude Desktop app on macOS.

This is the pre-flight check for the Cowork 3P provisioning flow — before we
can call `install_cowork_config.py` to write the Mify gateway config into the
Claude Desktop plist, the app itself must exist. Many Mify users haven't
installed Claude Desktop yet (the download page is the Anthropic site, not
Mify's internal app catalog).

Modes:
  (default)       Detect and print status — human readable.
  --json          Same detection, but machine-readable output.
  --install-brew  Run `brew install --cask claude` if Homebrew is available.
  --open-download Open https://claude.com/download in the default browser.
                  Use when brew is missing or the user prefers GUI install.

Exit codes:
  0  Claude Desktop is installed (or install attempt succeeded)
  1  Not installed and no install was attempted / install failed
  2  Environment error (not macOS, etc.)

Detection strategy:
  1. Spotlight metadata (`mdfind` on bundle identifier) — authoritative,
     finds the app at any location regardless of user's install habit.
  2. `/Applications/Claude.app` — covers the 95% case.
  3. `~/Applications/Claude.app` — user-scope install fallback.

The skill's SKILL.md references this script from the "Cowork 3P provisioning"
workflow. See `references/cowork_provisioning.md` for the broader context.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

BUNDLE_ID = "com.anthropic.claudefordesktop"
DOWNLOAD_URL = "https://claude.com/download"
INFO_PLIST = "Contents/Info.plist"


def die(msg: str, code: int = 2) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_bundle_version(app_path: Path) -> str | None:
    """Read CFBundleShortVersionString from an app bundle's Info.plist.

    Falls back to None on any failure rather than raising — the version is
    informational, not load-bearing.
    """
    plist = app_path / INFO_PLIST
    if not plist.exists():
        return None
    try:
        r = subprocess.run(
            ["defaults", "read", str(plist.with_suffix("")), "CFBundleShortVersionString"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def detect() -> dict:
    """Find Claude Desktop on this machine.

    Returns a dict:
      {"installed": bool, "path": str|None, "version": str|None, "method": str|None}

    `method` says how we found it — useful for debugging (Spotlight vs fallback path).
    """
    # 1. Spotlight — authoritative, bundle-id based
    try:
        r = subprocess.run(
            ["mdfind", f"kMDItemCFBundleIdentifier == '{BUNDLE_ID}'"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line and line.endswith(".app") and Path(line).exists():
                return {
                    "installed": True,
                    "path": line,
                    "version": read_bundle_version(Path(line)),
                    "method": "spotlight",
                }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 2. Conventional locations
    for candidate in [
        Path("/Applications/Claude.app"),
        Path.home() / "Applications/Claude.app",
    ]:
        if candidate.exists():
            return {
                "installed": True,
                "path": str(candidate),
                "version": read_bundle_version(candidate),
                "method": "filesystem-scan",
            }

    return {"installed": False, "path": None, "version": None, "method": None}


def install_via_brew() -> bool:
    """Install Claude Desktop via Homebrew cask.

    Returns True on success. False on any failure (including missing brew,
    cask not found, install error). Stderr gets the brew output on failure.

    Handles Rosetta mismatch: if this Python is x86_64 but brew lives at
    /opt/homebrew (ARM-native prefix), brew refuses to install under Rosetta.
    We detect this and re-wrap the command with `arch -arm64`. Without this,
    anyone running the skill from a Rosetta-spawned shell (conda-x86_64, etc.)
    gets "Cannot install under Rosetta 2 in ARM default prefix" and thinks
    the skill is broken.
    """
    import platform

    brew = shutil.which("brew")
    if not brew:
        print(
            "Homebrew not found. Either install Homebrew first "
            "(https://brew.sh), or run with --open-download to use the GUI installer.",
            file=sys.stderr,
        )
        return False

    cmd = [brew, "install", "--cask", "claude"]
    # If Python is Rosetta-x86 but brew is ARM-native, we must re-invoke under ARM
    if platform.machine() == "x86_64" and "/opt/homebrew" in brew:
        cmd = ["arch", "-arm64"] + cmd
        print(
            "note: detected Rosetta-x86 Python + ARM-native brew at /opt/homebrew, "
            "wrapping with `arch -arm64`",
            file=sys.stderr,
        )

    print("Installing Claude Desktop via Homebrew... (this may take 1–3 minutes)")
    r = subprocess.run(
        cmd,
        # stream brew output directly so the user sees progress
    )
    if r.returncode != 0:
        print(
            f"\nbrew install --cask claude failed (exit {r.returncode}). "
            "Try `--open-download` for the official DMG instead.",
            file=sys.stderr,
        )
        return False
    return True


def open_download_page() -> None:
    """Open the official download page in the user's default browser."""
    print(f"Opening {DOWNLOAD_URL} in your browser...")
    print("Download the DMG, drag Claude.app into Applications, then come back")
    print("and tell me 'installed' / '装好了' — I'll continue the setup.")
    opened = webbrowser.open(DOWNLOAD_URL)
    if not opened:
        # webbrowser returns False on some macOS setups even when it worked; also
        # try `open` as a belt-and-suspenders fallback.
        subprocess.run(["open", DOWNLOAD_URL])


def format_status(info: dict) -> str:
    if info["installed"]:
        ver = info.get("version") or "unknown"
        path = info["path"]
        method = info.get("method") or "?"
        return (
            f"✓ Claude Desktop is installed\n"
            f"  path:    {path}\n"
            f"  version: {ver}\n"
            f"  (found via {method})"
        )
    return (
        "✗ Claude Desktop is NOT installed on this machine.\n"
        "  Options:\n"
        f"    A. Homebrew (0-click):  brew install --cask claude\n"
        f"    B. Official DMG (GUI):  open {DOWNLOAD_URL}\n"
        "  Re-run this script with --install-brew or --open-download to act on\n"
        "  one of these, or have the skill orchestrate it for you."
    )


def main() -> None:
    if platform.system() != "Darwin":
        die(
            "This script only supports macOS. Claude Desktop on Windows/Linux "
            "is distributed separately — see https://claude.com/download."
        )

    p = argparse.ArgumentParser(
        description=(
            "Detect (and optionally install) Claude Desktop. Pre-flight check "
            "for Cowork 3P provisioning."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  check_claude_desktop.py                    # just detect\n"
            "  check_claude_desktop.py --json             # machine-readable\n"
            "  check_claude_desktop.py --install-brew     # try brew\n"
            "  check_claude_desktop.py --open-download    # open browser\n"
        ),
    )
    p.add_argument("--json", action="store_true", help="emit detection result as JSON")
    p.add_argument(
        "--install-brew",
        action="store_true",
        help="attempt `brew install --cask claude`",
    )
    p.add_argument(
        "--open-download",
        action="store_true",
        help=f"open {DOWNLOAD_URL} in the default browser",
    )
    args = p.parse_args()

    if args.install_brew and args.open_download:
        die("pick one of --install-brew / --open-download, not both")

    # First always detect current state
    info = detect()

    if args.install_brew and not info["installed"]:
        if not install_via_brew():
            sys.exit(1)
        # Re-detect after install
        info = detect()

    if args.open_download and not info["installed"]:
        open_download_page()
        # Don't re-detect — user hasn't finished the GUI install yet.
        print("\n(Detection not repeated — install is asynchronous.)")
        sys.exit(1)

    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(format_status(info))

    sys.exit(0 if info["installed"] else 1)


if __name__ == "__main__":
    main()
