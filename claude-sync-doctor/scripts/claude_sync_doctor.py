#!/usr/bin/env python3
"""Doctor for iCloud-backed Claude/Claude Desktop symlink sync."""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import json
import os
import plistlib
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


SCRIPT = Path(__file__).resolve()
SKILL_DIR = SCRIPT.parents[1]
DEFAULT_MANIFEST = SKILL_DIR / "references" / "default_manifest.json"


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def expand(path: str, icloud_root: Optional[Path] = None) -> Path:
    if icloud_root is not None and not path.startswith("~") and not path.startswith("/"):
        return (icloud_root / path).expanduser()
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
    """Return the brctl container name and root-relative path for an iCloud item."""
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
    relative = parts[container_index + 1 :]
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
            current_path = stripped[len("Under ") :]
            continue
        if current_path and any(term in stripped for term in needles):
            pending.add(current_path)
    return pending


def is_claude_running() -> Tuple[bool, List[str]]:
    override = os.environ.get("CLAUDE_SYNC_DOCTOR_ASSUME_RUNNING")
    if override is not None:
        running = override.strip().lower() in {"1", "true", "yes", "running"}
        return running, ["CLAUDE_SYNC_DOCTOR_ASSUME_RUNNING=1"] if running else []
    patterns = [
        "Claude.app/Contents/MacOS/Claude",
        "claude-code/.*/claude",
        "Application Support/Claude-3p/claude-code",
    ]
    pids: List[str] = []
    for pattern in patterns:
        proc = subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if "claude_sync_doctor.py" not in line:
                    pids.append(line)
    dedup = sorted(set(pids))
    return bool(dedup), dedup


class Doctor:
    def __init__(self, manifest_path: Path, quiet: bool = False):
        self.manifest_path = manifest_path
        self.manifest = read_json(manifest_path, {})
        if not self.manifest:
            raise SystemExit(f"Cannot read manifest: {manifest_path}")
        self.hostname = socket.gethostname()
        self.icloud_root = expand(self.manifest["icloudRoot"])
        self.backup_root = expand(self.manifest.get("backupRoot", "~/ClaudeSyncBackups/doctor"))
        state_template = self.manifest.get(
            "statePath",
            str(self.icloud_root / ".doctor" / "state" / "{hostname}.json"),
        )
        self.state_path = expand(state_template.format(hostname=self.hostname))
        self.state = read_json(self.state_path, {"entries": {}})
        self.quiet = quiet

    def entry_paths(self, entry: Dict[str, Any]) -> Tuple[Path, Path]:
        local = expand(entry["local"])
        cloud = expand(entry["cloud"], self.icloud_root)
        return local, cloud

    def print(self, msg: str) -> None:
        if not self.quiet:
            print(msg)

    def classify(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        local, cloud = self.entry_paths(entry)
        result: Dict[str, Any] = {
            "id": entry["id"],
            "type": entry["type"],
            "local": str(local),
            "cloud": str(cloud),
            "status": "UNKNOWN",
            "details": [],
            "local": str(local),
            "cloud": str(cloud),
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
                result["deep"] = {"note": "local symlink resolves to cloud; no separate tree diff needed"}
                continue
            if local.is_dir() and cloud.is_dir():
                result["deep"] = self.diff_trees(local, cloud, limit=50)
        return results

    def diff_trees(self, local: Path, cloud: Path, limit: int = 50) -> Dict[str, Any]:
        local_files = {
            str(p.relative_to(local)): p
            for p in local.rglob("*")
            if p.is_file() and not p.name.endswith(".icloud")
        }
        cloud_files = {
            str(p.relative_to(cloud)): p
            for p in cloud.rglob("*")
            if p.is_file() and not p.name.endswith(".icloud")
        }
        only_local = sorted(set(local_files) - set(cloud_files))
        only_cloud = sorted(set(cloud_files) - set(local_files))
        changed: List[str] = []
        for rel in sorted(set(local_files) & set(cloud_files)):
            lp = local_files[rel]
            cp = cloud_files[rel]
            try:
                if lp.stat().st_size != cp.stat().st_size or not filecmp.cmp(lp, cp, shallow=False):
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

    def repair(self, safe: bool, apply: bool, force: bool, update_state: bool) -> List[Dict[str, Any]]:
        running, processes = is_claude_running()
        results: List[Dict[str, Any]] = []
        for entry in self.manifest.get("entries", []):
            result = self.classify(entry)
            result["actions"] = []
            self.repair_entry(entry, result, running=running, safe=safe, apply=apply, force=force)
            if running and result.get("actions"):
                result["claudeRunning"] = True
                result["processSample"] = processes[:5]
            results.append(result)
        if update_state and apply:
            self.update_state([self.classify(e) for e in self.manifest.get("entries", [])])
        return results

    def repair_entry(
        self,
        entry: Dict[str, Any],
        result: Dict[str, Any],
        running: bool,
        safe: bool,
        apply: bool,
        force: bool,
    ) -> None:
        local, cloud = self.entry_paths(entry)
        status = result["status"]
        if status == "OK":
            return
        if entry["type"] == "directory":
            self.repair_directory(entry, result, local, cloud, running, safe, apply, force)
            return
        self.repair_file(entry, result, local, cloud, running, safe, apply, force)

    def add_action(self, result: Dict[str, Any], text: str) -> None:
        result.setdefault("actions", []).append(text)

    def backup_path(self, entry_id: str, side: str, original: Path) -> Path:
        dest = self.backup_root / now_stamp() / entry_id / side / original.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    def copy_file_atomic(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + f".tmp.{os.getpid()}")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)

    def backup_file(self, entry_id: str, side: str, path: Path, apply: bool, result: Dict[str, Any]) -> Optional[Path]:
        if not path.exists() or not path.is_file():
            return None
        dest = self.backup_path(entry_id, side, path)
        self.add_action(result, f"backup {side}: {path} -> {dest}")
        if apply:
            shutil.copy2(path, dest)
        return dest

    def relink_file(self, local: Path, cloud: Path, apply: bool, result: Dict[str, Any]) -> None:
        self.add_action(result, f"unlink local file and symlink: {local} -> {cloud}")
        if apply:
            try:
                local.unlink()
            except FileNotFoundError:
                pass
            local.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(str(cloud), str(local))

    def repair_file(
        self,
        entry: Dict[str, Any],
        result: Dict[str, Any],
        local: Path,
        cloud: Path,
        running: bool,
        safe: bool,
        apply: bool,
        force: bool,
    ) -> None:
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
                self.add_action(result, "defer relink because Claude is running")
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
                self.add_action(result, "defer relink because Claude is running")
                return
            self.backup_file(entry_id, "local-before-relink", local, apply, result)
            self.relink_file(local, cloud, apply, result)
            return
        if status == "LOCAL_FILE_MATCHES_CLOUD_BUT_NOT_SYMLINK":
            if running and safe and not force:
                self.add_action(result, "defer relink because Claude is running")
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
                    self.add_action(result, "defer relink because Claude is running")
                    return
                self.backup_file(entry_id, "local-before-relink", local, apply, result)
                self.relink_file(local, cloud, apply, result)
            elif decision == "cloud":
                if running and safe and not force:
                    self.add_action(result, "defer relink because Claude is running")
                    return
                self.backup_file(entry_id, "local-conflicting-copy", local, apply, result)
                self.relink_file(local, cloud, apply, result)
            else:
                self.add_action(result, "conflict: no automatic overwrite")
            return
        if status == "BROKEN_SYMLINK_TARGET_MISSING":
            self.add_action(result, "cloud target missing; cannot repair without source data")

    def decide_file_winner(self, entry_id: str, local: Path, cloud: Path) -> str:
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
        # Without ledger, use mtime only if one side is clearly newer.
        if abs(local_m - cloud_m) < 2:
            return "conflict"
        return "local" if local_m > cloud_m else "cloud"

    def repair_directory(
        self,
        entry: Dict[str, Any],
        result: Dict[str, Any],
        local: Path,
        cloud: Path,
        running: bool,
        safe: bool,
        apply: bool,
        force: bool,
    ) -> None:
        status = result["status"]
        if status == "MISSING_LOCAL_CLOUD_EXISTS":
            self.add_action(result, f"create local directory symlink: {local} -> {cloud}")
            if apply:
                local.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(str(cloud), str(local))
            return
        if status == "WRONG_SYMLINK_TARGET":
            if running and safe and not force:
                self.add_action(result, "defer relink because Claude is running")
                return
            self.add_action(result, "replace wrong directory symlink target")
            if apply:
                local.unlink()
                os.symlink(str(cloud), str(local))
            return
        if status == "LOCAL_DIR_EXISTS_BUT_NOT_SYMLINK":
            self.add_action(result, "real directory exists where symlink is expected; not auto-merging directories")
            self.add_action(result, "run migration scripts or inspect deep-check output before relinking")
            return
        if status == "LOCAL_DIR_CLOUD_MISSING":
            self.add_action(result, "cloud directory missing; not auto-initializing large directory from Doctor")
            return
        if status == "BROKEN_SYMLINK_TARGET_MISSING":
            self.add_action(result, "cloud directory target missing; cannot repair symlink target")

    def update_state(self, results: List[Dict[str, Any]]) -> None:
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

    def target_desktop_group(self, sessions: Path, owner: str, create: bool = False) -> Path:
        owner_dir = sessions / owner
        groups = [p for p in owner_dir.glob("*") if p.is_dir()] if owner_dir.exists() else []
        if groups:
            groups.sort(key=lambda p: (-len(list(p.glob("local_*.json"))), p.name))
            return groups[0]
        target = owner_dir / "00000000-0000-4000-8000-000000000001"
        if create:
            target.mkdir(parents=True, exist_ok=True)
        return target

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
            existing_time = existing.get("data", {}).get("lastActivityAt", 0) if existing else -1
            if existing is None or current_time >= existing_time:
                records[session_id] = {"path": meta, "data": data}
        return records

    def desktop_visibility_check(self) -> Dict[str, Any]:
        sessions = self.find_local_path_for_entry("desktop-code-sessions")
        dotclaude = self.find_local_path_for_entry("dotclaude")
        projects_entry = self.find_local_path_for_entry("dotclaude-projects")
        projects = projects_entry or (dotclaude / "projects" if dotclaude else Path("~/.claude/projects").expanduser())
        if not sessions or not sessions.exists():
            return {"available": False, "reason": "desktop-code-sessions path missing"}
        owner = self.current_desktop_owner(sessions)
        if not owner:
            return {"available": False, "reason": "current ownerAccountId missing"}
        target_group = self.target_desktop_group(sessions, owner, create=False)
        records = self.collect_desktop_metadata(sessions)
        current_visible = set()
        owner_dir = sessions / owner
        if owner_dir.exists():
            for meta in owner_dir.glob("*/local_*.json"):
                current_visible.add(read_json(meta, {}).get("sessionId") or meta.stem)

        missing = []
        orphans = []
        for session_id, record in sorted(records.items()):
            data = record["data"]
            cli_id = data.get("cliSessionId")
            item = {
                "sessionId": session_id,
                "cliSessionId": cli_id,
                "title": data.get("title"),
                "source": str(record["path"]),
                "target": str(target_group / f"{session_id}.json"),
            }
            if not self.transcript_exists(cli_id, projects):
                orphans.append(item)
                continue
            if session_id not in current_visible:
                missing.append(item)
        return {
            "available": True,
            "currentOwner": owner,
            "targetGroup": str(target_group),
            "metadataCount": len(records),
            "visibleCount": len(current_visible),
            "orphanCount": len(orphans),
            "missingVisibleCount": len(missing),
            "missingVisible": missing[:50],
            "orphans": orphans[:50],
        }

    def desktop_visibility_repair(self, apply: bool) -> Dict[str, Any]:
        report = self.desktop_visibility_check()
        report["applied"] = apply
        report["actions"] = []
        if not report.get("available"):
            return report
        target_group = Path(report["targetGroup"])
        if apply:
            target_group.mkdir(parents=True, exist_ok=True)
        for item in report.get("missingVisible", []):
            src = Path(item["source"])
            dst = target_group / src.name
            action = {"sessionId": item["sessionId"], "source": str(src), "target": str(dst), "action": "copy"}
            if dst.exists():
                if sha256(src) == sha256(dst):
                    action["action"] = "already-present"
                else:
                    action["action"] = "conflict"
                report["actions"].append(action)
                continue
            if apply:
                shutil.copy2(src, dst)
            report["actions"].append(action)
        if apply:
            return self.desktop_visibility_check() | {"applied": True, "actions": report["actions"]}
        return report

    def find_local_path_for_entry(self, entry_id: str) -> Optional[Path]:
        for entry in self.manifest.get("entries", []):
            if entry.get("id") == entry_id:
                return self.entry_paths(entry)[0]
        return None

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
            "available": True,
            "container": container,
            "prefix": prefix,
            "placeholderCount": placeholder_count,
            "placeholderSamples": placeholder_samples,
            "currentPendingCount": 0,
            "currentPending": [],
            "trashPendingCount": 0,
            "trashPending": [],
            "otherPendingCount": 0,
            "ready": False,
        }
        brctl = shutil.which("brctl")
        if not brctl:
            report.update({"available": False, "reason": "brctl not found"})
            return report
        try:
            proc = subprocess.run(
                [brctl, "status", container],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            report.update({"available": False, "reason": "brctl status timed out"})
            return report
        report["brctlReturnCode"] = proc.returncode
        if proc.returncode != 0:
            report.update(
                {
                    "available": False,
                    "reason": "brctl status failed",
                    "stderr": proc.stderr.strip()[:500],
                    "stdout": proc.stdout.strip()[:500],
                }
            )
            return report
        pending_terms = ("needs-sync-up", "sync-up-scheduled", "pending-scan", "uploading", "needs-sync")
        pending = brctl_pending_paths(proc.stdout, pending_terms)
        current = sorted(p for p in pending if path_is_under(p, prefix))
        trash = sorted(p for p in pending if p.startswith("/.Trash/") and self.icloud_root.name in p)
        other = sorted(p for p in pending if p not in set(current) and p not in set(trash))
        report.update(
            {
                "currentPendingCount": len(current),
                "currentPending": current[:50],
                "trashPendingCount": len(trash),
                "trashPending": trash[:50],
                "otherPendingCount": len(other),
                "ready": len(current) == 0 and len(placeholder_samples) == 0,
            }
        )
        return report

    def print_results(self, results: List[Dict[str, Any]], include_ok: bool = True) -> int:
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

    def install_launchagent(self, apply: bool, load: bool) -> Path:
        plist_path = Path("~/Library/LaunchAgents/com.park0er.claude-sync-doctor.plist").expanduser()
        log_dir = Path("~/Library/Logs/ClaudeSyncDoctor").expanduser()
        program = [
            sys.executable,
            str(SCRIPT),
            "repair",
            "--safe",
            "--apply",
            "--update-state",
            "--quiet",
        ]
        plist = {
            "Label": "com.park0er.claude-sync-doctor",
            "ProgramArguments": program,
            "StartInterval": 300,
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
                subprocess.run(["launchctl", "unload", str(plist_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["launchctl", "load", str(plist_path)], check=True)
        else:
            print(plistlib.dumps(plist).decode())
        return plist_path

    def handoff(self, apply: bool, yes: bool, force: bool, update_state: bool) -> int:
        """Guided end-of-machine handoff flow.

        This is intentionally a small orchestration layer over check + repair.
        The repair engine remains the single source of truth for data movement.
        """
        print_header(self)
        running, processes = is_claude_running()
        print(f"claude running: {running}")
        if running:
            print("running process sample:")
            for line in processes[:5]:
                print(f"  {line}")

        print("\n== Current check ==")
        current = self.check(update_state=False)
        current_bad = self.print_results(current, include_ok=False)
        orphan = self.desktop_orphan_check()
        visibility = self.desktop_visibility_check()
        icloud = self.icloud_upload_check()
        print(f"desktop orphan count: {orphan.get('orphanCount', 'n/a')}")
        print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
        print(f"iCloud current pending count: {icloud.get('currentPendingCount', 'n/a')}")
        print(f"iCloud placeholder count: {icloud.get('placeholderCount', 'n/a')}")
        print(f"iCloud trash pending count: {icloud.get('trashPendingCount', 'n/a')}")
        print(f"problem entries: {current_bad}")

        print("\n== Proposed repair ==")
        proposed = self.repair(safe=not force, apply=False, force=force, update_state=False)
        proposed_bad = self.print_results(proposed, include_ok=False)
        if proposed_bad == 0:
            print("No repair actions are needed.")

        if not apply and not yes:
            print("\nDry run only. Re-run with `handoff --apply` or `handoff --yes --force` to make changes.")
            return 0

        do_force = force
        if running and not force and not yes:
            choice = input(
                "\nClaude appears to be running. Choose: [f]orce relink, [s]afe repair/defer relink, [a]bort: "
            ).strip().lower()
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
        applied = self.repair(safe=not do_force, apply=True, force=do_force, update_state=update_state)
        self.print_results(applied, include_ok=False)
        desktop_repair = self.desktop_visibility_repair(apply=True)
        for action in desktop_repair.get("actions", []):
            print(f"desktop action: {action['action']}: {action['source']} -> {action['target']}")

        print("\n== Final check ==")
        final = self.check(update_state=update_state)
        final_bad = self.print_results(final, include_ok=False)
        final_orphan = self.desktop_orphan_check()
        final_visibility = self.desktop_visibility_check()
        final_icloud = self.icloud_upload_check()
        print(f"desktop orphan count: {final_orphan.get('orphanCount', 'n/a')}")
        print(f"desktop visible missing count: {final_visibility.get('missingVisibleCount', 'n/a')}")
        print(f"iCloud current pending count: {final_icloud.get('currentPendingCount', 'n/a')}")
        print(f"iCloud placeholder count: {final_icloud.get('placeholderCount', 'n/a')}")
        print(f"iCloud trash pending count: {final_icloud.get('trashPendingCount', 'n/a')}")
        print(f"problem entries: {final_bad}")

        if (
            final_bad == 0
            and final_orphan.get("orphanCount", 0) == 0
            and final_visibility.get("missingVisibleCount", 0) == 0
            and final_icloud.get("ready") is True
        ):
            print("\nHANDOFF_READY: symlinks healthy, desktop metadata is visible, and current ClaudeSync is uploaded.")
            return 0
        print("\nHANDOFF_NOT_READY: inspect the remaining entries before switching machines.")
        return 1


def print_header(doctor: Doctor) -> None:
    print(f"manifest: {doctor.manifest_path}")
    print(f"iCloud:   {doctor.icloud_root}")
    print(f"state:    {doctor.state_path}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check and repair Claude iCloud symlink sync.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="manifest JSON path")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--quiet", action="store_true", help="suppress OK entries")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="fast read-only check")
    p_check.add_argument("--update-state", action="store_true", help="write ledger state")

    p_deep = sub.add_parser("deep-check", help="compare local/cloud trees when both exist")

    p_repair = sub.add_parser("repair", help="repair safe symlink drift")
    p_repair.add_argument("--safe", action="store_true", default=True, help="avoid relink while Claude is running")
    p_repair.add_argument("--force", action="store_true", help="allow relink while Claude is running")
    p_repair.add_argument("--apply", action="store_true", help="make changes")
    p_repair.add_argument("--dry-run", action="store_true", help="show changes only")
    p_repair.add_argument("--update-state", action="store_true", help="update state ledger after apply")

    p_state = sub.add_parser("state", help="print state ledger")

    p_launch = sub.add_parser("install-launchagent", help="write LaunchAgent plist")
    p_launch.add_argument("--apply", action="store_true", help="write plist")
    p_launch.add_argument("--dry-run", action="store_true", help="print plist")
    p_launch.add_argument("--load", action="store_true", help="load LaunchAgent after writing")

    p_handoff = sub.add_parser("handoff", help="guided check + repair flow for switching Macs")
    p_handoff.add_argument("--apply", action="store_true", help="make changes after confirmation")
    p_handoff.add_argument("--yes", action="store_true", help="non-interactive apply with default choices")
    p_handoff.add_argument("--force", action="store_true", help="allow relink even if Claude is running")
    p_handoff.add_argument("--update-state", action="store_true", default=True, help="update state ledger after apply")

    p_icloud_check = sub.add_parser("icloud-check", help="check current ClaudeSync iCloud upload/apply status")

    p_desktop_check = sub.add_parser("desktop-check", help="check Claude Desktop owner visibility metadata")

    p_desktop_repair = sub.add_parser("desktop-repair", help="copy valid foreign Desktop metadata into current owner group")
    p_desktop_repair.add_argument("--apply", action="store_true", help="make changes")
    p_desktop_repair.add_argument("--dry-run", action="store_true", help="show changes only")

    args = parser.parse_args(argv)
    doctor = Doctor(Path(args.manifest).expanduser(), quiet=args.quiet)

    if args.cmd == "check":
        results = doctor.check(update_state=args.update_state)
        orphan = doctor.desktop_orphan_check()
        visibility = doctor.desktop_visibility_check()
        if args.json:
            print(
                json.dumps(
                    {"results": results, "desktopOrphans": orphan, "desktopVisibility": visibility},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print_header(doctor)
            bad = doctor.print_results(results)
            print(f"desktop orphan count: {orphan.get('orphanCount', 'n/a')}")
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            print(f"problem entries: {bad}")
        return 0

    if args.cmd == "deep-check":
        results = doctor.deep_check()
        orphan = doctor.desktop_orphan_check()
        visibility = doctor.desktop_visibility_check()
        if args.json:
            print(
                json.dumps(
                    {"results": results, "desktopOrphans": orphan, "desktopVisibility": visibility},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print_header(doctor)
            bad = doctor.print_results(results)
            print(f"desktop orphan count: {orphan.get('orphanCount', 'n/a')}")
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            print(f"problem entries: {bad}")
        return 0

    if args.cmd == "repair":
        apply = bool(args.apply and not args.dry_run)
        results = doctor.repair(safe=args.safe, apply=apply, force=args.force, update_state=args.update_state)
        if args.json:
            print(json.dumps({"applied": apply, "results": results}, indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"mode: {'apply' if apply else 'dry-run'}")
            print(f"claude running: {is_claude_running()[0]}")
            bad = doctor.print_results(results, include_ok=False)
            print(f"problem entries: {bad}")
        return 0

    if args.cmd == "state":
        print(json.dumps(doctor.state, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    if args.cmd == "install-launchagent":
        apply = bool(args.apply and not args.dry_run)
        path = doctor.install_launchagent(apply=apply, load=args.load)
        if apply:
            print(f"wrote {path}")
            if args.load:
                print("loaded LaunchAgent")
        return 0

    if args.cmd == "handoff":
        apply = bool(args.apply or args.yes)
        return doctor.handoff(apply=apply, yes=args.yes, force=args.force, update_state=args.update_state)

    if args.cmd == "icloud-check":
        report = doctor.icloud_upload_check()
        if args.json:
            print(json.dumps({"icloudUpload": report}, indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"iCloud container: {report.get('container', 'n/a')}")
            print(f"iCloud prefix: {report.get('prefix', 'n/a')}")
            print(f"iCloud current pending count: {report.get('currentPendingCount', 'n/a')}")
            print(f"iCloud placeholder count: {report.get('placeholderCount', 'n/a')}")
            print(f"iCloud trash pending count: {report.get('trashPendingCount', 'n/a')}")
            print(f"iCloud other pending count: {report.get('otherPendingCount', 'n/a')}")
            print(f"iCloud ready: {report.get('ready', False)}")
            if not report.get("available", True):
                print(f"iCloud check unavailable: {report.get('reason')}")
            for path in report.get("currentPending", []):
                print(f"  current pending: {path}")
            for path in report.get("placeholderSamples", []):
                print(f"  placeholder: {path}")
        return 0 if report.get("ready") is True else 1

    if args.cmd == "desktop-check":
        visibility = doctor.desktop_visibility_check()
        if args.json:
            print(json.dumps({"desktopVisibility": visibility}, indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            print(f"desktop visibility orphan count: {visibility.get('orphanCount', 'n/a')}")
        return 0

    if args.cmd == "desktop-repair":
        apply = bool(args.apply and not args.dry_run)
        visibility = doctor.desktop_visibility_repair(apply=apply)
        if args.json:
            print(json.dumps({"applied": apply, "desktopVisibility": visibility}, indent=2, ensure_ascii=False))
        else:
            print_header(doctor)
            print(f"mode: {'apply' if apply else 'dry-run'}")
            for action in visibility.get("actions", []):
                print(f"  {action['action']}: {action['source']} -> {action['target']}")
            print(f"desktop visible missing count: {visibility.get('missingVisibleCount', 'n/a')}")
            print(f"desktop visibility orphan count: {visibility.get('orphanCount', 'n/a')}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
