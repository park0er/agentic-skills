#!/usr/bin/env python3
"""Skill self-update orchestrator — 串起 config/cooldown/lock/remote/tarball/swap。"""
from __future__ import annotations

import json, shutil, sys, time
from datetime import datetime, timezone
from pathlib import Path

# 支持两种启动方式:
#   1) python skills/rollie-diagnose/scripts/updater/check_and_update.py
#      (create_session.sh 实战路径,此时 sys.path 只有脚本所在目录)
#   2) pytest(skill_root 已在 sys.path,可走 from scripts.updater import ...)
# 两种场景下 `from utils.http_client import ...` 都需要 scripts/ 在 sys.path。
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_SKILL_ROOT = _SCRIPTS_DIR.parent
for p in (_SKILL_ROOT, _SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from utils.http_client import SKILL_VERSION  # noqa: E402
from scripts.updater import config, cooldown, lock, remote, tarball, swap  # noqa: E402

def _log(msg: str) -> None:
    print(f"[updater] {msg}", file=sys.stderr)

def _cleanup(paths: list[Path]) -> None:
    for p in paths:
        try: shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        except OSError: pass

def _archive_suffix_for(url: str) -> str | None:
    """按 URL 白名单后缀选一个磁盘后缀名;未识别返回 None。

    保留 ``.tar.gz`` / ``.tgz`` / ``.tar`` / ``.zip`` 的原样写回,避免把
    ``foo.tgz`` 改写成 ``foo.tar.gz`` 打乱服务端登记记录的观察值。
    """
    lower = url.lower()
    for suffix in tarball.SUPPORTED_SUFFIXES:
        if lower.endswith(suffix):
            return suffix
    return None


def _do_upgrade(url: str, from_version: str, to_version: str) -> int:
    suffix = _archive_suffix_for(url)
    if suffix is None:
        _log(f"unsupported archive suffix: {url}")
        return config.EXIT_UPDATE_FAILED
    for d in (config.STATE_DIR, config.DOWNLOAD_DIR, config.STAGING_DIR, config.OLD_DIR):
        d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = config.DOWNLOAD_DIR / f"{to_version}_{ts}{suffix}"
    staging = config.STAGING_DIR / f"{to_version}_{ts}"
    old_target = config.OLD_DIR / f"{from_version}_{ts}"
    if not tarball.download(url, archive_path) or not tarball.verify(archive_path):
        _cleanup([archive_path]); return config.EXIT_UPDATE_FAILED
    if not tarball.safe_extract(archive_path, staging):
        _cleanup([archive_path, staging]); return config.EXIT_UPDATE_FAILED
    new_dir = swap.locate_new_skill_dir(staging)
    if new_dir is None:
        _log("cannot locate new skill dir in archive")
        _cleanup([archive_path, staging]); return config.EXIT_UPDATE_FAILED
    try:
        swap.atomic_replace(new_skill_dir=new_dir, old_target=old_target)
    except swap.SwapError as exc:
        _log(f"atomic replace failed: {exc}")
        _cleanup([archive_path, staging]); return config.EXIT_UPDATE_FAILED
    _cleanup([archive_path, staging])
    print(json.dumps({"status": "updated", "from_version": from_version, "to_version": to_version,
                      "message": f"skill 已升级到 {to_version}。请重新读取 SKILL.md 并重新执行当前查询。"},
                     ensure_ascii=False))
    return config.EXIT_UPDATED

def main() -> int:
    if config.skip_update() or cooldown.in_cooldown():
        return config.EXIT_CONTINUE
    with lock.update_lock() as acquired:
        if not acquired:
            return config.EXIT_CONTINUE
        data = remote.check_update(SKILL_VERSION)
        if data is None:
            return config.EXIT_CONTINUE
        cooldown.write_last_check_ts(time.time())
        if not data.get("has_update"):
            return config.EXIT_CONTINUE
        latest = str(data.get("latest_version") or "").strip()
        url = str(data.get("download_url") or "").strip()
        if not latest or not url or latest == SKILL_VERSION:
            return config.EXIT_CONTINUE
        return _do_upgrade(url, SKILL_VERSION, latest)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(config.EXIT_CONTINUE)
