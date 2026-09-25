#!/usr/bin/env python3
"""Manage Paseo import history for Codex/Claude sessions.

Paseo stores each imported session as a JSON file under ~/.paseo/agents/<workspace>/
with persistence.sessionId linking to the original Codex/Claude session.
When a session is "closed" in the Paseo UI, archivedAt is set and re-import is blocked.

Usage:
    paseo_agents.py list [--workspace PATTERN] [--status closed|idle|error|all]
    paseo_agents.py show SESSION_ID_PREFIX
    paseo_agents.py clean [--workspace PATTERN] [--status closed|error] [--dry-run]
    paseo_agents.py reset [--dry-run]
    paseo_agents.py diag [--show-all]
"""

import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

AGENTS_DIR = Path.home() / ".paseo" / "agents"
CODEX_STATE_DB = Path.home() / ".codex" / "state_5.sqlite"
PASEO_DAEMON_LOG = Path.home() / ".paseo" / "daemon.log"


def load_agents():
    """Load all agent JSON files, return list of (filepath, data) tuples."""
    agents = []
    pattern = str(AGENTS_DIR / "*" / "*.json")
    for fp in sorted(glob.glob(pattern)):
        try:
            with open(fp) as f:
                data = json.load(f)
            workspace = Path(fp).parent.name
            data["_workspace"] = workspace
            data["_filepath"] = fp
            agents.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARN: Could not read {fp}: {e}", file=sys.stderr)
    return agents


def get_status(a):
    return a.get("lastStatus", "unknown")


def get_session_id(a):
    return a.get("persistence", {}).get("sessionId", "?")


def is_archived(a):
    return a.get("archivedAt") is not None


def fmt_row(a):
    sid = get_session_id(a)
    status = get_status(a)
    archived = "archived" if is_archived(a) else "active"
    provider = a.get("provider", "?")
    title = a.get("title", "(no title)")
    workspace = a.get("_workspace", "?")
    created = a.get("createdAt", "?")[:19]
    return {
        "session_id": sid,
        "provider": provider,
        "status": status,
        "archived": archived,
        "title": title,
        "workspace": workspace,
        "created": created,
        "filepath": a.get("_filepath"),
    }


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(args):
    agents = load_agents()
    if not agents:
        print("No Paseo agent records found.")
        return

    rows = [fmt_row(a) for a in agents]

    # Filter by workspace
    if args.workspace:
        rows = [r for r in rows if args.workspace.lower() in r["workspace"].lower()]

    # Filter by status
    if args.status and args.status != "all":
        if args.status == "closed":
            rows = [r for r in rows if r["archived"] == "archived"]
        else:
            rows = [r for r in rows if r["status"] == args.status]

    if not rows:
        print("No matching records.")
        return

    # Print table
    print(f"{'Session ID':<40} {'Provider':<8} {'Status':<8} {'Archived':<10} {'Title':<30} {'Workspace'}")
    print("-" * 130)
    for r in rows:
        sid_short = r["session_id"][:36]
        title_short = r["title"][:28] if r["title"] else "(no title)"
        print(f"{sid_short:<40} {r['provider']:<8} {r['status']:<8} {r['archived']:<10} {title_short:<30} {r['workspace']}")

    print(f"\nTotal: {len(rows)} record(s)")


def cmd_show(args):
    agents = load_agents()
    prefix = args.session_id.lower()
    matches = [a for a in agents if get_session_id(a).lower().startswith(prefix)]

    if not matches:
        print(f"No agent record matching session ID prefix '{args.session_id}'.")
        return
    if len(matches) > 1:
        print(f"Multiple matches for '{args.session_id}':")
        for a in matches:
            print(f"  {get_session_id(a)}")
        return

    a = matches[0]
    print(json.dumps({k: v for k, v in a.items() if not k.startswith("_")}, indent=2))
    print(f"\nFile: {a['_filepath']}")


def cmd_clean(args):
    agents = load_agents()
    targets = []

    for a in agents:
        # Default: clean closed + archived
        status = get_status(a)
        archived = is_archived(a)

        if args.status == "error":
            if status == "error":
                targets.append(a)
        else:
            # Default: clean closed/archived
            if archived or status == "closed":
                targets.append(a)

    # Filter by workspace
    if args.workspace:
        targets = [a for a in targets if args.workspace.lower() in a["_workspace"].lower()]

    if not targets:
        print("No records to clean.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Will remove {len(targets)} record(s):\n")
    for a in targets:
        sid = get_session_id(a)
        status = get_status(a)
        title = a.get("title", "(no title)")
        print(f"  {sid[:36]}  status={status}  title={title}")
        print(f"    file: {a['_filepath']}")

    if not args.dry_run:
        for a in targets:
            os.remove(a["_filepath"])
        print(f"\nDeleted {len(targets)} record(s). Restart Paseo to re-import these sessions.")
    else:
        print(f"\n[DRY RUN] No files were deleted. Run without --dry-run to execute.")


def cmd_reset(args):
    agents = load_agents()
    if not agents:
        print("No agent records found.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Will remove ALL {len(agents)} agent record(s):\n")
    for a in agents:
        sid = get_session_id(a)
        status = get_status(a)
        print(f"  {sid[:36]}  status={status}  file={a['_filepath']}")

    if not args.dry_run:
        confirm = input("\nType 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            return
        for a in agents:
            os.remove(a["_filepath"])
        print(f"\nDeleted {len(agents)} record(s). Restart Paseo.")
    else:
        print(f"\n[DRY RUN] No files were deleted. Run without --dry-run to execute.")


def load_codex_sessions():
    """Load sessions from Codex state_5.sqlite. Returns dict of session_id -> title."""
    if not CODEX_STATE_DB.exists():
        return {}
    try:
        conn = sqlite3.connect(str(CODEX_STATE_DB))
        rows = conn.execute("SELECT id, title FROM threads").fetchall()
        conn.close()
        return {r[0]: (r[1] or "")[:60] for r in rows}
    except Exception as e:
        print(f"  WARN: Could not read Codex DB: {e}", file=sys.stderr)
        return {}


def check_relay_status():
    """Check recent relay connection status from daemon log."""
    if not PASEO_DAEMON_LOG.exists():
        return []
    entries = []
    try:
        # Read last 50 lines
        with open(PASEO_DAEMON_LOG) as f:
            lines = f.readlines()[-50:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                msg = obj.get("msg", "")
                if "relay" in msg.lower():
                    ts = obj.get("time", "")
                    entries.append((ts, msg))
            except json.JSONDecodeError:
                pass
    except OSError:
        pass
    return entries


def check_paseo_running():
    """Check if Paseo daemon is running."""
    try:
        result = subprocess.run(["pgrep", "-f", "Paseo Daemon"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def cmd_diag(args):
    """Deep diagnosis: cross-reference Codex DB vs Paseo records + relay status."""
    agents = load_agents()
    paseo_sids = {}
    for a in agents:
        sid = get_session_id(a)
        if sid != "?":
            paseo_sids[sid] = a

    codex_sessions = load_codex_sessions()

    print("=" * 80)
    print("PASEO IMPORT DOCTOR — DEEP DIAGNOSIS")
    print("=" * 80)

    # 1. Paseo daemon status
    running = check_paseo_running()
    print(f"\n[1] Paseo Daemon: {'RUNNING' if running else 'NOT RUNNING'}")
    if not running:
        print("    ⚠ Daemon is not running. Start Paseo before importing.")

    # 2. Paseo agent records summary
    print(f"\n[2] Paseo Agent Records: {len(agents)} total")
    by_status = {}
    for a in agents:
        s = get_status(a)
        by_status[s] = by_status.get(s, 0) + 1
    for s, c in sorted(by_status.items()):
        blocked = " ← blocks re-import" if s in ("closed", "error") else ""
        print(f"    {s}: {c}{blocked}")

    # 3. Cross-reference: Codex sessions blocked by Paseo records
    print(f"\n[3] Codex Sessions ({len(codex_sessions)} in DB):")
    blocked_count = 0
    importable_count = 0
    for sid, title in sorted(codex_sessions.items(), key=lambda x: x[1]):
        if sid in paseo_sids:
            a = paseo_sids[sid]
            status = get_status(a)
            ws = a.get("_workspace", "?")
            print(f"    BLOCKED:    {sid[:36]}  [{status}]  ws={ws}  title={title[:40]}")
            blocked_count += 1
        else:
            importable_count += 1

    if args.show_all:
        for sid, title in sorted(codex_sessions.items(), key=lambda x: x[1]):
            if sid not in paseo_sids:
                print(f"    IMPORTABLE: {sid[:36]}  title={title[:40]}")
    else:
        print(f"    ... {importable_count} importable sessions (use --show-all to list)")

    print(f"\n    Summary: {blocked_count} blocked, {importable_count} importable")

    # 4. Relay status
    relay_entries = check_relay_status()
    print(f"\n[4] Relay Connection (last {len(relay_entries)} entries):")
    if not relay_entries:
        print("    No relay entries found in daemon log.")
    else:
        disconnects = sum(1 for _, msg in relay_entries if "disconnect" in msg.lower())
        connects = sum(1 for _, msg in relay_entries if "connect" in msg.lower() and "disconnect" not in msg.lower())
        print(f"    Recent: {connects} connects, {disconnects} disconnects")
        for ts, msg in relay_entries[-5:]:
            print(f"      {ts}: {msg[:80]}")
        if disconnects > connects:
            print("    ⚠ More disconnects than connects — mobile app may have connection issues.")

    # 5. Workspace breakdown
    print(f"\n[5] Workspace Breakdown:")
    by_ws = {}
    for a in agents:
        ws = a.get("_workspace", "?")
        by_ws.setdefault(ws, []).append(a)
    for ws, ws_agents in sorted(by_ws.items()):
        blocked = sum(1 for a in ws_agents if is_archived(a) or get_status(a) == "closed")
        print(f"    {ws}: {len(ws_agents)} records ({blocked} blocked)")

    print(f"\n{'=' * 80}")


def cmd_restart(args):
    """Restart Paseo daemon + app so cleaned import records take effect."""
    # 1. Quit app gracefully
    print("[1/4] Quitting Paseo app...")
    subprocess.run(["osascript", "-e", 'quit app "Paseo"'], capture_output=True)
    time.sleep(2)

    # 2. Kill daemon
    print("[2/4] Killing Paseo Daemon...")
    try:
        result = subprocess.run(["pgrep", "-f", "Paseo Daemon"], capture_output=True, text=True)
        if result.returncode == 0:
            for pid in result.stdout.strip().split("\n"):
                pid = pid.strip()
                if pid:
                    subprocess.run(["kill", "-9", pid], capture_output=True)
            time.sleep(1)
        else:
            print("    (daemon already stopped)")
    except Exception as e:
        print(f"    WARN: {e}")

    # 3. Verify stopped
    print("[3/4] Verifying all Paseo processes stopped...")
    time.sleep(1)
    if check_paseo_running():
        print("    ⚠ Daemon still running! Try manually: kill -9 $(pgrep -f 'Paseo Daemon')")
        return
    print("    ✓ All Paseo processes stopped.")

    # 4. Reopen
    print("[4/4] Reopening Paseo...")
    subprocess.run(["open", "-a", "Paseo"], capture_output=True)
    time.sleep(3)
    if check_paseo_running():
        print("    ✓ Paseo restarted successfully. Import records reloaded from disk.")
    else:
        print("    ⚠ Paseo may still be starting. Wait a few seconds and check.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage Paseo import history")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List imported sessions")
    p_list.add_argument("--workspace", "-w", help="Filter by workspace name pattern")
    p_list.add_argument("--status", "-s", choices=["closed", "idle", "error", "all"], default="all",
                        help="Filter by status (default: all)")

    # show
    p_show = sub.add_parser("show", help="Show details of a session")
    p_show.add_argument("session_id", help="Session ID or prefix")

    # clean
    p_clean = sub.add_parser("clean", help="Remove archived/closed import records")
    p_clean.add_argument("--workspace", "-w", help="Filter by workspace name pattern")
    p_clean.add_argument("--status", "-s", choices=["closed", "error"], default="closed",
                         help="Which status to clean (default: closed)")
    p_clean.add_argument("--dry-run", "-n", action="store_true", help="Preview without deleting")

    # reset
    p_reset = sub.add_parser("reset", help="Remove ALL import records (nuclear option)")
    p_reset.add_argument("--dry-run", "-n", action="store_true", help="Preview without deleting")

    # diag
    p_diag = sub.add_parser("diag", help="Deep diagnosis: cross-ref Codex DB + relay status")
    p_diag.add_argument("--show-all", "-a", action="store_true", help="List all importable sessions")

    # restart
    sub.add_parser("restart", help="Restart Paseo daemon + app (reload cleaned records)")

    args = parser.parse_args()
    {"list": cmd_list, "show": cmd_show, "clean": cmd_clean, "reset": cmd_reset,
     "diag": cmd_diag, "restart": cmd_restart}[args.command](args)


if __name__ == "__main__":
    main()
