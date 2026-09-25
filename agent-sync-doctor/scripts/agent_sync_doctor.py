#!/usr/bin/env python3
"""Agent Sync Doctor — 统一的 Claude + Codex 同步健康检查与交接工具。

继承自 claude-sync-doctor 的 manifest-driven 架构，扩展对 Codex 的支持：
SQLite snapshot/restore、.codex-global-state.json JSON merge、first-time 接入编排。

Commands:
    check / deep-check / repair / handoff / icloud-check / state /
    desktop-check / desktop-repair / install-launchagent   (兼容旧 claude-sync-doctor)
    leave / arrive                                          (V2 新增统一命令)

Usage:
    python3 agent_sync_doctor.py check --products claude,codex
    python3 agent_sync_doctor.py leave --products claude,codex --yes
    python3 agent_sync_doctor.py arrive --products claude,codex --yes
    python3 agent_sync_doctor.py handoff --products claude --yes --force   # 旧命令兼容
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import json
import os
import plistlib
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


SCRIPT = Path(__file__).resolve()
SKILL_DIR = SCRIPT.parents[1]
REFS = SKILL_DIR / "references"
DEFAULT_CLAUDE_MANIFEST = REFS / "products.claude.json"
DEFAULT_CODEX_MANIFEST = REFS / "products.codex.json"
DEFAULT_DESKTOP_GROUP_ID = "00000000-0000-4000-8000-000000000001"


# ---------------------------------------------------------------------------
# Common utilities (ported from claude_sync_doctor.py)
# ---------------------------------------------------------------------------

def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def expand(path: str, root: Optional[Path] = None) -> Path:
    if root is not None and not path.startswith("~") and not path.startswith("/"):
        return (root / path).expanduser()
    return Path(path).expanduser()


def sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stat_info(path: Path) -> Dict[str, Any]:
    try:
        st = path.stat()
        return {"exists": True, "size": st.st_size, "mtime": int(st.st_mtime)}
    except FileNotFoundError:
        return {"exists": False}


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)


def same_target(local: Path, cloud: Path) -> bool:
    try:
        return local.resolve(strict=False) == cloud.resolve(strict=False)
    except OSError:
        return False


def cloud_container_and_prefix(path: Path) -> Tuple[str, str]:
    resolved = path.expanduser()
    parts = resolved.parts
    container_index = None
    for idx, part in enumerate(parts):
        if part.startswith("com~apple~CloudDocs"):
            container_index = idx
            break
    if container_index is None:
        return "com~apple~CloudDocs", f"/{resolved.name}"
    container = parts[container_index]
    relative = parts[container_index + 1:]
    prefix = "/" + "/".join(relative) if relative else "/"
    return container, prefix


def path_is_under(path: str, prefix: str) -> bool:
    if prefix == "/":
        return path.startswith("/")
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def brctl_pending_paths(output: str, terms: Iterable[str]) -> Set[str]:
    pending: Set[str] = set()
    current_path: Optional[str] = None
    needles = tuple(terms)
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Under "):
            current_path = stripped[len("Under "):]
            continue
        if current_path and any(term in stripped for term in needles):
            pending.add(current_path)
    return pending


def detect_processes(patterns: List[str]) -> Tuple[bool, List[str]]:
    """Detect running processes matching any of the given regex patterns."""
    override = os.environ.get("AGENT_SYNC_DOCTOR_ASSUME_RUNNING")
    if override is not None:
        running = override.strip().lower() in {"1", "true", "yes", "running"}
        return running, ["AGENT_SYNC_DOCTOR_ASSUME_RUNNING=1"] if running else []
    try:
        proc = subprocess.run(["ps", "-axo", "pid,ppid,args"], capture_output=True, text=True)
        lines = proc.stdout.splitlines()
    except Exception:
        # Fall back to pgrep (may fail under Claude Code sandbox)
        pids: List[str] = []
        for pattern in patterns:
            try:
                p = subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True)
                if p.returncode == 0:
                    for line in p.stdout.splitlines():
                        if "agent_sync_doctor" not in line:
                            pids.append(line)
            except Exception:
                pass
        return bool(pids), sorted(set(pids))

    combined = "|".join(patterns)
    matches = []
    for line in lines:
        if re.search(combined, line) and "agent_sync_doctor" not in line and "claude_sync_doctor" not in line:
            matches.append(line.strip())
    return bool(matches), matches


# ---------------------------------------------------------------------------
# File-Provider dataless detection — delegated to icloud-materialization-doctor
# ---------------------------------------------------------------------------
# macOS 12+ replaced `.icloud` placeholder files with a File-Provider "dataless"
# state: node exists, logical size is correct, but physical blocks = 0. The
# classic `find -name '*.icloud'` readiness check misses this entirely, so we
# delegate to the companion skill icloud-materialization-doctor. Fail-open: if
# the companion is not installed, this returns None and callers fall back to
# placeholder-only checks (backwards-compat).

_ICLOUD_MATERIALIZATION_SCRIPT_CANDIDATES = (
    "~/.agents/skills/icloud-materialization-doctor/scripts/icloud_materialization_doctor.py",
    "~/.claude/skills/icloud-materialization-doctor/scripts/icloud_materialization_doctor.py",
)


def _find_icloud_materialization_script() -> Optional[Path]:
    for raw in _ICLOUD_MATERIALIZATION_SCRIPT_CANDIDATES:
        p = Path(raw).expanduser()
        if p.is_file():
            return p
    return None


def icloud_materialization_report(icloud_root: Path, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """Invoke icloud-materialization-doctor check --json on icloud_root.

    Returns parsed JSON payload on success, or None if the companion skill is
    not installed / the call failed / the output wasn't JSON. Callers treat
    None as "can't determine dataless state" and fall back to allow-through.
    """
    script = _find_icloud_materialization_script()
    if script is None:
        return None
    try:
        proc = subprocess.run(
            ["python3", str(script), "check", "--json", "--paths", str(icloud_root)],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    # check returns 0=ready, 1=dataless present, 2=bad args. Accept 0/1.
    if proc.returncode not in (0, 1):
        return None
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# ProductDoctor — 基类：manifest-driven 的单产品 Doctor
# ---------------------------------------------------------------------------

class ProductDoctor:
    """Base class for per-product sync doctor. Manifest-driven, like the
    original claude_sync_doctor.py's Doctor class."""

    def __init__(self, manifest_path: Path, quiet: bool = False):
        self.manifest_path = manifest_path
        self.manifest = read_json(manifest_path, {})
        if not self.manifest:
            raise SystemExit(f"Cannot read manifest: {manifest_path}")
        self.product = self.manifest.get("product", "unknown")
        self.hostname = socket.gethostname()
        self.icloud_root = expand(self.manifest["icloudRoot"])
        self.backup_root = expand(self.manifest.get(
            "backupRoot", f"~/{self.product}SyncBackups/doctor"))
        state_template = self.manifest.get(
            "statePath",
            str(self.icloud_root / ".doctor" / "state" / "{hostname}.json"),
        )
        self.state_path = expand(state_template.format(hostname=self.hostname))
        self.state = read_json(self.state_path, {"entries": {}})
        self.quiet = quiet
        self.process_patterns = self.manifest.get("processPatterns", [])

    def is_running(self) -> Tuple[bool, List[str]]:
        return detect_processes(self.process_patterns)

    def entry_paths(self, entry: Dict[str, Any]) -> Tuple[Path, Path]:
        local = expand(entry["local"])
        cloud = expand(entry["cloud"], self.icloud_root)
        return local, cloud

    def print(self, msg: str) -> None:
        if not self.quiet:
            print(msg)

    # ----- Classification -------------------------------------------------

    def classify(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        local, cloud = self.entry_paths(entry)
        result: Dict[str, Any] = {
            "id": entry["id"],
            "type": entry["type"],
            "local": str(local),
            "cloud": str(cloud),
            "status": "UNKNOWN",
            "localIsSymlink": local.is_symlink(),
            "cloudExists": cloud.exists(),
        }
        exists_or_link = local.exists() or local.is_symlink()
        if not exists_or_link:
            result["status"] = "MISSING_LOCAL_CLOUD_EXISTS" if cloud.exists() else "MISSING_BOTH"
            return result
        if local.is_symlink():
            result["linkTarget"] = os.readlink(local)
            if same_target(local, cloud):
                result["status"] = "OK" if cloud.exists() else "BROKEN_SYMLINK_TARGET_MISSING"
            else:
                result["status"] = "WRONG_SYMLINK_TARGET"
            return result
        if entry["type"] == "file":
            if not local.is_file():
                result["status"] = "LOCAL_SPECIAL"
                return result
            if not cloud.exists():
                result["status"] = "LOCAL_FILE_CLOUD_MISSING"
                result["localSha"] = sha256(local)
                return result
            if not cloud.is_file():
                result["status"] = "CLOUD_NOT_FILE"
                return result
            local_sha = sha256(local)
            cloud_sha = sha256(cloud)
            result["localSha"] = local_sha
            result["cloudSha"] = cloud_sha
            result["localStat"] = stat_info(local)
            result["cloudStat"] = stat_info(cloud)
            if local_sha == cloud_sha:
                result["status"] = "LOCAL_FILE_MATCHES_CLOUD_BUT_NOT_SYMLINK"
            else:
                result["status"] = "LOCAL_FILE_DIFFERS_FROM_CLOUD"
            return result
        if entry["type"] == "directory":
            if not local.is_dir():
                result["status"] = "LOCAL_NOT_DIRECTORY"
                return result
            if not cloud.exists():
                result["status"] = "LOCAL_DIR_CLOUD_MISSING"
                return result
            if not cloud.is_dir():
                result["status"] = "CLOUD_NOT_DIRECTORY"
                return result
            result["status"] = "LOCAL_DIR_EXISTS_BUT_NOT_SYMLINK"
            return result
        return result

    def check(self, update_state: bool = False) -> List[Dict[str, Any]]:
        results = [self.classify(e) for e in self.manifest.get("entries", [])]
        if update_state:
            self.update_state(results)
        return results

    def deep_check(self) -> List[Dict[str, Any]]:
        results = self.check(update_state=False)
        for entry, result in zip(self.manifest.get("entries", []), results):
            local, cloud = self.entry_paths(entry)
            if entry["type"] != "directory":
                continue
            if local.is_symlink() and same_target(local, cloud):
                result["deep"] = {"note": "symlink resolves to cloud; no tree diff needed"}
                continue
            if local.is_dir() and cloud.is_dir():
                result["deep"] = self.diff_trees(local, cloud, limit=50)
        return results

    def diff_trees(self, local: Path, cloud: Path, limit: int = 50) -> Dict[str, Any]:
        local_files = {str(p.relative_to(local)): p for p in local.rglob("*")
                       if p.is_file() and not p.name.endswith(".icloud")}
        cloud_files = {str(p.relative_to(cloud)): p for p in cloud.rglob("*")
                       if p.is_file() and not p.name.endswith(".icloud")}
        only_local = sorted(set(local_files) - set(cloud_files))
        only_cloud = sorted(set(cloud_files) - set(local_files))
        changed: List[str] = []
        for rel in sorted(set(local_files) & set(cloud_files)):
            try:
                if local_files[rel].stat().st_size != cloud_files[rel].stat().st_size \
                        or not filecmp.cmp(local_files[rel], cloud_files[rel], shallow=False):
                    changed.append(rel)
            except OSError:
                changed.append(rel)
            if len(changed) >= limit:
                break
        return {
            "onlyLocalCount": len(only_local),
            "onlyCloudCount": len(only_cloud),
            "changedCountAtLeast": len(changed),
            "onlyLocalSample": only_local[:limit],
            "onlyCloudSample": only_cloud[:limit],
            "changedSample": changed[:limit],
        }

    # ----- Repair ---------------------------------------------------------

    def repair(self, safe: bool, apply: bool, force: bool, update_state: bool) -> List[Dict[str, Any]]:
        running, processes = self.is_running()
        results: List[Dict[str, Any]] = []
        for entry in self.manifest.get("entries", []):
            result = self.classify(entry)
            result["actions"] = []
            self.repair_entry(entry, result, running=running, safe=safe, apply=apply, force=force)
            if running and result.get("actions"):
                result["productRunning"] = True
                result["processSample"] = processes[:5]
            results.append(result)
        if update_state and apply:
            self.update_state([self.classify(e) for e in self.manifest.get("entries", [])])
        return results

    def repair_entry(self, entry, result, running, safe, apply, force):
        if result["status"] == "OK":
            return
        local, cloud = self.entry_paths(entry)
        if entry["type"] == "directory":
            self.repair_directory(entry, result, local, cloud, running, safe, apply, force)
        else:
            self.repair_file(entry, result, local, cloud, running, safe, apply, force)

    def add_action(self, result, text):
        result.setdefault("actions", []).append(text)

    def backup_path(self, entry_id, side, original):
        dest = self.backup_root / now_stamp() / entry_id / side / original.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    def copy_file_atomic(self, src, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + f".tmp.{os.getpid()}")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)

    def backup_file(self, entry_id, side, path, apply, result):
        if not path.exists() or not path.is_file():
            return None
        dest = self.backup_path(entry_id, side, path)
        self.add_action(result, f"backup {side}: {path} -> {dest}")
        if apply:
            shutil.copy2(path, dest)
        return dest

    def relink_file(self, local, cloud, apply, result):
        self.add_action(result, f"unlink local file and symlink: {local} -> {cloud}")
        if apply:
            try:
                local.unlink()
            except FileNotFoundError:
                pass
            local.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(str(cloud), str(local))

    def repair_file(self, entry, result, local, cloud, running, safe, apply, force):
        status = result["status"]
        entry_id = entry["id"]
        if status == "MISSING_LOCAL_CLOUD_EXISTS":
            self.add_action(result, f"create local symlink: {local} -> {cloud}")
            if apply:
                local.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(str(cloud), str(local))
            return
        if status == "WRONG_SYMLINK_TARGET":
            if running and safe and not force:
                self.add_action(result, f"defer relink because {self.product} is running")
                return
            self.add_action(result, "replace wrong symlink target")
            if apply:
                local.unlink()
                os.symlink(str(cloud), str(local))
            return
        if status == "LOCAL_FILE_CLOUD_MISSING":
            self.add_action(result, f"copy local file to missing cloud target: {cloud}")
            if apply:
                self.copy_file_atomic(local, cloud)
            if running and safe and not force:
                self.add_action(result, f"defer relink because {self.product} is running")
                return
            self.backup_file(entry_id, "local-before-relink", local, apply, result)
            self.relink_file(local, cloud, apply, result)
            return
        if status == "LOCAL_FILE_MATCHES_CLOUD_BUT_NOT_SYMLINK":
            if running and safe and not force:
                self.add_action(result, f"defer relink because {self.product} is running")
                return
            self.backup_file(entry_id, "local-before-relink", local, apply, result)
            self.relink_file(local, cloud, apply, result)
            return
        if status == "LOCAL_FILE_DIFFERS_FROM_CLOUD":
            decision = self.decide_file_winner(entry_id, local, cloud)
            result["decision"] = decision
            if decision == "local":
                self.backup_file(entry_id, "cloud-before-overwrite", cloud, apply, result)
                self.add_action(result, f"copy newer local file to cloud: {local} -> {cloud}")
                if apply:
                    self.copy_file_atomic(local, cloud)
                if running and safe and not force:
                    self.add_action(result, f"defer relink because {self.product} is running")
                    return
                self.backup_file(entry_id, "local-before-relink", local, apply, result)
                self.relink_file(local, cloud, apply, result)
            elif decision == "cloud":
                if running and safe and not force:
                    self.add_action(result, f"defer relink because {self.product} is running")
                    return
                self.backup_file(entry_id, "local-conflicting-copy", local, apply, result)
                self.relink_file(local, cloud, apply, result)
            else:
                self.add_action(result, "conflict: no automatic overwrite")
            return
        if status == "BROKEN_SYMLINK_TARGET_MISSING":
            self.add_action(result, "cloud target missing; cannot repair without source data")

    def decide_file_winner(self, entry_id, local, cloud):
        entry_state = self.state.get("entries", {}).get(entry_id, {})
        previous_sha = entry_state.get("cloudSha")
        local_sha = sha256(local)
        cloud_sha = sha256(cloud)
        if previous_sha:
            if cloud_sha == previous_sha and local_sha != previous_sha:
                return "local"
            if local_sha == previous_sha and cloud_sha != previous_sha:
                return "cloud"
            if local_sha == cloud_sha:
                return "same"
            return "conflict"
        try:
            local_m = local.stat().st_mtime
            cloud_m = cloud.stat().st_mtime
        except FileNotFoundError:
            return "conflict"
        if abs(local_m - cloud_m) < 2:
            return "conflict"
        return "local" if local_m > cloud_m else "cloud"

    def repair_directory(self, entry, result, local, cloud, running, safe, apply, force):
        status = result["status"]
        if status == "MISSING_LOCAL_CLOUD_EXISTS":
            self.add_action(result, f"create local directory symlink: {local} -> {cloud}")
            if apply:
                local.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(str(cloud), str(local))
            return
        if status == "WRONG_SYMLINK_TARGET":
            if running and safe and not force:
                self.add_action(result, f"defer relink because {self.product} is running")
                return
            self.add_action(result, "replace wrong directory symlink target")
            if apply:
                local.unlink()
                os.symlink(str(cloud), str(local))
            return
        if status == "LOCAL_DIR_EXISTS_BUT_NOT_SYMLINK":
            self.add_action(result, "real directory exists where symlink is expected; not auto-merging")
            self.add_action(result, "run migration/arrive first-time flow")
            return
        if status == "LOCAL_DIR_CLOUD_MISSING":
            self.add_action(result, "cloud directory missing; not auto-initializing from Doctor")
            return
        if status == "BROKEN_SYMLINK_TARGET_MISSING":
            self.add_action(result, "cloud target missing; cannot repair")

    def update_state(self, results):
        state = {"updatedAt": dt.datetime.now().isoformat(), "hostname": self.hostname, "entries": {}}
        for entry in self.manifest.get("entries", []):
            local, cloud = self.entry_paths(entry)
            e: Dict[str, Any] = {
                "type": entry["type"],
                "local": str(local),
                "cloud": str(cloud),
                "status": next((r["status"] for r in results if r["id"] == entry["id"]), "UNKNOWN"),
            }
            if entry["type"] == "file" and cloud.is_file():
                e["cloudSha"] = sha256(cloud)
                e["cloudStat"] = stat_info(cloud)
            elif entry["type"] == "directory" and cloud.is_dir():
                e["cloudStat"] = stat_info(cloud)
            state["entries"][entry["id"]] = e
        write_json(self.state_path, state)
        self.state = state

    # ----- iCloud status --------------------------------------------------

    def icloud_upload_check(self) -> Dict[str, Any]:
        container, prefix = cloud_container_and_prefix(self.icloud_root)
        placeholder_count = 0
        placeholder_samples: List[str] = []
        if self.icloud_root.exists():
            for p in sorted(self.icloud_root.rglob("*.icloud")):
                if not (p.is_file() or p.is_symlink()):
                    continue
                placeholder_count += 1
                if len(placeholder_samples) < 50:
                    placeholder_samples.append(str(p))
        report: Dict[str, Any] = {
            "available": True, "container": container, "prefix": prefix,
            "placeholderCount": placeholder_count, "placeholderSamples": placeholder_samples,
            "currentPendingCount": 0, "currentPending": [], "trashPendingCount": 0,
            "trashPending": [], "otherPendingCount": 0, "ready": False,
            # File-Provider dataless (macOS 12+): populated by companion skill
            # icloud-materialization-doctor. None ⇒ companion not installed,
            # and readiness falls back to placeholder-only check (backwards-compat).
            "datalessCount": None, "datalessSamples": [],
            "datalessCompanionAvailable": False,
        }
        # Delegate to icloud-materialization-doctor. Runs regardless of brctl
        # availability so sandboxed / brctl-less environments still get the
        # dataless signal.
        dl = icloud_materialization_report(self.icloud_root)
        if dl is not None:
            summary = dl.get("summary", {})
            samples = [s for p in dl.get("paths", []) for s in p.get("dataless_samples", [])]
            report["datalessCount"] = summary.get("datalessCount")
            report["datalessSamples"] = samples[:50]
            report["datalessCompanionAvailable"] = True

        def _compute_ready(pending_current_count: int) -> bool:
            """Readiness = no upload pending + no `.icloud` placeholder + no
            File-Provider dataless (or companion unavailable → fall back to
            legacy behavior)."""
            return (
                pending_current_count == 0
                and placeholder_count == 0
                and (report["datalessCount"] in (0, None))
            )

        brctl = shutil.which("brctl")
        if not brctl:
            report.update({"available": False, "reason": "brctl not found",
                           "ready": _compute_ready(0)})
            return report
        try:
            proc = subprocess.run([brctl, "status", container],
                                  capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            report.update({"available": False, "reason": "brctl status timed out",
                           "ready": _compute_ready(0)})
            return report
        report["brctlReturnCode"] = proc.returncode
        if proc.returncode != 0:
            report.update({"available": False, "reason": "brctl status failed",
                          "stderr": proc.stderr.strip()[:500],
                          "ready": _compute_ready(0)})
            return report
        pending_terms = ("needs-sync-up", "sync-up-scheduled", "pending-scan",
                         "uploading", "needs-sync", "needs-upload")
        pending = brctl_pending_paths(proc.stdout, pending_terms)
        current = sorted(p for p in pending if path_is_under(p, prefix))
        trash = sorted(p for p in pending if p.startswith("/.Trash/") and self.icloud_root.name in p)
        other = sorted(p for p in pending if p not in set(current) and p not in set(trash))
        report.update({
            "currentPendingCount": len(current), "currentPending": current[:50],
            "trashPendingCount": len(trash), "trashPending": trash[:50],
            "otherPendingCount": len(other),
            "ready": _compute_ready(len(current)),
        })
        return report

    def wait_icloud_drain(self, max_attempts: int = 12, sleep_sec: int = 25) -> bool:
        """Poll iCloud status until currentPending == 0 and placeholder == 0."""
        for i in range(max_attempts):
            report = self.icloud_upload_check()
            if report.get("ready"):
                self.print(f"  iCloud drained after {i+1} attempt(s)")
                return True
            self.print(f"  iCloud pending={report.get('currentPendingCount', '?')} "
                       f"placeholders={report.get('placeholderCount', '?')}; "
                       f"attempt {i+1}/{max_attempts}")
            time.sleep(sleep_sec)
        return False

    # ----- Print helpers --------------------------------------------------

    def print_results(self, results, include_ok=True):
        bad = 0
        for r in results:
            status = r["status"]
            if status != "OK":
                bad += 1
            if self.quiet and status == "OK":
                continue
            if not include_ok and status == "OK":
                continue
            print(f"[{status}] {r['id']}")
            print(f"  local: {r['local']}")
            print(f"  cloud: {r['cloud']}")
            if r.get("linkTarget"):
                print(f"  link:  {r['linkTarget']}")
            if r.get("decision"):
                print(f"  decision: {r['decision']}")
            for action in r.get("actions", []):
                print(f"  action: {action}")
            if r.get("deep"):
                print(f"  deep: {json.dumps(r['deep'], ensure_ascii=False)}")
        return bad

    # ----- Hooks for subclasses -------------------------------------------

    def leave_extra(self, apply: bool) -> List[str]:
        """Product-specific leave actions (snapshot SQLite etc.). Return list of messages."""
        return []

    def arrive_first_time(self, apply: bool) -> List[str]:
        """Product-specific first-time onboarding actions. Return list of messages."""
        return []

    def arrive_extra(self, apply: bool, first_time: bool) -> List[str]:
        """Product-specific arrive actions (restore SQLite etc.). Return list of messages."""
        return []

    def desktop_orphan_check(self) -> Dict[str, Any]:
        """Override in subclass for product-specific orphan checks."""
        return {"available": False}

    def desktop_visibility_check(self) -> Dict[str, Any]:
        """Override in subclass for product-specific visibility checks."""
        return {"available": False}

    def desktop_visibility_repair(self, apply: bool) -> Dict[str, Any]:
        return {"available": False}

    def is_first_time(self) -> bool:
        """Detect first-time onboarding. Override per product."""
        return False


# ---------------------------------------------------------------------------
# ClaudeProductDoctor — 旧 claude_sync_doctor 的 desktop visibility 逻辑
# ---------------------------------------------------------------------------

class ClaudeProductDoctor(ProductDoctor):

    def find_local_path_for_entry(self, entry_id: str) -> Optional[Path]:
        for entry in self.manifest.get("entries", []):
            if entry.get("id") == entry_id:
                return self.entry_paths(entry)[0]
        return None

    def desktop_orphan_check(self) -> Dict[str, Any]:
        sessions = self.find_local_path_for_entry("desktop-code-sessions")
        dotclaude = self.find_local_path_for_entry("dotclaude")
        projects_entry = self.find_local_path_for_entry("dotclaude-projects")
        projects = projects_entry or (dotclaude / "projects" if dotclaude else Path("~/.claude/projects").expanduser())
        orphans = []
        if not sessions or not sessions.exists() or not projects.exists():
            return {"available": False, "orphans": orphans}
        for meta in sessions.glob("*/*/local_*.json"):
            data = read_json(meta, {})
            cli_id = data.get("cliSessionId")
            if not cli_id:
                continue
            found = list(projects.glob(f"**/{cli_id}.jsonl"))
            if not found:
                orphans.append({"meta": str(meta), "title": data.get("title"), "cliSessionId": cli_id})
        return {"available": True, "orphanCount": len(orphans), "orphans": orphans[:50]}

    def current_desktop_owner(self, sessions: Path) -> Optional[str]:
        data = read_json(sessions.parent / "cowork-enabled-cli-ops.json", {})
        owner = data.get("ownerAccountId")
        return owner if isinstance(owner, str) and owner else None

    def active_desktop_config(self, sessions: Path) -> Dict[str, Any]:
        config_dir = self.find_local_path_for_entry("desktop-config-library") or (sessions.parent / "configLibrary")
        meta = read_json(config_dir / "_meta.json", {})
        applied_id = meta.get("appliedId") or meta.get("activeId")
        active_path = config_dir / f"{applied_id}.json" if isinstance(applied_id, str) and applied_id else None
        active = read_json(active_path, {}) if active_path else {}
        deployment_uuid = active.get("deploymentOrganizationUuid")
        return {
            "configLibrary": str(config_dir),
            "appliedId": applied_id,
            "activeConfig": str(active_path) if active_path else None,
            "deploymentOrganizationUuid": deployment_uuid if isinstance(deployment_uuid, str) else None,
            "configLibraryExists": config_dir.exists(),
        }

    def target_desktop_group(self, sessions: Path, owner: str, create: bool = False) -> Path:
        profile = self.active_desktop_config(sessions)
        deployment_uuid = profile.get("deploymentOrganizationUuid")
        if deployment_uuid:
            target = sessions / owner / deployment_uuid
            if create:
                target.mkdir(parents=True, exist_ok=True)
            return target
        owner_dir = sessions / owner
        groups = [p for p in owner_dir.glob("*") if p.is_dir()] if owner_dir.exists() else []
        if groups:
            groups.sort(key=lambda p: (-len(list(p.glob("local_*.json"))), p.name))
            return groups[0]
        target = owner_dir / DEFAULT_DESKTOP_GROUP_ID
        if create:
            target.mkdir(parents=True, exist_ok=True)
        return target

    def candidate_desktop_groups(self, sessions: Path, owner: str, deployment_uuid: Optional[str]) -> List[Dict[str, str]]:
        candidates: List[Dict[str, str]] = []
        seen: Set[str] = set()

        def add(path: Path, reason: str) -> None:
            key = str(path)
            if key in seen:
                return
            seen.add(key)
            candidates.append({"path": key, "groupId": path.name, "reason": reason})

        if deployment_uuid:
            add(sessions / owner / deployment_uuid, "active-deployment")
        add(sessions / owner / DEFAULT_DESKTOP_GROUP_ID, "legacy-default")
        return candidates

    def desktop_group_summary(self, sessions: Path, owner: str, target_groups: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        summary: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        def add(path: Path, reason: str) -> None:
            key = str(path)
            if key in seen:
                return
            seen.add(key)
            visible = self.visible_session_ids(path)
            summary.append({
                "path": key,
                "groupId": path.name,
                "reason": reason,
                "exists": path.exists(),
                "visibleCount": len(visible),
            })

        for group in target_groups:
            add(Path(group["path"]), group["reason"])
        owner_dir = sessions / owner
        if owner_dir.exists():
            for group in sorted(p for p in owner_dir.iterdir() if p.is_dir()):
                add(group, "existing-owner-group")
        return summary

    def transcript_exists(self, cli_id: str, projects: Path) -> bool:
        if not cli_id or not projects.exists():
            return False
        return any(projects.glob(f"**/{cli_id}.jsonl"))

    def collect_desktop_metadata(self, sessions: Path) -> Dict[str, Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        for meta in sessions.glob("*/*/local_*.json"):
            data = read_json(meta, {})
            session_id = data.get("sessionId") or meta.stem
            if not session_id:
                continue
            existing = records.get(session_id)
            current_time = data.get("lastActivityAt") or data.get("createdAt") or 0
            existing_data = existing.get("data", {}) if existing else {}
            existing_time = existing_data.get("lastActivityAt") or existing_data.get("createdAt") or -1
            if existing is None or current_time >= existing_time:
                records[session_id] = {"path": meta, "data": data, "fileName": meta.name}
        return records

    def visible_session_ids(self, group: Path) -> Set[str]:
        visible: Set[str] = set()
        if not group.exists():
            return visible
        for meta in group.glob("local_*.json"):
            visible.add(read_json(meta, {}).get("sessionId") or meta.stem)
        return visible

    def agent_session_sources(self, agent_sessions: Optional[Path], session_id: str) -> Dict[str, Path]:
        if not agent_sessions or not agent_sessions.exists():
            return {}
        sources: Dict[str, Path] = {}
        for pattern in (f"*/*/{session_id}", f"*/*/{session_id}.json"):
            for src in agent_sessions.glob(pattern):
                if not (src.is_file() or src.is_dir()):
                    continue
                previous = sources.get(src.name)
                if previous is None or src.stat().st_mtime >= previous.stat().st_mtime:
                    sources[src.name] = src
        return sources

    def desktop_visibility_check(self) -> Dict[str, Any]:
        sessions = self.find_local_path_for_entry("desktop-code-sessions")
        agent_sessions = self.find_local_path_for_entry("desktop-agent-sessions")
        dotclaude = self.find_local_path_for_entry("dotclaude")
        projects_entry = self.find_local_path_for_entry("dotclaude-projects")
        projects = projects_entry or (dotclaude / "projects" if dotclaude else Path("~/.claude/projects").expanduser())
        if not sessions or not sessions.exists():
            return {"available": False, "reason": "desktop-code-sessions path missing"}
        owner = self.current_desktop_owner(sessions)
        if not owner:
            return {"available": False, "reason": "current ownerAccountId missing"}
        active_config = self.active_desktop_config(sessions)
        deployment_uuid = active_config.get("deploymentOrganizationUuid")
        target_groups = self.candidate_desktop_groups(sessions, owner, deployment_uuid)
        target_group = Path(target_groups[0]["path"])
        records = self.collect_desktop_metadata(sessions)
        current_visible = self.visible_session_ids(target_group)
        group_summary = self.desktop_group_summary(sessions, owner, target_groups)
        missing = []
        conflicts = []
        agent_missing = []
        orphans = []
        for session_id, record in sorted(records.items()):
            data = record["data"]
            cli_id = data.get("cliSessionId")
            base_item = {"sessionId": session_id, "cliSessionId": cli_id, "title": data.get("title"),
                         "source": str(record["path"])}
            if not self.transcript_exists(cli_id, projects):
                orphans.append({**base_item, "target": str(target_group / record["fileName"])})
                continue
            for group_info in target_groups:
                group = Path(group_info["path"])
                dst = group / record["fileName"]
                item = {**base_item, "target": str(dst), "targetGroup": str(group), "groupReason": group_info["reason"]}
                if dst.exists():
                    if sha256(record["path"]) != sha256(dst):
                        conflicts.append({**item, "reason": "metadata target exists with different content"})
                    continue
                missing.append(item)
                for name, src in self.agent_session_sources(agent_sessions, session_id).items():
                    agent_dst = (agent_sessions / owner / group.name / name) if agent_sessions else None
                    if agent_dst and src.resolve(strict=False) != agent_dst.resolve(strict=False) and not agent_dst.exists():
                        agent_missing.append({
                            "sessionId": session_id, "source": str(src), "target": str(agent_dst),
                            "targetGroup": str(agent_dst.parent), "groupReason": group_info["reason"],
                        })
        missing_active = [item for item in missing if item.get("targetGroup") == str(target_group)]
        return {
            "available": True, "currentOwner": owner, "activeConfig": active_config,
            "deploymentOrganizationUuid": deployment_uuid,
            "targetGroup": str(target_group), "targetGroups": target_groups,
            "groupSummary": group_summary,
            "metadataCount": len(records), "visibleCount": len(current_visible),
            "orphanCount": len(orphans), "missingVisibleCount": len(missing),
            "missingActiveCount": len(missing_active),
            "metadataConflictCount": len(conflicts),
            "agentSessionMissingCount": len(agent_missing),
            "missingVisible": missing[:50], "missingActive": missing_active[:50],
            "metadataConflicts": conflicts[:50],
            "agentSessionMissing": agent_missing[:50], "orphans": orphans[:50],
        }

    def desktop_visibility_repair(self, apply: bool) -> Dict[str, Any]:
        report = self.desktop_visibility_check()
        report["applied"] = apply
        report["actions"] = []
        if not report.get("available"):
            return report
        for item in report.get("missingVisible", []):
            src = Path(item["source"])
            dst = Path(item["target"])
            action = {"sessionId": item["sessionId"], "source": str(src),
                      "target": str(dst), "action": "copy-metadata"}
            if dst.exists():
                if sha256(src) == sha256(dst):
                    action["action"] = "already-present"
                else:
                    action["action"] = "conflict"
                report["actions"].append(action)
                continue
            if apply:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            report["actions"].append(action)
        for item in report.get("agentSessionMissing", []):
            src = Path(item["source"])
            dst = Path(item["target"])
            action = {"sessionId": item["sessionId"], "source": str(src),
                      "target": str(dst), "action": "copy-agent-session"}
            if dst.exists():
                if src.is_file() and dst.is_file() and sha256(src) == sha256(dst):
                    action["action"] = "already-present"
                else:
                    action["action"] = "conflict"
                report["actions"].append(action)
                continue
            if apply:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            report["actions"].append(action)
        if apply:
            return self.desktop_visibility_check() | {"applied": True, "actions": report["actions"]}
        return report


# ---------------------------------------------------------------------------
# CodexProductDoctor — Codex-specific extensions
# ---------------------------------------------------------------------------

UNION_LIST_KEYS = [
    "electron-saved-workspace-roots", "active-workspace-roots",
    "pinned-thread-ids", "projectless-thread-ids",
    "seen-model-upgrade-list", "project-order",
]
UNION_MAP_KEYS = [
    "thread-titles", "thread-workspace-root-hints",
    "sidebar-collapsed-groups", "agent-mode-by-host-id",
]


def json_union_merge(mac_a: dict, mac_b: dict) -> dict:
    """Union-merge two .codex-global-state.json objects. Mac B (current) wins on scalars."""
    merged = dict(mac_b)
    atom_a = mac_a.get("electron-persisted-atom-state", {})
    atom_b = mac_b.get("electron-persisted-atom-state", {})
    atom_merged = dict(atom_b)
    for key in UNION_LIST_KEYS + ["prompt-history"]:
        a_v = atom_a.get(key, [])
        b_v = atom_b.get(key, [])
        if isinstance(a_v, list) and isinstance(b_v, list):
            seen = set()
            result = []
            for item in b_v + a_v:
                k = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
                if k not in seen:
                    seen.add(k)
                    result.append(item)
            atom_merged[key] = result
    for key in UNION_MAP_KEYS:
        a_v = atom_a.get(key)
        b_v = atom_b.get(key)
        if isinstance(a_v, dict) or isinstance(b_v, dict):
            m = dict(a_v or {})
            m.update(b_v or {})
            atom_merged[key] = m
    merged["electron-persisted-atom-state"] = atom_merged
    for key in UNION_LIST_KEYS:
        a_v = mac_a.get(key, [])
        b_v = mac_b.get(key, [])
        if isinstance(a_v, list) or isinstance(b_v, list):
            seen = set()
            result = []
            for item in (b_v or []) + (a_v or []):
                k = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
                if k not in seen:
                    seen.add(k)
                    result.append(item)
            merged[key] = result
    for key in UNION_MAP_KEYS:
        a_v = mac_a.get(key)
        b_v = mac_b.get(key)
        if isinstance(a_v, dict) or isinstance(b_v, dict):
            m = dict(a_v or {})
            m.update(b_v or {})
            merged[key] = m
    return merged


class CodexProductDoctor(ProductDoctor):

    @property
    def codex_home(self) -> Path:
        return Path("~/.codex").expanduser()

    @property
    def snapshot_cfg(self) -> dict:
        return self.manifest.get("snapshot", {})

    def is_first_time(self) -> bool:
        """No .pre-icloud-* markers = never onboarded."""
        if not self.codex_home.exists():
            return True
        for p in self.codex_home.iterdir():
            if ".pre-icloud-" in p.name:
                return False
        return True

    def sqlite_thread_count(self, db: Path) -> Optional[int]:
        if not db.exists():
            return None
        try:
            result = subprocess.run(
                ["sqlite3", f"file:{db}?mode=ro", "SELECT count(*) FROM threads;"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        return None

    def sqlite_orphan_check(self, db: Path) -> Tuple[int, int]:
        if not db.exists():
            return (0, 0)
        try:
            result = subprocess.run(
                ["sqlite3", f"file:{db}?mode=ro", "SELECT rollout_path FROM threads;"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return (0, 0)
            rows = [l for l in result.stdout.strip().split("\n") if l]
            orphan = 0
            dotcodex_icloud = self.icloud_root / "dotcodex"
            for rp in rows:
                p = Path(rp)
                if p.exists():
                    continue
                rel = rp.replace(str(self.codex_home) + "/", "")
                if not (dotcodex_icloud / rel).exists():
                    orphan += 1
            return (len(rows), orphan)
        except Exception:
            return (0, 0)

    # ----- leave: snapshot SQLite + auth + plist --------------------------

    def leave_extra(self, apply: bool) -> List[str]:
        messages: List[str] = []
        snap = self.snapshot_cfg

        if not apply:
            messages.append("would checkpoint + snapshot SQLite/auth/plist to iCloud")
            messages.extend(codex_plugin_leave_sync(self, apply=False))
            return messages

        # state_5
        state5 = snap.get("state5", {})
        if state5:
            local = expand(state5["local"])
            cloud = expand(state5["cloud"], self.icloud_root)
            if local.exists():
                wal = local.with_name(local.name + "-wal")
                if wal.exists() and wal.stat().st_size > 0:
                    subprocess.run(["sqlite3", str(local), "PRAGMA wal_checkpoint(TRUNCATE);"],
                                   capture_output=True, text=True, timeout=30)
                    messages.append("state_5 WAL checkpoint OK")
                cloud.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local, cloud)
                messages.append(f"state_5.sqlite → {cloud}")

        # codex-dev.db
        dev = snap.get("codexDev", {})
        if dev:
            local = expand(dev["local"])
            cloud = expand(dev["cloud"], self.icloud_root)
            if local.exists():
                subprocess.run(["sqlite3", str(local), "PRAGMA wal_checkpoint(TRUNCATE);"],
                               capture_output=True, text=True, timeout=30)
                cloud.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local, cloud)
                messages.append(f"codex-dev.db → {cloud}")

        # auth
        for item in snap.get("auth", []):
            local = expand(item["local"])
            cloud = expand(item["cloud"], self.icloud_root)
            if local.exists():
                cloud.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local, cloud)
                h = sha256(local) or ""
                messages.append(f"auth: {local.name} size={local.stat().st_size} sha256={h[:16]}…")

        # preferences
        for item in snap.get("preferences", []):
            local = expand(item["local"])
            cloud = expand(item["cloud"], self.icloud_root)
            if local.exists():
                cloud.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local, cloud)
                h = sha256(local) or ""
                messages.append(f"plist: {local.name} size={local.stat().st_size} sha256={h[:16]}…")

        # v4.3: plugin/marketplace config sync (extract + union-merge + write
        # back to iCloud snapshot). plugin source code (plugins/cache, .tmp/*)
        # is intentionally NOT synced — Codex auto-rebuilds on startup.
        messages.extend(codex_plugin_leave_sync(self, apply=True))

        return messages

    # ----- arrive: first-time merge + restore -----------------------------

    def arrive_first_time(self, apply: bool) -> List[str]:
        """Run 08 (SQLite merge) + 09 (JSON merge) logic for first-time onboarding."""
        messages: List[str] = []
        ts = now_stamp()

        # 09: JSON merge for .codex-global-state.json
        local_json = self.codex_home / ".codex-global-state.json"
        icloud_json = self.icloud_root / "dotcodex/.codex-global-state.json"
        if local_json.exists() and icloud_json.exists():
            with open(icloud_json) as f:
                mac_a = json.load(f)
            with open(local_json) as f:
                mac_b = json.load(f)
            merged = json_union_merge(mac_a, mac_b)
            ws_a = len(mac_a.get("electron-saved-workspace-roots", []))
            ws_b = len(mac_b.get("electron-saved-workspace-roots", []))
            ws_m = len(merged.get("electron-saved-workspace-roots", []))
            messages.append(f"JSON merge workspace-roots: A={ws_a} B={ws_b} merged={ws_m}")
            if apply:
                backup = icloud_json.with_name(icloud_json.name + f".pre-merge-{ts}.bak")
                shutil.copy2(icloud_json, backup)
                with open(icloud_json, "w") as f:
                    json.dump(merged, f, indent=2, ensure_ascii=False)
                messages.append(f"JSON backup: {backup.name}")

        # 08: SQLite merge
        snap_db = self.icloud_root / "snapshots/state_5/state_5.sqlite"
        local_db = self.codex_home / "state_5.sqlite"
        if snap_db.exists() and local_db.exists() and apply:
            # Checkpoint local
            wal = local_db.with_name(local_db.name + "-wal")
            if wal.exists() and wal.stat().st_size > 0:
                subprocess.run(["sqlite3", str(local_db), "PRAGMA wal_checkpoint(TRUNCATE);"],
                               capture_output=True, text=True)
            # Schema check
            def get_ver(db):
                r = subprocess.run(["sqlite3", f"file:{db}?mode=ro",
                                    "SELECT max(version) FROM _sqlx_migrations;"],
                                   capture_output=True, text=True)
                return r.stdout.strip() if r.returncode == 0 else None
            if get_ver(snap_db) != get_ver(local_db):
                messages.append("SQLite merge ABORTED: schema mismatch")
                return messages

            # Staging + merge
            staging_dir = tempfile.mkdtemp(prefix="codex-merge-")
            staging = Path(staging_dir) / "state_5.sqlite"
            shutil.copy2(snap_db, staging)
            pre_total = int(subprocess.run(
                ["sqlite3", str(staging), "SELECT count(*) FROM threads;"],
                capture_output=True, text=True).stdout.strip())

            merge_sql = f"""
PRAGMA foreign_keys = ON;
ATTACH DATABASE '{local_db}' AS macb;
BEGIN TRANSACTION;
CREATE TEMP TABLE _macb_unique AS
  SELECT b.id FROM macb.threads b
  WHERE NOT EXISTS (SELECT 1 FROM main.threads a WHERE a.id = b.id);
CREATE TEMP TABLE _macb_wins AS
  SELECT b.id FROM macb.threads b
  JOIN main.threads a ON a.id = b.id
  WHERE b.updated_at > a.updated_at;
DELETE FROM main.threads WHERE id IN (SELECT id FROM _macb_wins);
DELETE FROM main.thread_spawn_edges WHERE child_thread_id IN (SELECT id FROM _macb_wins);
INSERT INTO main.threads SELECT * FROM macb.threads
  WHERE id IN (SELECT id FROM _macb_unique) OR id IN (SELECT id FROM _macb_wins);
INSERT OR IGNORE INTO main.thread_dynamic_tools SELECT * FROM macb.thread_dynamic_tools
  WHERE thread_id IN (SELECT id FROM _macb_unique) OR thread_id IN (SELECT id FROM _macb_wins);
INSERT OR IGNORE INTO main.thread_goals SELECT * FROM macb.thread_goals
  WHERE thread_id IN (SELECT id FROM _macb_unique) OR thread_id IN (SELECT id FROM _macb_wins);
INSERT OR IGNORE INTO main.thread_spawn_edges SELECT * FROM macb.thread_spawn_edges
  WHERE child_thread_id IN (SELECT id FROM _macb_unique) OR child_thread_id IN (SELECT id FROM _macb_wins);
COMMIT;
DETACH DATABASE macb;
"""
            result = subprocess.run(["sqlite3", str(staging)], input=merge_sql,
                                    capture_output=True, text=True)
            if result.returncode != 0:
                shutil.rmtree(staging_dir)
                messages.append(f"SQLite merge FAILED: {result.stderr}")
                return messages
            post_total = int(subprocess.run(
                ["sqlite3", str(staging), "SELECT count(*) FROM threads;"],
                capture_output=True, text=True).stdout.strip())
            _, orphan = self.sqlite_orphan_check(staging)
            if orphan > 0:
                shutil.rmtree(staging_dir)
                messages.append(f"SQLite merge ABORTED: orphan={orphan}")
                return messages
            backup = snap_db.with_name(f"state_5.sqlite.pre-merge-{ts}.bak")
            shutil.copy2(snap_db, backup)
            shutil.move(str(staging), str(snap_db))
            shutil.rmtree(staging_dir, ignore_errors=True)
            messages.append(f"SQLite merge: {pre_total} → {post_total} (+{post_total - pre_total})")
            messages.append(f"SQLite backup: {backup.name}")
        elif apply:
            messages.append("SQLite merge skipped (snapshot or local DB missing)")

        return messages

    def arrive_extra(self, apply: bool, first_time: bool) -> List[str]:
        """Restore SQLite/auth/plist from iCloud snapshot."""
        messages: List[str] = []
        if not apply:
            messages.append("would restore SQLite/auth/plist from iCloud snapshot")
            messages.extend(codex_plugin_arrive_sync(self, apply=False))
            return messages
        ts = now_stamp()
        snap = self.snapshot_cfg

        # state_5
        state5 = snap.get("state5", {})
        if state5:
            local = expand(state5["local"])
            cloud = expand(state5["cloud"], self.icloud_root)
            if cloud.exists():
                if local.exists() or local.is_symlink():
                    local.rename(local.with_name(f"{local.name}.pre-icloud-{ts}"))
                    for ext in ["-wal", "-shm"]:
                        aux = local.with_name(f"{local.name}{ext}")
                        if aux.exists():
                            aux.rename(aux.with_name(f"{aux.name}.pre-icloud-{ts}"))
                shutil.copy2(cloud, local)
                threads = self.sqlite_thread_count(local)
                messages.append(f"state_5.sqlite restored ({threads} threads)")

        # codex-dev
        dev = snap.get("codexDev", {})
        if dev:
            local = expand(dev["local"])
            cloud = expand(dev["cloud"], self.icloud_root)
            if cloud.exists():
                local.parent.mkdir(parents=True, exist_ok=True)
                if local.exists():
                    local.rename(local.with_name(f"{local.name}.pre-icloud-{ts}"))
                shutil.copy2(cloud, local)
                messages.append("codex-dev.db restored")

        # auth
        for item in snap.get("auth", []):
            local = expand(item["local"])
            cloud = expand(item["cloud"], self.icloud_root)
            if cloud.exists():
                if local.exists():
                    local.rename(local.with_name(f"{local.name}.pre-icloud-{ts}"))
                shutil.copy2(cloud, local)
                h = sha256(local) or ""
                messages.append(f"auth restored: {local.name} sha256={h[:16]}…")

        # preferences
        for item in snap.get("preferences", []):
            local = expand(item["local"])
            cloud = expand(item["cloud"], self.icloud_root)
            if cloud.exists():
                if local.exists():
                    local.rename(local.with_name(f"{local.name}.pre-icloud-{ts}"))
                shutil.copy2(cloud, local)
                h = sha256(local) or ""
                messages.append(f"plist restored: {local.name} sha256={h[:16]}…")

        # v4.3: plugin/marketplace config restore — read iCloud snapshot,
        # union-merge with this Mac's local config.toml, write back. Plugin
        # source code is not touched; Codex's startup_sync rebuilds it.
        messages.extend(codex_plugin_arrive_sync(self, apply=True))

        return messages


# ---------------------------------------------------------------------------
# AgentSyncDoctor — multi-product orchestrator
# ---------------------------------------------------------------------------

def load_doctor(product: str, manifest_path: Optional[Path] = None,
                quiet: bool = False) -> ProductDoctor:
    if product == "claude":
        path = manifest_path or DEFAULT_CLAUDE_MANIFEST
        return ClaudeProductDoctor(path, quiet=quiet)
    elif product == "codex":
        path = manifest_path or DEFAULT_CODEX_MANIFEST
        return CodexProductDoctor(path, quiet=quiet)
    else:
        raise SystemExit(f"Unknown product: {product}")


def print_header(doctor: ProductDoctor) -> None:
    print(f"product:  {doctor.product}")
    print(f"manifest: {doctor.manifest_path}")
    print(f"iCloud:   {doctor.icloud_root}")
    print(f"state:    {doctor.state_path}")


# ---------------------------------------------------------------------------
# Handoff / leave / arrive orchestration
# ---------------------------------------------------------------------------

def run_handoff(doctor: ProductDoctor, apply: bool, yes: bool,
                force: bool, update_state: bool,
                ignore_conflicts: bool = False) -> int:
    """Ported directly from claude_sync_doctor.py handoff(), with v4 phase-2
    integrity-conflict blocker: iCloud conflict residues (e.g. `* N` numbered
    copies, `*.conflict-*` files) halt the handoff unless ignore_conflicts is
    set. Rationale: each conflict file is evidence that a prior multi-writer
    race was resolved by dropping somebody's data; proceeding without review
    risks repeating it (see ISSUES-2026-05-13 incident)."""
    print_header(doctor)
    running, processes = doctor.is_running()
    print(f"{doctor.product} running: {running}")
    if running:
        print("running process sample:")
        for line in processes[:5]:
            print(f"  {line}")

    print("\n== Current check ==")
    current = doctor.check(update_state=False)
    current_bad = doctor.print_results(current, include_ok=False)
    orphan = doctor.desktop_orphan_check()
    visibility = doctor.desktop_visibility_check()
    icloud = doctor.icloud_upload_check()
    print(f"desktop orphan count: {orphan.get('orphanCount', 'n/a')}")
    print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
    print(f"iCloud current pending count: {icloud.get('currentPendingCount', 'n/a')}")
    print(f"iCloud placeholder count: {icloud.get('placeholderCount', 'n/a')}")
    print(f"iCloud trash pending count: {icloud.get('trashPendingCount', 'n/a')}")
    if icloud.get("datalessCompanionAvailable"):
        print(f"iCloud dataless count: {icloud.get('datalessCount')}")
    else:
        print("iCloud dataless count: n/a (install icloud-materialization-doctor to enable)")
    print(f"problem entries: {current_bad}")

    # v4-phase2: Integrity pre-check. Phantom-activity warnings are still
    # informational, but iCloud conflict residues now BLOCK the handoff
    # unless ignore_conflicts is set (matching the ISSUES-2026-05-13 lesson:
    # 5/7 incident was a conflict-file nobody noticed).
    print("\n== Integrity pre-check ==")
    pre_integrity = print_integrity_summary(doctor, gap_minutes=30)
    pre_si = (pre_integrity.get("integrity") or {}).get("summaryWarnings") or []
    pre_conf = (pre_integrity.get("conflicts") or {}).get("total") or 0
    if pre_si:
        print("  note: session-integrity warnings are informational only; they do NOT block handoff.")
    if pre_conf > 0:
        if ignore_conflicts:
            print(f"  note: {pre_conf} iCloud conflict residues present, "
                  "but --ignore-conflicts is set — continuing anyway.")
        else:
            print(f"\n  BLOCKER: {pre_conf} iCloud conflict residues detected.")
            print("  These are artifacts of past multi-writer races. Proceeding "
                  "risks repeating the 5/7 incident (silent 14 plugin-entry drop).")
            print("  To fix: inspect via `scan-conflicts`, then `clean-conflicts --apply` "
                  "to remove them safely.")
            print("  To ignore (you accept the risk): re-run with --ignore-conflicts.")
            return 1

    print("\n== Proposed repair ==")
    proposed = doctor.repair(safe=not force, apply=False, force=force, update_state=False)
    proposed_bad = doctor.print_results(proposed, include_ok=False)
    if proposed_bad == 0:
        print("No repair actions are needed.")

    if not apply and not yes:
        print("\nDry run only. Re-run with --apply or --yes --force to make changes.")
        return 0

    do_force = force
    if running and not force and not yes:
        choice = input("\nProcess running. [f]orce / [s]afe / [a]bort: ").strip().lower()
        if choice == "f":
            do_force = True
        elif choice == "s":
            do_force = False
        else:
            print("Aborted.")
            return 1
    elif not yes:
        choice = input("\nApply these repairs now? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Aborted.")
            return 1

    print("\n== Applying repair ==")
    applied = doctor.repair(safe=not do_force, apply=True, force=do_force, update_state=update_state)
    doctor.print_results(applied, include_ok=False)
    dv = doctor.desktop_visibility_repair(apply=True)
    for action in dv.get("actions", []):
        print(f"desktop action: {action['action']}: {action['source']} -> {action['target']}")

    print("\n== Final check ==")
    final = doctor.check(update_state=update_state)
    final_bad = doctor.print_results(final, include_ok=False)
    final_orphan = doctor.desktop_orphan_check()
    final_visibility = doctor.desktop_visibility_check()
    final_icloud = doctor.icloud_upload_check()
    print(f"desktop orphan count: {final_orphan.get('orphanCount', 'n/a')}")
    print(f"desktop visible missing count: {final_visibility.get('missingVisibleCount', 'n/a')}")
    print(f"iCloud current pending count: {final_icloud.get('currentPendingCount', 'n/a')}")
    print(f"iCloud placeholder count: {final_icloud.get('placeholderCount', 'n/a')}")
    print(f"iCloud trash pending count: {final_icloud.get('trashPendingCount', 'n/a')}")
    if final_icloud.get("datalessCompanionAvailable"):
        print(f"iCloud dataless count: {final_icloud.get('datalessCount')}")
    print(f"problem entries: {final_bad}")

    if (final_bad == 0 and final_orphan.get("orphanCount", 0) == 0
            and final_visibility.get("missingVisibleCount", 0) == 0
            and final_icloud.get("ready") is True):
        print("\nHANDOFF_READY")
        return 0
    # Surface the most actionable failure reason (matching run_arrive's style).
    dl_count = final_icloud.get("datalessCount") or 0
    if final_icloud.get("datalessCompanionAvailable") and dl_count > 0:
        script = _find_icloud_materialization_script()
        hint = f"python3 {script} fix --force-read" if script else \
            "install icloud-materialization-doctor, then: <script> fix --force-read"
        print(f"\nHANDOFF_NOT_READY: {dl_count} File-Provider dataless files — "
              "local bytes missing (materialize them before leaving).")
        print(f"  remediate: {hint}")
        for s in (final_icloud.get("datalessSamples") or [])[:3]:
            print(f"    sample: {s}")
    else:
        print("\nHANDOFF_NOT_READY: inspect remaining entries before switching.")
    return 1


def run_leave(doctors: List[ProductDoctor], yes: bool, force: bool,
              ignore_conflicts: bool = False) -> int:
    """Unified leave: per-product handoff-equivalent + snapshot."""
    all_ok = True
    for d in doctors:
        print(f"\n======== {d.product} ========")
        rc = run_handoff(d, apply=yes, yes=yes, force=force, update_state=True,
                         ignore_conflicts=ignore_conflicts)
        if rc != 0:
            all_ok = False
        # Product-specific leave extras (Codex: snapshot SQLite/auth/plist)
        extras = d.leave_extra(apply=yes)
        for m in extras:
            print(f"  {m}")
    print("\n========")
    if all_ok:
        print("AGENT_SYNC_READY (leave)")
        return 0
    print("AGENT_SYNC_NOT_READY (leave)")
    return 2


def run_arrive(doctors: List[ProductDoctor], yes: bool) -> int:
    """Unified arrive: iCloud drain check + first-time/restore + repair."""
    all_ok = True
    for d in doctors:
        print(f"\n======== {d.product} ========")
        print_header(d)
        # 1. iCloud download complete?
        icloud = d.icloud_upload_check()
        print(f"iCloud placeholder count: {icloud.get('placeholderCount', 'n/a')}")
        if icloud.get("placeholderCount", 0) > 0:
            print(f"NOT READY: {icloud['placeholderCount']} .icloud placeholders — download incomplete")
            all_ok = False
            continue
        # 1b. File-Provider dataless check (macOS 12+): files with correct
        # metadata but zero physical bytes. Invisible to placeholder check.
        if icloud.get("datalessCompanionAvailable"):
            dl_count = icloud.get("datalessCount") or 0
            print(f"iCloud dataless count: {dl_count}")
            if dl_count > 0:
                script = _find_icloud_materialization_script()
                hint = f"python3 {script} fix --force-read" if script else \
                    "install icloud-materialization-doctor, then: <script> fix --force-read"
                print(f"NOT READY: {dl_count} File-Provider dataless files — local bytes missing")
                print(f"  remediate: {hint}")
                samples = icloud.get("datalessSamples") or []
                for s in samples[:3]:
                    print(f"    sample: {s}")
                all_ok = False
                continue
        else:
            print("iCloud dataless check: SKIPPED (icloud-materialization-doctor not installed)")
        # 2. First-time detection
        first_time = d.is_first_time()
        print(f"first-time onboarding: {first_time}")
        # 3. Process check
        running, processes = d.is_running()
        if running and yes:
            print(f"ERROR: {d.product} processes running")
            for p in processes[:3]:
                print(f"  {p}")
            all_ok = False
            continue
        # 4. First-time merge (Codex only)
        if first_time:
            extras = d.arrive_first_time(apply=yes)
            for m in extras:
                print(f"  {m}")
        # 5. Repair symlinks (manifest-driven)
        print("\n-- repair symlinks --")
        applied = d.repair(safe=True, apply=yes, force=False, update_state=yes)
        d.print_results(applied, include_ok=False)
        # 6. Restore SQLite/auth/plist (Codex only)
        extras = d.arrive_extra(apply=yes, first_time=first_time)
        for m in extras:
            print(f"  {m}")
        # 7. Desktop repair
        dv = d.desktop_visibility_repair(apply=yes)
        for action in dv.get("actions", []):
            print(f"  desktop action: {action['action']}: {action['source']} -> {action['target']}")
        # 8. Verify
        print("\n-- verification --")
        final = d.check(update_state=yes)
        final_bad = d.print_results(final, include_ok=False)
        if final_bad > 0:
            all_ok = False
        # v4-phase2: post-arrive integrity check. Arrive's merges / restores
        # can themselves produce conflicts (e.g. if two Macs both pushed state
        # into iCloud). Surface any that appeared so the user reviews them
        # before the next leave gets blocked by the pre-check.
        print("\n-- post-arrive integrity --")
        post = scan_icloud_conflicts(d)
        post_total = (post or {}).get("total", 0) if post.get("available") else 0
        if post_total > 0:
            print(f"NOTE: {post_total} iCloud conflict residues are now present.")
            print("  (These won't block this arrive, but future leaves will be "
                  "blocked until resolved.)")
            print("  Run `scan-conflicts` for details or `clean-conflicts --apply` to remove.")
            for f in post.get("findings", [])[:3]:
                mt = dt.datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M")
                path = f["path"]
                if len(path) > 90:
                    path = "…" + path[-89:]
                print(f"    [{mt}] ({f.get('pattern','?')}) {path}")
            if post_total > 3:
                print(f"    ... ({post_total-3} more)")
        else:
            print("iCloud conflicts: 0")
    print("\n========")
    if all_ok:
        print("AGENT_SYNC_READY (arrive)")
        return 0
    print("AGENT_SYNC_NOT_READY (arrive)")
    return 2


# ---------------------------------------------------------------------------
# Codex integrity checks (added 2026-05-13 after data-loss incident)
# ---------------------------------------------------------------------------
#
# These are read-only audits that surface sync-health issues the topology-level
# `check` can't see. Motivated by the 2026-05-13 incident where:
#   - state_5.threads.updated_at_ms disagreed with the jsonl last-line timestamp
#     by 4h40min, making "data loss" look real when it was actually a Codex
#     close-time heartbeat after an interrupted turn (see ISSUES-*.md).
#   - An old config.toml iCloud conflict file had silently dropped 14 plugin
#     enable entries on 2026-05-07 and nothing alerted on it.

def _decode_uuid7_ms(u: Optional[str]) -> Optional[int]:
    """Decode UUIDv7's first 48 bits as epoch milliseconds.
    Returns None if `u` is not a valid UUIDv7 (wrong version nibble, too short, etc).
    """
    if not u:
        return None
    try:
        hex_str = u.replace("-", "")
        if len(hex_str) < 16 or hex_str[12].lower() != "7":
            return None
        return int(hex_str[:12], 16)
    except Exception:
        return None


def _jsonl_last_ts_ms(path: Path) -> Optional[int]:
    """Extract the last JSON line's `timestamp` (or `created_at`) field from a
    rollout jsonl and return its epoch-ms value. Reads only the file's tail to
    avoid loading multi-MB jsonls.
    """
    if not path or not path.exists():
        return None
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - 8192))
            tail = f.read()
        for raw in reversed(tail.splitlines()):
            line = raw.strip()
            if not line:
                continue
            try:
                d = json.loads(line.decode("utf-8", errors="replace"))
            except Exception:
                continue
            ts = d.get("timestamp") or d.get("created_at")
            if not ts:
                continue
            try:
                if isinstance(ts, str):
                    s = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
                    obj = dt.datetime.fromisoformat(s)
                    if obj.tzinfo is None:
                        obj = obj.replace(tzinfo=dt.timezone.utc)
                    return int(obj.timestamp() * 1000)
                if isinstance(ts, (int, float)):
                    return int(ts * 1000) if ts < 1e12 else int(ts)
            except Exception:
                return None
        return None
    except Exception:
        return None


def codex_session_integrity(doctor: "ProductDoctor", gap_ms: int = 5 * 60 * 1000) -> Dict[str, Any]:
    """For each thread in state_5.threads, cross-check `updated_at_ms` against
    the actual rollout jsonl's last-line timestamp. Flag threads where state_5
    is `gap_ms` newer than the jsonl — a signature of either (a) UI heartbeat
    bumps with no content (benign), (b) in-memory writes never flushed (data
    loss), or (c) iCloud sync dropping late writes (sync failure).

    Distinguishing (a) from (b)/(c) requires looking at `latestTurnStatus` from
    Codex Desktop's Electron log — we don't have access to that here, so we
    surface all three as warnings for the caller to triage.
    """
    result: Dict[str, Any] = {
        "available": False,
        "total": 0,
        "warnings": [],
        "gapThresholdMs": gap_ms,
    }
    if doctor.product != "codex":
        result["reason"] = "codex-only check"
        return result
    db = doctor.codex_home / "state_5.sqlite"
    if not db.exists():
        result["reason"] = f"state_5.sqlite not found at {db}"
        return result
    result["available"] = True
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = list(con.execute(
            "SELECT id, rollout_path, updated_at_ms, created_at_ms, tokens_used, title, archived "
            "FROM threads ORDER BY updated_at_ms DESC"
        ))
        con.close()
    except Exception as e:
        result["reason"] = f"sqlite read failed: {e}"
        return result
    result["total"] = len(rows)
    warnings: List[Dict[str, Any]] = []
    for r in rows:
        tid = r["id"]
        rp_str = r["rollout_path"]
        rp = Path(rp_str) if rp_str else None
        upd_ms = int(r["updated_at_ms"]) if r["updated_at_ms"] else 0
        last_ts_ms = _jsonl_last_ts_ms(rp) if rp else None
        warning = None
        if rp is None:
            warning = "rollout_path missing in state_5"
        elif not rp.exists():
            warning = "rollout jsonl file missing on disk"
        elif last_ts_ms is None:
            warning = "rollout jsonl unparseable (empty or corrupt last line)"
        else:
            delta = upd_ms - last_ts_ms
            if delta > gap_ms:
                gap_minutes = delta // 60000
                warning = f"phantom activity: state_5 updated_at is {gap_minutes}min newer than jsonl last-line ts"
        if warning:
            # Severity: phantom activity on a tokens_used>0 thread is the
            # dangerous case (possible real data loss). Empty sessions whose
            # jsonl is unparseable because nothing ever got written are noise.
            if warning.startswith("phantom activity"):
                severity = 0
            elif warning.startswith("rollout jsonl file missing"):
                severity = 1
            elif warning.startswith("rollout_path missing"):
                severity = 2
            else:  # unparseable
                severity = 3 if (r["tokens_used"] or 0) > 0 else 4
            warnings.append({
                "thread_id": tid,
                "title": (r["title"] or "").split("\n", 1)[0][:80],
                "rollout_path": str(rp) if rp else None,
                "state5_updated_at_ms": upd_ms,
                "jsonl_last_ts_ms": last_ts_ms,
                "gap_ms": (upd_ms - last_ts_ms) if last_ts_ms is not None else None,
                "tokens_used": r["tokens_used"],
                "archived": bool(r["archived"]) if r["archived"] is not None else None,
                "uuid7_created_ms": _decode_uuid7_ms(tid),
                "warning": warning,
                "severity": severity,
            })
    # Sort: most-severe first, then largest-gap first within same severity.
    warnings.sort(key=lambda w: (w["severity"], -(w.get("gap_ms") or 0)))
    result["warnings"] = warnings
    return result


# Filename patterns signalling iCloud conflict resolution artifacts or other
# multi-writer races. Each pattern is a compiled regex applied against the
# basename.
_CONFLICT_PATTERNS = [
    (re.compile(r"\.conflict-"), "doctor-conflict"),                     # *.conflict-<host>-<ts>
    (re.compile(r" \d+\.[^/]+$"), "macos-icloud-numbered"),              # "foo 2.json" / "bar 12.txt"
    (re.compile(r"(?i) copy(?: \d+)?\.[^/]+$"), "macos-finder-copy"),    # "foo copy.txt" / "foo copy 2.txt"
    (re.compile(r"(?i)\(conflicted copy\)"), "conflicted-copy-office"),  # office-style conflicted copy
]


def scan_icloud_conflicts(doctor: "ProductDoctor") -> Dict[str, Any]:
    """Recursively scan the product's iCloud root for files whose names match
    known conflict-like patterns (doctor's own *.conflict-*, macOS iCloud's
    " N" numbered suffix, " copy" suffix, and Office-style "(conflicted copy)").

    Each hit is a multi-writer race fingerprint that the topology-level `check`
    silently ignores. Presence of any hit is a signal to pause handoff and
    investigate which writer was the loser.
    """
    result: Dict[str, Any] = {
        "available": False,
        "scannedRoot": str(doctor.icloud_root),
        "total": 0,
        "findings": [],
    }
    root = doctor.icloud_root
    if not root.exists():
        result["reason"] = f"iCloud root not found: {root}"
        return result
    result["available"] = True
    findings: List[Dict[str, Any]] = []
    try:
        for p in root.rglob("*"):
            try:
                if not p.is_file():
                    continue
                name = p.name
                matched_label = None
                for pat, label in _CONFLICT_PATTERNS:
                    if pat.search(name):
                        matched_label = label
                        break
                if matched_label is None:
                    continue
                st = p.stat()
                findings.append({
                    "path": str(p),
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "pattern": matched_label,
                })
            except (OSError, PermissionError):
                continue
    except Exception as e:
        result["reason"] = f"rglob failed: {e}"
        return result
    findings.sort(key=lambda x: x["mtime"], reverse=True)
    result["findings"] = findings
    result["total"] = len(findings)
    return result


def _canonical_version_path(p: Path, pattern_label: str) -> Optional[Path]:
    """Given a conflict file path + the pattern_label returned by
    scan-conflicts, compute what the canonical (non-conflicted) counterpart
    should be. Returns None if we can't infer a canonical name (in which case
    clean-conflicts will skip the file — don't delete files whose "supposed
    original" we don't know).
    """
    name = p.name
    if pattern_label == "macos-icloud-numbered":
        # "foo 2.txt" → "foo.txt" ;  "foo 12.tar.gz" → "foo.tar.gz"
        m = re.match(r"^(.+) \d+(\.[^/]+)$", name)
        if m:
            return p.with_name(m.group(1) + m.group(2))
    elif pattern_label == "macos-finder-copy":
        # "foo copy.txt" / "foo copy 2.txt"  →  "foo.txt"
        m = re.match(r"^(.+) copy(?: \d+)?(\.[^/]+)$", name, re.IGNORECASE)
        if m:
            return p.with_name(m.group(1) + m.group(2))
    elif pattern_label == "doctor-conflict":
        # "foo.conflict-host-ts"  →  "foo"
        m = re.match(r"^(.+)\.conflict-.*$", name)
        if m:
            return p.with_name(m.group(1))
    elif pattern_label == "conflicted-copy-office":
        # "foo (conflicted copy).txt"  →  "foo.txt"
        canon = re.sub(r"\s*\(conflicted copy[^)]*\)", "", name, flags=re.IGNORECASE)
        if canon != name:
            return p.with_name(canon)
    return None


def clean_icloud_conflicts(doctor: "ProductDoctor", apply: bool,
                           under_prefix: Optional[str] = None) -> Dict[str, Any]:
    """Remove iCloud conflict residues discovered by scan_icloud_conflicts.
    Dry-run unless apply=True.

    Safety gates (all checked per-file):
    1. Must match a known conflict pattern (inherited from scan-conflicts).
    2. Must have an inferable canonical counterpart (via _canonical_version_path).
       If not, skip — the "original file we're protecting" is unknown.
    3. Canonical must actually exist on disk. If not, skip — something odd is
       going on (maybe the "conflict" file IS the only remaining version, so
       deletion would lose data).
    4. On apply, use unlink() which fails fast on permission / locked files.
    """
    scan = scan_icloud_conflicts(doctor)
    result: Dict[str, Any] = {
        "available": scan.get("available", False),
        "scannedRoot": scan.get("scannedRoot"),
        "underPrefix": under_prefix,
        "applied": apply,
        "actions": [],
    }
    if not scan.get("available"):
        result["reason"] = scan.get("reason")
        return result
    findings = list(scan.get("findings", []))
    if under_prefix:
        if not under_prefix.startswith("/"):
            under_prefix = str(doctor.icloud_root / under_prefix)
        findings = [f for f in findings if f["path"].startswith(under_prefix)]
    for f in findings:
        path = Path(f["path"])
        label = f.get("pattern", "?")
        canonical = _canonical_version_path(path, label)
        action: Dict[str, Any] = {
            "path": str(path),
            "pattern": label,
            "size": f.get("size"),
        }
        if canonical is None:
            action["status"] = "skip"
            action["reason"] = "no canonical inferable for this pattern"
        else:
            action["canonical"] = str(canonical)
            if not canonical.exists():
                action["status"] = "skip"
                action["reason"] = (f"canonical '{canonical.name}' does not exist; "
                                    "refusing to delete possibly-unique copy")
            elif apply:
                try:
                    path.unlink()
                    action["status"] = "removed"
                except Exception as e:
                    action["status"] = "error"
                    action["error"] = str(e)
            else:
                action["status"] = "would-remove"
        result["actions"].append(action)
    result["removedCount"] = sum(1 for a in result["actions"] if a["status"] == "removed")
    result["wouldRemoveCount"] = sum(1 for a in result["actions"] if a["status"] == "would-remove")
    result["skippedCount"] = sum(1 for a in result["actions"] if a["status"] == "skip")
    result["errorCount"] = sum(1 for a in result["actions"] if a["status"] == "error")
    return result


def _ms_to_bj_str(ms: Optional[int]) -> str:
    """Format epoch-ms as Beijing-time (UTC+8) ISO string, or '?' if None."""
    if not ms:
        return "?"
    try:
        obj = dt.datetime.utcfromtimestamp(ms / 1000) + dt.timedelta(hours=8)
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "?"


def print_integrity_summary(doctor: "ProductDoctor", gap_minutes: int = 30) -> Dict[str, Any]:
    """Print a concise integrity summary (session-integrity + scan-conflicts) and
    return the raw result objects so callers can decide on blocking semantics.

    Shared between `check` subcommand and `run_handoff` / `run_leave` so both
    surface the same quality signal. All output is read-only — this function
    never modifies files.
    """
    result: Dict[str, Any] = {"integrity": None, "conflicts": None}
    if doctor.product == "codex":
        integrity = codex_session_integrity(doctor, gap_ms=gap_minutes * 60 * 1000)
        if integrity.get("available"):
            sw = [w for w in integrity.get("warnings", [])
                  if not w.get("archived") and w.get("severity", 99) <= 2]
            integrity["summaryWarnings"] = sw
            print(f"session integrity: {len(sw)} warnings "
                  f"(gap > {gap_minutes}min, non-archived, content-bearing)")
            for w in sw[:3]:
                tid_short = (w.get("thread_id") or "")[:8]
                gap_m = (w.get("gap_ms") or 0) // 60000
                print(f"  [{tid_short}…] {w.get('warning')}  (gap={gap_m}min)")
            if len(sw) > 3:
                print(f"  ... ({len(sw)-3} more, run `session-integrity` for full list)")
        result["integrity"] = integrity
    conflicts = scan_icloud_conflicts(doctor)
    if conflicts.get("available"):
        total_c = conflicts.get("total", 0)
        print(f"iCloud conflicts: {total_c}")
        for f in conflicts.get("findings", [])[:3]:
            mt = dt.datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M")
            pat = f.get("pattern", "?")
            path = f["path"]
            if len(path) > 90:
                path = "…" + path[-89:]
            print(f"  [{mt}] ({pat}) {path}")
        if total_c > 3:
            print(f"  ... ({total_c-3} more, run `scan-conflicts` for full list)")
    result["conflicts"] = conflicts
    return result


# ---------------------------------------------------------------------------
# Codex plugin config sync (v4 phase 3, 2026-05-14)
# ---------------------------------------------------------------------------
#
# Background: Codex's [plugins.*] enabled list and [marketplaces.*] config in
# ~/.codex/config.toml are the ONLY plugin state that needs cross-Mac sync.
# The plugin sources themselves (~/.codex/plugins/cache/, ~/.codex/.tmp/*) are
# per-machine cache that Codex auto-rebuilds on startup. So this module only
# touches config.toml's plugin/marketplace sections.
#
# Why surgical text editing instead of full TOML round-trip:
# - Python 3.9 (the user's `python3`) lacks `tomllib` (3.11+) and tomli_w isn't
#   stdlib at all. Full round-trip would require vendoring deps or installing.
# - We only need to modify [plugins.*] and [marketplaces.*]. Everything else
#   (model, projects, shell_environment_policy, [[skills.config]]) we want to
#   preserve byte-for-byte. Surgical regex-based edit is the right tool.
# - Plugin/marketplace sections in Codex config.toml use a tiny TOML subset:
#   `key = "string"`, `key = true/false`, `key = N` (int), and string lists.
#   No nested tables, no inline tables, no datetime types (all stored as ISO
#   strings).

# Match a complete [plugins.<id>] or [marketplaces.<id>] block: header line +
# its body lines until next blank line or next section header.
# - id may be quoted ("documents@openai-primary-runtime") or bare (claude-hud).
_CODEX_PLUGIN_SECTION_RE = re.compile(
    r'^\[(plugins|marketplaces)\.([^\]]+)\]\n((?:[^\[\n].*\n?)*)',
    re.MULTILINE,
)


def _parse_codex_toml_value(s: str) -> Any:
    """Parse a TOML rhs value used in plugin/marketplace sections.
    Handles: string, bool, int, list-of-strings. No floats, no nested tables,
    no inline tables, no datetime."""
    s = s.strip()
    if s == "true":
        return True
    if s == "false":
        return False
    # Quoted string. Codex doesn't use escapes in plugin/marketplace fields,
    # so naive strip-quotes is safe here.
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    # List of strings: [ "a", "b" ] or ["a","b"]
    if s.startswith("[") and s.endswith("]"):
        return re.findall(r'"((?:[^"\\]|\\.)*)"', s)
    # Integer
    try:
        return int(s)
    except ValueError:
        pass
    return s  # fallback: keep as raw string


def _format_codex_toml_value(v: Any) -> str:
    """Inverse of _parse_codex_toml_value. Used to emit a value for a
    [plugins.<id>] / [marketplaces.<id>] field."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        # Quote and escape backslash + quote conservatively. Codex paths can
        # contain spaces but never embedded quotes, so this is safe.
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, list):
        items = ", ".join(_format_codex_toml_value(x) for x in v)
        return f"[{items}]"
    raise ValueError(f"unsupported TOML value type for codex config: {type(v)}")


def _parse_section_body(body: str) -> Dict[str, Any]:
    """Parse the body of a single [plugins.x] / [marketplaces.x] section into
    {field_name: value}. Ignores blank lines and full-line comments."""
    out: Dict[str, Any] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue  # skip malformed lines defensively
        key, _, val = stripped.partition("=")
        out[key.strip()] = _parse_codex_toml_value(val)
    return out


def _format_section_id(section_id: str) -> str:
    """Re-emit a section id as it should appear inside [plugins.<here>].
    If the id contains '.' or '@' or whitespace, it must be quoted; otherwise
    bare is fine."""
    if any(ch in section_id for ch in '.@" \t/'):
        return f'"{section_id}"'
    return section_id


def extract_codex_plugin_config(toml_text: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Read all [plugins.*] and [marketplaces.*] sections from the full TOML
    text. Returns:
        {
          "plugins":      {"documents@openai-primary-runtime": {"enabled": True}, ...},
          "marketplaces": {"openai-bundled": {"source_type": "local", ...}, ...},
        }
    """
    extracted: Dict[str, Dict[str, Dict[str, Any]]] = {"plugins": {}, "marketplaces": {}}
    for m in _CODEX_PLUGIN_SECTION_RE.finditer(toml_text):
        section_type = m.group(1)
        raw_id = m.group(2)
        body = m.group(3)
        # raw_id may be quoted: "documents@openai-primary-runtime"
        if raw_id.startswith('"') and raw_id.endswith('"'):
            section_id = raw_id[1:-1]
        else:
            section_id = raw_id
        extracted[section_type][section_id] = _parse_section_body(body)
    return extracted


def serialize_codex_plugin_sections(
    extracted: Dict[str, Dict[str, Dict[str, Any]]],
) -> str:
    """Inverse: take an extracted dict and emit it as TOML text.
    Sections are emitted alphabetically within each type for stable diff."""
    blocks: List[str] = []
    for section_type in ("marketplaces", "plugins"):
        for section_id in sorted(extracted.get(section_type, {}).keys()):
            fields = extracted[section_type][section_id]
            id_emit = _format_section_id(section_id)
            block_lines = [f"[{section_type}.{id_emit}]"]
            for k, v in fields.items():
                block_lines.append(f"{k} = {_format_codex_toml_value(v)}")
            blocks.append("\n".join(block_lines) + "\n")
    return "\n".join(blocks)


def replace_codex_plugin_sections(toml_text: str,
                                   new_extracted: Dict[str, Dict[str, Dict[str, Any]]]) -> str:
    """Replace all [plugins.*] and [marketplaces.*] blocks in toml_text with
    new content from new_extracted. Everything outside those blocks is kept
    byte-for-byte (modulo a trailing newline normalization)."""
    # Strip out all existing plugin/marketplace blocks from the source text.
    cleaned = _CODEX_PLUGIN_SECTION_RE.sub("", toml_text)
    # Collapse multiple consecutive blank lines (the regex leaves gaps).
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).rstrip()
    new_blocks = serialize_codex_plugin_sections(new_extracted)
    if new_blocks:
        return cleaned + "\n\n" + new_blocks
    return cleaned + "\n"


def union_merge_plugin_config(
    local: Dict[str, Dict[str, Dict[str, Any]]],
    cloud: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Merge two plugin configs by union semantics.

    Rules:
    - [plugins.<id>]: union by id. If both sides have the same id:
        * `enabled`: any-true wins (true OR true → true; true OR false → true;
          false OR false → false). Rationale: see migration plan §4.3 — choose
          conservatively for v4.3; revisit with timestamp-aware merge in v4.4
          if "explicit disable resurrected" complaints surface.
        * Other fields (mcp_servers.*, etc.): cloud wins. Same-id fields are
          rare; cloud-wins keeps merge deterministic.
    - [marketplaces.<name>]: union by name. All fields take-cloud (including
      `source` for source_type=local — see §1.2 of migration plan; sanity
      check at arrive will warn if local source path doesn't exist on this
      Mac, which only happens with mismatched usernames).
    - Side-only entries (in local-only or cloud-only): kept as-is."""
    merged: Dict[str, Dict[str, Dict[str, Any]]] = {"plugins": {}, "marketplaces": {}}

    # Plugins union
    plugin_ids = set(local.get("plugins", {}).keys()) | set(cloud.get("plugins", {}).keys())
    for pid in plugin_ids:
        l = local.get("plugins", {}).get(pid)
        c = cloud.get("plugins", {}).get(pid)
        if l is None:
            merged["plugins"][pid] = dict(c)
            continue
        if c is None:
            merged["plugins"][pid] = dict(l)
            continue
        # Both sides have it
        m: Dict[str, Any] = {}
        # enabled: any-true wins
        l_en = bool(l.get("enabled", False))
        c_en = bool(c.get("enabled", False))
        m["enabled"] = l_en or c_en
        # Other fields: cloud wins for fields cloud has, fall back to local
        for k, v in l.items():
            if k != "enabled":
                m[k] = v
        for k, v in c.items():
            if k != "enabled":
                m[k] = v  # cloud overrides local
        merged["plugins"][pid] = m

    # Marketplaces: take-cloud union
    mp_names = set(local.get("marketplaces", {}).keys()) | set(cloud.get("marketplaces", {}).keys())
    for name in mp_names:
        l = local.get("marketplaces", {}).get(name)
        c = cloud.get("marketplaces", {}).get(name)
        if l is None:
            merged["marketplaces"][name] = dict(c)
            continue
        if c is None:
            merged["marketplaces"][name] = dict(l)
            continue
        # take-cloud, fields cloud doesn't have fall back to local
        m = dict(l)
        m.update(c)
        merged["marketplaces"][name] = m

    return merged


def verify_local_marketplace_paths(
    extracted: Dict[str, Dict[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Sanity check: for every marketplace with source_type=local, verify
    that the `source` path actually exists on this Mac. Returns a list of
    warnings (empty list = all OK).

    Catches the "different username across Macs" or "Codex Desktop not yet
    bootstrapped on this Mac" cases. Does not modify anything."""
    warnings: List[Dict[str, Any]] = []
    for name, fields in extracted.get("marketplaces", {}).items():
        if fields.get("source_type") != "local":
            continue
        src = fields.get("source")
        if not src:
            warnings.append({
                "marketplace": name,
                "issue": "source_type=local but no source field",
                "source": None,
            })
            continue
        path = Path(src).expanduser()
        if not path.exists():
            warnings.append({
                "marketplace": name,
                "issue": "source path does not exist on this Mac",
                "source": str(path),
                "hint": (
                    "If this marketplace is bundled by Codex Desktop "
                    "(openai-bundled), launching Codex Desktop should bootstrap "
                    "it. For openai-primary-runtime, launch Codex Desktop or "
                    "run codex CLI to trigger codex-runtimes installation."
                ),
            })
    return warnings


# Path under iCloud where doctor stores the merged plugin/marketplace state.
# Lives next to the existing snapshots/ family (state_5, sqlite, preferences).
CODEX_PLUGIN_SNAPSHOT_RELPATH = "snapshots/config-toml/_merged.toml"


def codex_plugin_snapshot_path(doctor: "ProductDoctor") -> Path:
    """Resolved path to the iCloud-side merged plugin/marketplace snapshot."""
    return doctor.icloud_root / CODEX_PLUGIN_SNAPSHOT_RELPATH


def read_codex_plugin_snapshot(doctor: "ProductDoctor") -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Read iCloud's merged snapshot. Returns empty dict if missing."""
    p = codex_plugin_snapshot_path(doctor)
    if not p.exists():
        return {"plugins": {}, "marketplaces": {}}
    try:
        return extract_codex_plugin_config(p.read_text())
    except Exception:
        return {"plugins": {}, "marketplaces": {}}


def write_codex_plugin_snapshot(
    doctor: "ProductDoctor",
    extracted: Dict[str, Dict[str, Dict[str, Any]]],
) -> None:
    """Write the merged plugin/marketplace state to iCloud as a small TOML
    file. The snapshot has only [plugins.*] and [marketplaces.*] sections —
    not a full config.toml replica."""
    p = codex_plugin_snapshot_path(doctor)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = serialize_codex_plugin_sections(extracted)
    header = (
        "# Doctor-managed merged plugin & marketplace state.\n"
        "# Source of truth across Macs for [plugins.*] and [marketplaces.*].\n"
        "# Updated on every leave; consumed on every arrive (union-merged).\n"
        "# Do not edit by hand — your changes will be overwritten on next leave.\n\n"
    )
    p.write_text(header + body)


def codex_plugin_leave_sync(
    doctor: "ProductDoctor",
    apply: bool,
) -> List[str]:
    """leave-side: extract this Mac's plugin config, union-merge with iCloud
    snapshot, write merged state back to iCloud."""
    messages: List[str] = []
    config_path = doctor.codex_home / "config.toml"
    if not config_path.exists():
        messages.append("plugin sync skipped: no config.toml")
        return messages
    local = extract_codex_plugin_config(config_path.read_text())
    cloud = read_codex_plugin_snapshot(doctor)
    merged = union_merge_plugin_config(local, cloud)
    p = codex_plugin_snapshot_path(doctor)
    if not apply:
        messages.append(f"would write plugin snapshot → {p}")
        messages.append(f"  plugins: {len(merged.get('plugins', {}))} entries")
        messages.append(f"  marketplaces: {len(merged.get('marketplaces', {}))} entries")
        return messages
    write_codex_plugin_snapshot(doctor, merged)
    messages.append(f"plugin snapshot written → {p}")
    messages.append(f"  plugins: {len(merged.get('plugins', {}))} entries")
    messages.append(f"  marketplaces: {len(merged.get('marketplaces', {}))} entries")
    return messages


def codex_plugin_arrive_sync(
    doctor: "ProductDoctor",
    apply: bool,
) -> List[str]:
    """arrive-side: read iCloud snapshot, union-merge with this Mac's local
    config, write merged config back to ~/.codex/config.toml. Then run sanity
    check on local marketplace paths."""
    messages: List[str] = []
    config_path = doctor.codex_home / "config.toml"
    if not config_path.exists():
        messages.append("plugin sync skipped: no config.toml")
        return messages
    cloud = read_codex_plugin_snapshot(doctor)
    if not cloud.get("plugins") and not cloud.get("marketplaces"):
        messages.append("plugin sync skipped: no iCloud snapshot yet (first-time)")
        return messages
    original_text = config_path.read_text()
    local = extract_codex_plugin_config(original_text)
    merged = union_merge_plugin_config(local, cloud)
    new_text = replace_codex_plugin_sections(original_text, merged)

    if not apply:
        # In dry-run mode, summarize what would change.
        added_plugins = set(merged["plugins"].keys()) - set(local["plugins"].keys())
        added_mp = set(merged["marketplaces"].keys()) - set(local["marketplaces"].keys())
        messages.append(f"would update {config_path}")
        messages.append(f"  plugins: local={len(local['plugins'])} cloud={len(cloud['plugins'])} merged={len(merged['plugins'])}")
        if added_plugins:
            messages.append(f"  new plugins to enable: {sorted(added_plugins)[:5]}{' ...' if len(added_plugins) > 5 else ''}")
        messages.append(f"  marketplaces: local={len(local['marketplaces'])} cloud={len(cloud['marketplaces'])} merged={len(merged['marketplaces'])}")
        if added_mp:
            messages.append(f"  new marketplaces: {sorted(added_mp)}")
        return messages

    # Apply: backup original, write merged
    ts = now_stamp()
    backup_path = config_path.with_name(f"{config_path.name}.pre-arrive-{ts}.bak")
    shutil.copy2(config_path, backup_path)
    config_path.write_text(new_text)
    messages.append(f"updated {config_path}")
    messages.append(f"  backup: {backup_path}")
    messages.append(f"  plugins: {len(merged['plugins'])} entries")
    messages.append(f"  marketplaces: {len(merged['marketplaces'])} entries")

    # Sanity check
    warnings = verify_local_marketplace_paths(merged)
    if warnings:
        messages.append(f"sanity check: {len(warnings)} local marketplace path(s) missing on this Mac:")
        for w in warnings:
            messages.append(f"  ⚠ [marketplaces.{w['marketplace']}] {w['issue']}")
            if w.get("source"):
                messages.append(f"      source: {w['source']}")
            if w.get("hint"):
                messages.append(f"      hint: {w['hint']}")
    else:
        messages.append("sanity check: all source_type=local marketplace paths exist ✓")

    return messages


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Sync Doctor (Claude + Codex unified)")
    parser.add_argument("--products", default="claude,codex",
                        help="Comma-separated: claude,codex (default: both)")
    parser.add_argument("--manifest", help="Override manifest path (only with single --products)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--quiet", action="store_true", help="suppress OK entries")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Unified V2 commands
    pl = sub.add_parser("leave", help="离开当前电脑前：check + repair + snapshot + iCloud drain")
    pl.add_argument("--yes", action="store_true", help="非交互执行")
    pl.add_argument("--force", action="store_true", help="允许在进程运行时 relink")
    pl.add_argument("--ignore-conflicts", action="store_true",
                    help="即使发现 iCloud conflict 残骸也继续 handoff（接受风险）")

    pa = sub.add_parser("arrive", help="到达新电脑：首次检测 + merge + restore + repair")
    pa.add_argument("--yes", action="store_true", help="非交互执行")

    # Legacy per-product commands (preserved for compatibility with claude-sync-doctor)
    p_check = sub.add_parser("check", help="只读检查")
    p_check.add_argument("--update-state", action="store_true")
    p_check.add_argument("--no-integrity", action="store_true",
                         help="跳过 session-integrity / scan-conflicts 的默认摘要（纯 topology 检查）")
    p_check.add_argument("--integrity-gap-minutes", type=int, default=30,
                         help="check 默认跑的 session-integrity 阈值，默认 30min")
    p_deep = sub.add_parser("deep-check", help="本地 vs 云端目录 diff")
    p_repair = sub.add_parser("repair", help="修 symlink drift")
    p_repair.add_argument("--safe", action="store_true", default=True)
    p_repair.add_argument("--force", action="store_true")
    p_repair.add_argument("--apply", action="store_true")
    p_repair.add_argument("--dry-run", action="store_true")
    p_repair.add_argument("--update-state", action="store_true")
    p_state = sub.add_parser("state", help="打印 state ledger")
    p_launch = sub.add_parser("install-launchagent", help="写 LaunchAgent plist")
    p_launch.add_argument("--apply", action="store_true")
    p_launch.add_argument("--dry-run", action="store_true")
    p_launch.add_argument("--load", action="store_true")
    p_handoff = sub.add_parser("handoff", help="旧版交接流程（等价于 leave --products <single>）")
    p_handoff.add_argument("--apply", action="store_true")
    p_handoff.add_argument("--yes", action="store_true")
    p_handoff.add_argument("--force", action="store_true")
    p_handoff.add_argument("--update-state", action="store_true", default=True)
    p_handoff.add_argument("--ignore-conflicts", action="store_true",
                           help="即使发现 iCloud conflict 残骸也继续 handoff（接受风险）")
    p_icloud = sub.add_parser("icloud-check", help="brctl 上传/占位状态")
    p_dc = sub.add_parser("desktop-check", help="desktop visibility metadata")
    p_dr = sub.add_parser("desktop-repair", help="复制 desktop metadata 到当前 owner group")
    p_dr.add_argument("--apply", action="store_true")
    p_dr.add_argument("--dry-run", action="store_true")

    # V2.1 integrity checks (added 2026-05-13 after data-loss incident)
    p_si = sub.add_parser("session-integrity",
                          help="Codex: cross-check state_5.updated_at vs rollout jsonl last-ts")
    p_si.add_argument("--gap-minutes", type=int, default=5,
                      help="Flag thread if state_5 is newer than jsonl by > N minutes (default 5)")
    p_si.add_argument("--include-archived", action="store_true", default=False,
                      help="Include archived threads (default: skip)")
    p_si.add_argument("--limit", type=int, default=20,
                      help="Max warnings to print in non-JSON mode (default 20)")

    p_sc = sub.add_parser("scan-conflicts",
                          help="扫 iCloud root 里 *.conflict-* / macOS ' N' / ' copy' 冲突残留")
    p_sc.add_argument("--limit", type=int, default=40,
                      help="Max findings to print in non-JSON mode (default 40)")

    p_cc = sub.add_parser("clean-conflicts",
                          help="删除 scan-conflicts 找到的冲突残骸（默认 dry-run）")
    p_cc.add_argument("--apply", action="store_true",
                      help="真删；不加则只打印会删哪些")
    p_cc.add_argument("--under",
                      help="限制范围到 iCloud root 下的子路径（例如 dotcodex/plugins/cache）")

    args = parser.parse_args(argv)
    products = [p.strip() for p in args.products.split(",") if p.strip()]
    manifest_override = Path(args.manifest).expanduser() if args.manifest else None
    if manifest_override and len(products) > 1:
        raise SystemExit("--manifest requires a single product")

    doctors = [load_doctor(p, manifest_override, quiet=args.quiet) for p in products]

    # Unified commands
    if args.cmd == "leave":
        return run_leave(doctors, yes=args.yes, force=args.force,
                         ignore_conflicts=args.ignore_conflicts)
    if args.cmd == "arrive":
        return run_arrive(doctors, yes=args.yes)

    # Legacy commands — operate per-product
    if len(doctors) > 1 and args.cmd in {"deep-check", "repair", "state",
                                          "install-launchagent", "handoff",
                                          "desktop-check", "desktop-repair"}:
        print(f"NOTE: {args.cmd} runs per-product. Specify --products <single> to target one.")

    overall_rc = 0
    for d in doctors:
        rc = run_legacy(d, args)
        if rc != 0:
            overall_rc = rc
    return overall_rc


def run_legacy(doctor: ProductDoctor, args) -> int:
    """Handle the legacy (single-product) commands."""
    if args.cmd == "check":
        results = doctor.check(update_state=args.update_state)
        orphan = doctor.desktop_orphan_check()
        visibility = doctor.desktop_visibility_check()

        # v4-phase1: default integrity summary (opt-out via --no-integrity).
        # We compute the data up-front so both --json and text paths see it.
        integrity_data: Optional[Dict[str, Any]] = None

        if args.json:
            # For JSON we compute without printing (helper prints to stdout).
            payload: Dict[str, Any] = {"product": doctor.product, "results": results,
                                       "desktopOrphans": orphan, "desktopVisibility": visibility}
            if not args.no_integrity:
                if doctor.product == "codex":
                    payload["sessionIntegrity"] = codex_session_integrity(
                        doctor, gap_ms=args.integrity_gap_minutes * 60 * 1000)
                payload["conflicts"] = scan_icloud_conflicts(doctor)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            bad = doctor.print_results(results)
            print(f"desktop orphan count: {orphan.get('orphanCount', 'n/a')}")
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            if doctor.product == "codex":
                db = doctor.codex_home / "state_5.sqlite"
                total, codex_orphan = doctor.sqlite_orphan_check(db)
                print(f"codex threads: {total}")
                print(f"codex rollout_path orphan: {codex_orphan}")
            if not args.no_integrity:
                integrity_data = print_integrity_summary(
                    doctor, gap_minutes=args.integrity_gap_minutes)
            print(f"problem entries: {bad}")
        return 0

    if args.cmd == "deep-check":
        results = doctor.deep_check()
        if args.json:
            print(json.dumps({"product": doctor.product, "results": results},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            doctor.print_results(results)
        return 0

    if args.cmd == "repair":
        apply = bool(args.apply and not args.dry_run)
        results = doctor.repair(safe=args.safe, apply=apply, force=args.force,
                                update_state=args.update_state)
        if args.json:
            print(json.dumps({"product": doctor.product, "applied": apply, "results": results},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"mode: {'apply' if apply else 'dry-run'}")
            running, _ = doctor.is_running()
            print(f"{doctor.product} running: {running}")
            bad = doctor.print_results(results, include_ok=False)
            print(f"problem entries: {bad}")
        return 0

    if args.cmd == "state":
        print(json.dumps({"product": doctor.product, "state": doctor.state},
                         indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.cmd == "install-launchagent":
        apply = bool(args.apply and not args.dry_run)
        path = install_launchagent(doctor, apply=apply, load=args.load)
        if apply:
            print(f"wrote {path}")
            if args.load:
                print("loaded LaunchAgent")
        return 0

    if args.cmd == "handoff":
        apply = bool(args.apply or args.yes)
        return run_handoff(doctor, apply=apply, yes=args.yes, force=args.force,
                           update_state=args.update_state,
                           ignore_conflicts=args.ignore_conflicts)

    if args.cmd == "icloud-check":
        report = doctor.icloud_upload_check()
        if args.json:
            print(json.dumps({"product": doctor.product, "icloudUpload": report},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"iCloud container: {report.get('container', 'n/a')}")
            print(f"iCloud prefix: {report.get('prefix', 'n/a')}")
            print(f"iCloud current pending count: {report.get('currentPendingCount', 'n/a')}")
            print(f"iCloud placeholder count: {report.get('placeholderCount', 'n/a')}")
            print(f"iCloud trash pending count: {report.get('trashPendingCount', 'n/a')}")
            if report.get("datalessCompanionAvailable"):
                print(f"iCloud dataless count: {report.get('datalessCount')}")
                for s in (report.get("datalessSamples") or [])[:3]:
                    print(f"  dataless sample: {s}")
            else:
                print("iCloud dataless count: n/a (install icloud-materialization-doctor to enable)")
            print(f"iCloud ready: {report.get('ready', False)}")
            if not report.get("available", True):
                print(f"unavailable: {report.get('reason')}")
            for path in report.get("currentPending", [])[:20]:
                print(f"  current pending: {path}")
        return 0 if report.get("ready") is True else 1

    if args.cmd == "desktop-check":
        visibility = doctor.desktop_visibility_check()
        if args.json:
            print(json.dumps({"product": doctor.product, "desktopVisibility": visibility},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            print(f"desktop visibility orphan count: {visibility.get('orphanCount', 'n/a')}")
        return 0

    if args.cmd == "desktop-repair":
        apply = bool(args.apply and not args.dry_run)
        visibility = doctor.desktop_visibility_repair(apply=apply)
        if args.json:
            print(json.dumps({"product": doctor.product, "applied": apply,
                              "desktopVisibility": visibility},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"mode: {'apply' if apply else 'dry-run'}")
            for action in visibility.get("actions", []):
                print(f"  {action['action']}: {action['source']} -> {action['target']}")
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
        return 0

    if args.cmd == "session-integrity":
        report = codex_session_integrity(doctor, gap_ms=args.gap_minutes * 60 * 1000)
        if not args.include_archived:
            report["warnings"] = [w for w in report["warnings"] if not w.get("archived")]
        if args.json:
            print(json.dumps({"product": doctor.product, "sessionIntegrity": report},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            if not report.get("available"):
                print(f"unavailable: {report.get('reason', 'n/a')}")
                return 0
            print(f"total threads scanned: {report['total']}")
            print(f"gap threshold: {report['gapThresholdMs'] // 60000} min")
            print(f"warnings: {len(report['warnings'])} (non-archived)")
            shown = report["warnings"][:args.limit]
            for w in shown:
                gap_m = (w.get("gap_ms") or 0) // 60000
                upd_bj = _ms_to_bj_str(w.get("state5_updated_at_ms"))
                jsonl_bj = _ms_to_bj_str(w.get("jsonl_last_ts_ms"))
                created_bj = _ms_to_bj_str(w.get("uuid7_created_ms"))
                print(f"  [{w['thread_id']}] {w['warning']}")
                print(f"      title       : {w['title']}")
                print(f"      created (BJ): {created_bj}  (from UUIDv7)")
                print(f"      state_5 upd : {upd_bj}")
                print(f"      jsonl last  : {jsonl_bj}   gap: {gap_m}min")
                print(f"      tokens_used : {w.get('tokens_used')}")
            if len(report["warnings"]) > args.limit:
                print(f"  ... ({len(report['warnings']) - args.limit} more, use --json for full list)")
        return 0 if not report["warnings"] else 1

    if args.cmd == "scan-conflicts":
        report = scan_icloud_conflicts(doctor)
        if args.json:
            print(json.dumps({"product": doctor.product, "conflicts": report},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            if not report.get("available"):
                print(f"unavailable: {report.get('reason', 'n/a')}")
                return 0
            print(f"scanned root: {report['scannedRoot']}")
            print(f"conflicts found: {report['total']}")
            shown = report["findings"][:args.limit]
            for f in shown:
                mt = dt.datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  [{mt}] ({f['pattern']}) size={f['size']}  {f['path']}")
            if len(report["findings"]) > args.limit:
                print(f"  ... ({len(report['findings']) - args.limit} more, use --json for full list)")
        return 0 if report["total"] == 0 else 1

    if args.cmd == "clean-conflicts":
        rep = clean_icloud_conflicts(doctor, apply=args.apply, under_prefix=args.under)
        if args.json:
            print(json.dumps({"product": doctor.product, "cleanConflicts": rep},
                             indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            if not rep.get("available"):
                print(f"unavailable: {rep.get('reason', 'n/a')}")
                return 0
            mode = "apply (will delete)" if rep["applied"] else "dry-run (use --apply to delete)"
            print(f"mode: {mode}")
            if rep.get("underPrefix"):
                print(f"scope: {rep['underPrefix']}")
            for a in rep.get("actions", []):
                status = a["status"]
                canonical_bit = ""
                if a.get("canonical"):
                    canonical_bit = f"  canonical={Path(a['canonical']).name}"
                size_b = a.get("size", 0)
                print(f"  [{status}] ({a['pattern']}) size={size_b}  {a['path']}{canonical_bit}")
                if a.get("reason"):
                    print(f"      reason: {a['reason']}")
                if a.get("error"):
                    print(f"      error: {a['error']}")
            print(f"summary: removed={rep.get('removedCount',0)}  "
                  f"would-remove={rep.get('wouldRemoveCount',0)}  "
                  f"skipped={rep.get('skippedCount',0)}  "
                  f"errors={rep.get('errorCount',0)}")
        return 0 if rep.get("errorCount", 0) == 0 else 1

    return 2


def install_launchagent(doctor: ProductDoctor, apply: bool, load: bool) -> Path:
    label = f"com.park0er.agent-sync-doctor.{doctor.product}"
    plist_path = Path(f"~/Library/LaunchAgents/{label}.plist").expanduser()
    log_dir = Path(f"~/Library/Logs/AgentSyncDoctor/{doctor.product}").expanduser()
    program = [sys.executable, str(SCRIPT), "--products", doctor.product,
               "repair", "--safe", "--apply", "--update-state", "--quiet"]
    plist = {
        "Label": label, "ProgramArguments": program, "StartInterval": 300,
        "RunAtLoad": True,
        "StandardOutPath": str(log_dir / "doctor.out.log"),
        "StandardErrorPath": str(log_dir / "doctor.err.log"),
    }
    if apply:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        with plist_path.open("wb") as f:
            plistlib.dump(plist, f)
        if load:
            subprocess.run(["launchctl", "unload", str(plist_path)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    else:
        print(plistlib.dumps(plist).decode())
    return plist_path


if __name__ == "__main__":
    raise SystemExit(main())
