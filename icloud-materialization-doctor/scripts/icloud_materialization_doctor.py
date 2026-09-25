#!/usr/bin/env python3
"""icloud-materialization-doctor

Diagnose macOS iCloud Drive sync issues in BOTH directions:

  Download-side ("dataless" files, the original purpose of this skill):
    On modern macOS, iCloud Drive no longer exposes `.icloud` placeholder
    files as its primary "not yet downloaded" marker. Instead, files appear
    with their real name and correct logical size but with zero physical
    blocks on disk (st_size > 0 && st_blocks == 0). These files are invisible
    to the classic `find -name '*.icloud'` readiness check, which is why
    tools like agent-sync-doctor can falsely report "iCloud is ready" while
    real content is still missing on the local disk.

  Upload-side (added in v2): files that exist locally with full content but
    never finish uploading to iCloud. Common symptoms include `brctl status`
    entries with `sig:<file-pending>` plus an `[active]` upload session that
    sits there for hours, `brctl quota` hanging, and other devices on the
    same iCloud account never receiving the file. The canonical signal is
    `brctl status`, which we can read when not sandboxed; we always fall
    back to filesystem analysis (large files / build-artifact dirs) so the
    `upload-check` subcommand still produces useful output even when brctl
    is unavailable.

The download-side check / fix path is sandbox-safe by design (only stdlib
file-system calls). The upload-side path uses `brctl` opportunistically and
degrades gracefully when it can't.

Subcommands:
    check                  — scan paths, report dataless file count / samples;
                             exit 0 iff all files are materialized.
    fix                    — stat-walk to nudge File Provider, then optional
                             `head -c 1` force-read; exits 0 iff clean.
    upload-check           — diagnose upload-side stuck state (brctl pending
                             counts when available + filesystem-level
                             upload-pressure analysis); always prints a
                             multi-machine caveat (see "Causal humility"
                             section in SKILL.md).
    housekeeping-suggest   — propose safe build-artifact cleanup for sync
                             roots; dry-run by default, requires --apply
                             to actually delete.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional, Tuple

# --- Constants ---------------------------------------------------------------

# Known iCloud sync roots used by the agent-sync-doctor family of skills. When
# invoked with no --paths, we default to whichever of these exist. Extend or
# override via --paths on the CLI.
DEFAULT_ROOTS: Tuple[str, ...] = (
    "~/Library/Mobile Documents/com~apple~CloudDocs/AgentSync",
    "~/Library/Mobile Documents/com~apple~CloudDocs/ClaudeSync",
    "~/Library/Mobile Documents/com~apple~CloudDocs/CodexSync",
)

# On APFS, materialized files always have st_blocks >= 1 for any nonzero size.
# A file with st_size > 0 and st_blocks == 0 is the File-Provider "dataless"
# state: metadata is local, bytes are not.
def _is_dataless(st: os.stat_result) -> bool:
    return st.st_size > 0 and st.st_blocks == 0


# Build-artifact directory names that are well-defined enough to safely treat
# as "remove-and-recreate-from-source" candidates. Conservative on purpose:
# anything not on this list stays. We'd rather under-suggest than risk eating
# user data from a directory that *happens* to match a generic name in the
# wrong context.
BUILD_ARTIFACT_DIR_NAMES: Tuple[str, ...] = (
    "node_modules",   # npm/yarn/pnpm — fully reproducible from package.json
    "build",          # generic build output (PyInstaller, CMake, etc.)
    "dist",           # bundlers (webpack, rollup, vite, setuptools)
    "__pycache__",    # CPython bytecode cache
    ".next",          # Next.js dev server cache
    ".turbo",         # Turborepo cache
    ".pytest_cache",  # pytest discovery cache
)


# --- ANSI / brctl helpers ----------------------------------------------------
#
# `brctl status` is the single most authoritative source for "what does THIS
# Mac believe is pending upload to iCloud". Two operational realities limit
# how much we can rely on it:
#
#   1. It's blocked inside sandboxes. Claude Code, Codex, and most macOS
#      app sandboxes can't invoke it (returns ENOENT-ish or gets killed by
#      Endpoint Security). We must degrade gracefully.
#   2. It only reflects local state. If the upload that's "stuck" was
#      originated by a *different* Mac on the same iCloud account, this
#      machine's brctl will not show it — see SKILL.md "Multi-machine pitfall".
#
# So: we try brctl with a short timeout, capture output, strip ANSI escapes
# (brctl emits coloured text by default which would confuse downstream
# regexes), and produce a structured count. If brctl is unavailable for any
# reason, callers still get a usable report from the filesystem-level helpers
# below — they just have to interpret it knowing they can't see the upload
# queue.

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


@dataclass
class BrctlPending:
    """Counts parsed from `brctl status` output.

    Field semantics from a 2026-05-14 sample on macOS 26:

        sig_pending     — content signature never computed; means bird never
                          finished the local pre-upload step. Strong stuck
                          signal.
        active_uploads  — current upload sessions. A high count combined
                          with non-zero sig_pending suggests sessions are
                          opening but not progressing.
        pending_sync_up — items queued behind active uploads.
        needs_upload /
        needs_sync_up   — total objects with pending changes.

    `available=False` means we couldn't even run brctl. The note explains why
    so the caller can show the right remediation message.
    """
    sig_pending: int = 0
    active_uploads: int = 0
    pending_sync_up: int = 0
    needs_upload: int = 0
    needs_sync_up: int = 0
    available: bool = False
    note: str = ""


def try_brctl_status(timeout_s: int = 15) -> BrctlPending:
    """Attempt to run `brctl status` and parse it. Always returns a
    BrctlPending; `available=False` if invocation failed.

    Note: `brctl quota` is sometimes a sharper "is the iCloud control plane
    talking to me?" probe than `brctl status` (we've seen it hang specifically
    when CloudKit upload sessions are stuck). We deliberately do NOT call
    `brctl quota` here because it can hang for minutes when broken — the
    timeout would be unreliable and the user would think the script froze.
    The status command is a safer signal source.
    """
    if not shutil.which("brctl"):
        return BrctlPending(note="brctl not in PATH (older macOS or stripped image)")
    try:
        proc = subprocess.run(
            ["brctl", "status"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return BrctlPending(
            note=f"brctl status hung past {timeout_s}s — itself a strong stuck signal"
        )
    except (OSError, PermissionError) as e:
        return BrctlPending(note=f"brctl invocation refused: {e!s} (likely sandboxed)")
    if proc.returncode != 0:
        msg = proc.stderr.strip()[:200] or f"exit {proc.returncode}"
        return BrctlPending(note=f"brctl returned non-zero: {msg}")
    text = _strip_ansi(proc.stdout)
    # Each item appears once in brctl output, but the same metric can occur
    # in multiple lines (e.g. needs-upload appears in both the header and
    # status row). We count occurrences as the most stable proxy.
    return BrctlPending(
        sig_pending=text.count("sig:<file-pending>"),
        active_uploads=len(re.findall(r"> upload\{\[ active", text)),
        pending_sync_up=len(re.findall(r"> upload\{\[ pending-sync-up", text)),
        needs_upload=text.count("up:needs-upload"),
        needs_sync_up=text.count("up:needs-sync-up"),
        available=True,
        note="",
    )


# --- Filesystem-level upload-pressure analysis -------------------------------
#
# These helpers run in any sandbox and answer two practical questions even
# when brctl is unavailable:
#
#   "What are the largest single files that iCloud is being asked to push?"
#       (Big single files dominate sync time and are common stuck sources.)
#
#   "Where are the build-artifact directories that bloat file-count?"
#       (file-count carries per-file RPC overhead; dropping a node_modules
#        with 12K files removes 12K small per-file decisions for sync engine.)


def _dir_stats(d: Path) -> Tuple[int, int]:
    """Return (total_bytes, file_count) for a directory subtree."""
    total_bytes = 0
    count = 0
    stack: List[Path] = [d]
    while stack:
        cur = stack.pop()
        try:
            it = os.scandir(cur)
        except OSError:
            continue
        with it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    total_bytes += st.st_size
                    count += 1
    return total_bytes, count


def find_largest_files(roots: List[Path], top_n: int = 20,
                       min_bytes: int = 1024 * 1024) -> List[Tuple[int, str]]:
    """Return top_n largest regular files across roots, descending by size.

    Used by upload-check to surface the "single biggest pieces of upload
    pressure" even when brctl is unavailable. We don't follow symlinks out
    of the roots — sync roots often contain symlinks pointing back to local
    non-iCloud paths (the agent-sync-doctor pattern), and chasing those
    would inflate the result with unrelated files.
    """
    candidates: List[Tuple[int, str]] = []
    for root in roots:
        if not root.exists():
            continue
        stack: List[Path] = [root]
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for entry in it:
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        if st.st_size >= min_bytes:
                            candidates.append((st.st_size, entry.path))
    candidates.sort(reverse=True)
    return candidates[:top_n]


def find_build_artifact_dirs(roots: List[Path]) -> List[Tuple[int, int, str]]:
    """Return [(size_bytes, file_count, path)] for each build-artifact
    directory found under roots. Sorted by size descending.

    A build-artifact dir is a directory whose name appears in
    BUILD_ARTIFACT_DIR_NAMES. We do NOT recurse into it once we've claimed
    it as an artifact — if there's a `node_modules/foo/build/` nested inside
    a `node_modules`, we treat the outer node_modules as one removable unit.
    """
    out: List[Tuple[int, int, str]] = []
    for root in roots:
        if not root.exists():
            continue
        stack: List[Path] = [root]
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for entry in it:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if entry.name in BUILD_ARTIFACT_DIR_NAMES:
                        size, count = _dir_stats(Path(entry.path))
                        out.append((size, count, entry.path))
                        # Don't descend into a known artifact dir.
                    else:
                        stack.append(Path(entry.path))
    out.sort(reverse=True)
    return out


def _human_size(n: int) -> str:
    """Render a byte count for human eyes. Stays within 6 chars when possible."""
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.1f} {unit}" if unit != "B" else f"{int(f)} {unit}"
        f /= 1024
    return f"{f:.1f} PB"


# --- Core scan ---------------------------------------------------------------

@dataclass
class ScanResult:
    path: str
    exists: bool
    total_files: int = 0
    dataless_count: int = 0
    dataless_bytes: int = 0
    dataless_samples: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.exists and self.dataless_count == 0


def scan_path(root: Path, max_samples: int = 50) -> ScanResult:
    """Walk root recursively, count files and dataless files.

    Uses os.scandir for speed; avoids following symlinks that leave the root
    (to match standard rsync/find semantics). Errors (e.g. broken symlinks)
    are collected but non-fatal.
    """
    result = ScanResult(path=str(root), exists=root.exists())
    if not result.exists:
        return result

    stack: List[Path] = [root]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError as e:
            result.errors.append(f"{d}: {e}")
            continue
        with it:
            for entry in it:
                try:
                    # follow_symlinks=False: we don't want to chase symlinks
                    # out of the iCloud tree (e.g. .claude symlinks may point
                    # back into non-iCloud paths).
                    st = entry.stat(follow_symlinks=False)
                except OSError as e:
                    result.errors.append(f"{entry.path}: {e}")
                    continue
                mode = st.st_mode
                # Regular files only. Directories recurse; symlinks skipped
                # (they are always 0 bytes anyway).
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    result.total_files += 1
                    if _is_dataless(st):
                        result.dataless_count += 1
                        result.dataless_bytes += st.st_size
                        if len(result.dataless_samples) < max_samples:
                            result.dataless_samples.append(entry.path)
    return result


# --- Fix ladder --------------------------------------------------------------

def nudge_by_stat(roots: List[Path]) -> None:
    """Level 1: Stat every file. For many stuck items this alone is enough
    to make File Provider re-queue the dataless ones for background fetch.
    Cheap, safe, no network pressure.
    """
    for root in roots:
        if not root.exists():
            continue
        stack: List[Path] = [root]
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for entry in it:
                    try:
                        entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))


def force_read_dataless(samples: List[str], byte_budget_per_file: int = 1) -> Tuple[int, int]:
    """Level 2: `head -c N` each dataless file. Forces a synchronous open+read,
    which File Provider typically upgrades to a full-file fetch on the first
    byte access. Returns (attempted, materialized_after).
    """
    attempted = 0
    materialized = 0
    for path in samples:
        p = Path(path)
        if not p.exists():
            continue
        try:
            st_before = p.stat()
        except OSError:
            continue
        if not _is_dataless(st_before):
            continue
        attempted += 1
        try:
            # open() alone isn't enough on all macOS versions; we must read at
            # least one byte to trigger the File Provider materialization RPC.
            with open(p, "rb") as f:
                f.read(byte_budget_per_file)
        except OSError:
            # Common transient errors: ETIMEDOUT during fetch, EIO. Leave the
            # counter at "attempted but not verified" — the subsequent scan
            # will tell us the truth.
            continue
        try:
            st_after = p.stat()
        except OSError:
            continue
        if not _is_dataless(st_after):
            materialized += 1
    return attempted, materialized


def wait_drain(roots: List[Path], deadline_s: int = 120,
               poll_every_s: int = 5) -> List[ScanResult]:
    """After nudging, some files will still be actively downloading. Poll
    until either all roots are clean or deadline expires. Returns the final
    scan results regardless.
    """
    deadline = time.monotonic() + deadline_s
    while True:
        results = [scan_path(r) for r in roots]
        remaining = sum(r.dataless_count for r in results)
        if remaining == 0 or time.monotonic() >= deadline:
            return results
        time.sleep(poll_every_s)


# --- CLI ---------------------------------------------------------------------

def resolve_paths(paths: Optional[List[str]]) -> List[Path]:
    if paths:
        return [Path(os.path.expanduser(p)).resolve() for p in paths]
    out: List[Path] = []
    for p in DEFAULT_ROOTS:
        resolved = Path(os.path.expanduser(p))
        if resolved.exists():
            out.append(resolved)
    return out


def emit_human(results: List[ScanResult], *, verbose: bool = False) -> None:
    total_dataless = sum(r.dataless_count for r in results)
    total_files = sum(r.total_files for r in results)
    total_bytes = sum(r.dataless_bytes for r in results)
    for r in results:
        flag = "OK" if r.ready else ("MISSING" if not r.exists else "DATALESS")
        print(f"[{flag}] {r.path}")
        print(f"  files total: {r.total_files}")
        print(f"  dataless:    {r.dataless_count} ({r.dataless_bytes} bytes)")
        if r.errors:
            print(f"  scan errors: {len(r.errors)}")
            if verbose:
                for e in r.errors[:10]:
                    print(f"    {e}")
        if verbose and r.dataless_samples:
            print("  samples:")
            for s in r.dataless_samples[:10]:
                print(f"    {s}")
    print()
    print(f"SUMMARY dataless={total_dataless} bytes={total_bytes} "
          f"(out of {total_files} files across {len(results)} paths)")


def emit_json(results: List[ScanResult]) -> None:
    # Stable schema, version field so callers (agent-sync-doctor) can pin.
    payload = {
        "schemaVersion": 1,
        "paths": [asdict(r) for r in results],
        "summary": {
            "datalessCount": sum(r.dataless_count for r in results),
            "datalessBytes": sum(r.dataless_bytes for r in results),
            "totalFiles":    sum(r.total_files for r in results),
            "ready":         all(r.ready for r in results),
        },
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_check(args: argparse.Namespace) -> int:
    roots = resolve_paths(args.paths)
    if not roots:
        print("no paths to scan (default roots don't exist, and --paths not given)",
              file=sys.stderr)
        return 2
    results = [scan_path(r) for r in roots]
    if args.json:
        emit_json(results)
    else:
        emit_human(results, verbose=args.verbose)
    return 0 if all(r.ready for r in results) else 1


def cmd_fix(args: argparse.Namespace) -> int:
    roots = resolve_paths(args.paths)
    if not roots:
        print("no paths to scan (default roots don't exist, and --paths not given)",
              file=sys.stderr)
        return 2
    quiet = args.json

    if not quiet:
        print("=== phase 1: initial scan ===")
    before = [scan_path(r) for r in roots]
    if not quiet:
        emit_human(before, verbose=args.verbose)

    if all(r.ready for r in before):
        if not quiet:
            print("nothing to do, all roots clean.")
        if args.json:
            emit_json(before)
        return 0

    if not quiet:
        print("=== phase 2: stat-walk nudge (File Provider re-queue) ===")
    nudge_by_stat(roots)

    if not quiet:
        print("=== phase 3: poll for drain (up to {}s) ===".format(args.deadline))
    after_nudge = wait_drain(roots, deadline_s=args.deadline,
                             poll_every_s=args.poll_interval)
    remaining = sum(r.dataless_count for r in after_nudge)
    if not quiet:
        print(f"remaining dataless after nudge + drain: {remaining}")

    if remaining > 0 and args.force_read:
        if not quiet:
            print("=== phase 4: force-read remaining dataless (head -c 1) ===")
        stragglers = [s for r in after_nudge for s in r.dataless_samples]
        # Samples cap is 50 per path; re-fetch exhaustive list if that isn't
        # enough. We do a fresh scan into memory to collect all paths.
        if remaining > sum(len(r.dataless_samples) for r in after_nudge):
            all_paths: List[str] = []
            for r in roots:
                fr = scan_path(r, max_samples=10**9)
                all_paths.extend(fr.dataless_samples)
            stragglers = all_paths
        attempted, materialized = force_read_dataless(stragglers)
        if not quiet:
            print(f"force-read: attempted={attempted} materialized={materialized}")
        after_nudge = wait_drain(roots, deadline_s=args.deadline,
                                 poll_every_s=args.poll_interval)

    if args.json:
        emit_json(after_nudge)
    else:
        print("=== final state ===")
        emit_human(after_nudge, verbose=args.verbose)

    if all(r.ready for r in after_nudge):
        return 0
    # Escalation hints — we intentionally do NOT auto-killall daemons. That
    # path is reserved for the user's hand or an explicit agent-sync-doctor
    # driver with --really-force.
    if not args.json:
        print()
        print("STILL DATALESS. Next steps (manual):")
        print("  1. Wait — File Provider may finish on its own over minutes.")
        print("  2. `killall bird fileproviderd` from a non-sandboxed Terminal")
        print("     (daemons auto-restart; re-queues the fetch pipeline).")
        print("  3. System Settings → Apple ID → iCloud Drive → toggle off/on.")
        print("  4. Sign out of iCloud Drive and back in (last resort, keeps data).")
    return 1


# --- Upload-side subcommands -------------------------------------------------


def _print_multi_machine_caveat() -> None:
    """Always prefix upload-check output with this. The single most common
    way to mis-interpret upload-side data is to forget that brctl reports
    THIS machine's queue, not the queue of whichever machine is actually
    stuck.
    """
    print(f"# host: {socket.gethostname()} ({platform.system()} {platform.release()})")
    print("# CAVEAT: numbers below describe THIS machine's local upload queue.")
    print("#         If the stuck upload was started from a different Mac")
    print("#         (typical when ~/.claude, ~/.codex, ~/.agents are symlinked")
    print("#         to iCloud), this report won't see it. Diagnose on the")
    print("#         machine that did the writes — `ls -la ~/.claude/` to see")
    print("#         whether you're on the symlink-source or symlink-target.")
    print()


def cmd_upload_check(args: argparse.Namespace) -> int:
    """Diagnose upload-side stuck state.

    Strategy:
      1. Print multi-machine caveat (always — the trap is real).
      2. Try `brctl status`. If it works, parse pending counts.
      3. Always run filesystem-level analysis (largest files, build-artifact
         dirs). These work in any sandbox and are useful even when brctl
         isn't, because they identify upload-pressure independently of
         what bird/cloudd is currently doing.

    Exit code:
        0 — brctl available AND no sig:<file-pending>; or brctl unavailable
            AND no obvious upload-pressure structures
        1 — brctl reports stuck items, OR (when brctl unavailable) we found
            bulk build-artifact dirs that are likely a sync hazard
    """
    roots = resolve_paths(args.paths)
    if not roots:
        print("no paths to scan (default roots don't exist, and --paths not given)",
              file=sys.stderr)
        return 2

    if not args.json:
        _print_multi_machine_caveat()

    brctl = try_brctl_status()
    min_bytes = max(1, int(args.min_size_mb)) * 1024 * 1024
    largest = find_largest_files(roots, top_n=args.top_n, min_bytes=min_bytes)
    artifacts = find_build_artifact_dirs(roots)

    if args.json:
        payload = {
            "schemaVersion": 1,
            "subcommand": "upload-check",
            "host": socket.gethostname(),
            "platform": f"{platform.system()} {platform.release()}",
            "brctl": asdict(brctl),
            "topLargestFiles": [
                {"sizeBytes": s, "path": p} for s, p in largest
            ],
            "buildArtifactDirs": [
                {"sizeBytes": s, "fileCount": c, "path": p}
                for s, c, p in artifacts
            ],
            "buildArtifactSummary": {
                "dirCount": len(artifacts),
                "totalBytes": sum(s for s, _, _ in artifacts),
                "totalFiles": sum(c for _, c, _ in artifacts),
            },
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        # brctl section
        print("=== brctl status (this machine only) ===")
        if brctl.available:
            print(f"  sig:<file-pending>          {brctl.sig_pending}")
            print(f"  [active] upload sessions    {brctl.active_uploads}")
            print(f"  [pending-sync-up] queued    {brctl.pending_sync_up}")
            print(f"  up:needs-upload             {brctl.needs_upload}")
            print(f"  up:needs-sync-up            {brctl.needs_sync_up}")
        else:
            print(f"  UNAVAILABLE: {brctl.note}")
            print("  ⚠ Cannot confirm what is or isn't pending upload from this view.")
            print("  ⚠ Run from a non-sandboxed Terminal to get authoritative numbers.")
        print()

        # Largest files
        print(f"=== Top {len(largest)} largest local files (≥{args.min_size_mb} MB) ===")
        if not largest:
            print("  (no files at or above the size threshold)")
        else:
            for size, path in largest:
                print(f"  {_human_size(size):>10}  {path}")
        print()

        # Build artifacts
        print("=== Build-artifact dirs (housekeeping candidates) ===")
        if not artifacts:
            print("  (none found)")
        else:
            total_size = sum(s for s, _, _ in artifacts)
            total_count = sum(c for _, c, _ in artifacts)
            print(f"  found {len(artifacts)} dirs / {total_count} files / "
                  f"{_human_size(total_size)} total")
            for size, count, path in artifacts[:10]:
                print(f"  {_human_size(size):>10}  {count:>6}f  {path}")
            if len(artifacts) > 10:
                print(f"  ... ({len(artifacts) - 10} more)")
            print()
            print("  Run `housekeeping-suggest` to see a removal plan (dry-run by default).")

    if brctl.available:
        return 0 if brctl.sig_pending == 0 else 1
    # brctl unavailable: fall back to "do we have bulk build artifacts?"
    return 0 if not artifacts else 1


def cmd_housekeeping_suggest(args: argparse.Namespace) -> int:
    """Propose removal of build-artifact directories under sync roots.

    Always dry-run unless --apply is passed. With --apply, removes via
    `rm -rf` (these are reproducible from source — npm install, build
    rerun, etc.). We do NOT remove anything outside BUILD_ARTIFACT_DIR_NAMES
    even with --apply; if the user wants to delete other things they should
    do that by hand or write their own command.

    Why no auto-delete of session JSONLs (Codex sessions/, Claude project
    history): those contain irrecoverable conversation history. Surfacing
    them to the user via upload-check is fine; mass-deletion isn't.
    """
    roots = resolve_paths(args.paths)
    if not roots:
        print("no paths to scan (default roots don't exist, and --paths not given)",
              file=sys.stderr)
        return 2

    artifacts = find_build_artifact_dirs(roots)

    print("=== Phase 0: BEFORE state ===")
    total_before_bytes = 0
    total_before_files = 0
    for r in roots:
        sz, cnt = _dir_stats(r)
        total_before_bytes += sz
        total_before_files += cnt
        print(f"  {r}")
        print(f"    {cnt} files / {_human_size(sz)}")
    print()

    if not artifacts:
        print("=== Plan ===")
        print("  No build-artifact directories under the listed roots. Nothing to do.")
        return 0

    art_total_size = sum(s for s, _, _ in artifacts)
    art_total_count = sum(c for _, c, _ in artifacts)

    print("=== Plan: remove these build-artifact directories ===")
    print(f"  {len(artifacts)} dirs / {art_total_count} files / "
          f"{_human_size(art_total_size)} total")
    print(f"  method: rm -rf  (reproducible from source — package.json / build script / py-bytecode)")
    print()
    for size, count, path in artifacts:
        print(f"    {_human_size(size):>10}  {count:>6}f  {path}")
    print()

    if not args.apply:
        print("=== DRY RUN ===")
        print("Re-run with --apply to actually delete. There is no undo for build artifacts;")
        print("recovery means rebuilding from source. We chose rm-rf over Trash because Trash")
        print("on the system disk would itself fill if the artifacts are large.")
        return 0

    # --apply path
    print("=== Applying ===")
    removed = 0
    failed: List[Tuple[str, str]] = []
    for size, count, path in artifacts:
        try:
            # Use shutil instead of subprocess rm to avoid spawning a shell
            # for each dir. shutil.rmtree handles symlink edge cases safely
            # by not following them when given a directory path.
            shutil.rmtree(path)
            removed += 1
            print(f"  removed  {path}  ({_human_size(size)}, {count}f)")
        except OSError as e:
            failed.append((path, str(e)))
            print(f"  FAILED   {path}: {e}")

    print()
    print("=== Phase 2: AFTER state ===")
    total_after_bytes = 0
    total_after_files = 0
    for r in roots:
        sz, cnt = _dir_stats(r)
        total_after_bytes += sz
        total_after_files += cnt
        print(f"  {r}")
        print(f"    {cnt} files / {_human_size(sz)}")
    print()
    print(f"removed {removed}/{len(artifacts)} dirs; "
          f"freed {_human_size(total_before_bytes - total_after_bytes)}; "
          f"file count: {total_before_files} -> {total_after_files}")
    if failed:
        print()
        print(f"WARNINGS: {len(failed)} dirs could not be removed. Review and resolve:")
        for path, err in failed:
            print(f"  {path}: {err}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    # Shared options live in a parent parser so they can be placed either
    # before or after the subcommand on the command line. This matches the
    # ergonomics of most CLIs (git, docker, etc.): `doctor check --paths X`
    # and `doctor --paths X check` both work.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--paths", nargs="+",
                        help="paths to scan. default = agent-sync-doctor roots that exist.")

    p = argparse.ArgumentParser(
        prog="icloud-materialization-doctor",
        description="Detect & remediate macOS File-Provider dataless files in iCloud Drive.",
        parents=[common],
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check",
                       parents=[common],
                       help="scan and report; exit 0 iff all files materialized")
    c.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    c.add_argument("-v", "--verbose", action="store_true", help="print dataless sample paths")
    c.set_defaults(func=cmd_check)

    f = sub.add_parser("fix",
                       parents=[common],
                       help="nudge bird + optional force-read")
    f.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    f.add_argument("-v", "--verbose", action="store_true", help="print dataless sample paths")
    f.add_argument("--force-read", action="store_true",
                   help="also force-read stubborn dataless files (head -c 1 each)")
    f.add_argument("--deadline", type=int, default=120,
                   help="seconds to poll for drain after nudge (default 120)")
    f.add_argument("--poll-interval", type=int, default=5,
                   help="poll interval while waiting for drain (default 5)")
    f.set_defaults(func=cmd_fix)

    u = sub.add_parser("upload-check",
                       parents=[common],
                       help="diagnose upload-side stuck state (sandbox-aware)")
    u.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    u.add_argument("--top-n", type=int, default=20,
                   help="how many largest files to list (default 20)")
    u.add_argument("--min-size-mb", type=int, default=1,
                   help="minimum file size in MB to consider for the largest-files "
                        "list (default 1; raises the threshold to skip clutter)")
    u.set_defaults(func=cmd_upload_check)

    h = sub.add_parser("housekeeping-suggest",
                       parents=[common],
                       help="propose build-artifact cleanup; dry-run unless --apply")
    h.add_argument("--apply", action="store_true",
                   help="actually rm -rf the listed build-artifact dirs (NO undo)")
    h.set_defaults(func=cmd_housekeeping_suggest)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
