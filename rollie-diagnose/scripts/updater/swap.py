"""目录原子替换 + state 合并回写 + 失败回滚。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import config


def _log(msg: str) -> None:
    print(f"[updater:swap] {msg}", file=sys.stderr)


class SwapError(Exception):
    """原子替换失败;调用方负责清理临时文件并按退出码 EXIT_UPDATE_FAILED 返回。"""


def _rename(src: Path, dst: Path) -> None:
    """包一层 os.rename 便于测试 monkey-patch 注入失败。"""
    os.rename(src, dst)


def locate_new_skill_dir(staging_root: Path) -> Path | None:
    direct = staging_root / config.SKILL_ROOT.name
    if (direct / "SKILL.md").is_file():
        return direct
    entries = [p for p in staging_root.iterdir() if p.is_dir()]
    if len(entries) == 1 and (entries[0] / "SKILL.md").is_file():
        return entries[0]
    return None


def merge_state_back(old_skill_root: Path, new_skill_root: Path) -> None:
    """把老 skill 目录的 state/(业务状态如 cookies.json)合并回新 skill 目录。

    注意:这里的 state/ 是 skill 业务状态(SKILL_ROOT/state/),
    不是 updater 自己的 ~/.rollie/updater/.../ 运行时状态。
    """
    old_state = old_skill_root / "state"
    if not old_state.is_dir():
        return
    new_state = new_skill_root / "state"
    new_state.mkdir(parents=True, exist_ok=True)
    for item in old_state.iterdir():
        dst = new_state / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                if dst.exists():
                    dst.unlink()
                shutil.copy2(item, dst)
        except OSError as exc:
            _log(f"state merge warn {item}: {exc}")


def atomic_replace(*, new_skill_dir: Path, old_target: Path) -> None:
    """两步 rename + state 合并。失败抛 SwapError,并保证 SKILL_ROOT 回到原位。

    前置条件:调用方必须传一个位于 SKILL_ROOT 外部的 old_target 路径。
    config.OLD_DIR 默认位于 ~/.rollie/updater/<skill_id>/old 已经满足此条件。
    """
    # Step 1: SKILL_ROOT → old_target
    try:
        _rename(config.SKILL_ROOT, old_target)
    except OSError as exc:
        raise SwapError(f"rename old failed: {exc}") from exc

    # Step 2: new_skill_dir → SKILL_ROOT
    try:
        _rename(new_skill_dir, config.SKILL_ROOT)
    except OSError as exc:
        # 回滚:把老目录挪回去
        try:
            _rename(old_target, config.SKILL_ROOT)
        except OSError as roll_exc:
            _log(f"rollback failed: {roll_exc}")
        raise SwapError(f"rename new failed: {exc}") from exc

    # Step 3: 把老 state/ 内容搬回新目录
    try:
        merge_state_back(old_target, config.SKILL_ROOT)
    except Exception as exc:  # merge 失败不回滚,此时目录已经是新版
        _log(f"state merge error: {exc}")


__all__ = ["SwapError", "atomic_replace", "locate_new_skill_dir", "merge_state_back"]
