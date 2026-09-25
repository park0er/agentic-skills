"""update.lock 文件锁,context manager。"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import BinaryIO, Iterator

from . import config


def _log(msg: str) -> None:
    print(f"[updater:lock] {msg}", file=sys.stderr)


def _lock_file(f: BinaryIO) -> None:
    """Acquire a non-blocking exclusive lock on the lock file."""
    if os.name == "nt":
        import msvcrt

        f.seek(0, os.SEEK_END)
        if f.tell() == 0:
            f.write(b"\0")
            f.flush()
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(f: BinaryIO) -> None:
    """Release the platform-specific lock."""
    if os.name == "nt":
        import msvcrt

        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextmanager
def update_lock() -> Iterator[bool]:
    """独占非阻塞锁。yield True 表示拿到,False 表示被其他进程占用。"""
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    f = config.LOCK_FILE.open("a+b")
    try:
        try:
            _lock_file(f)
        except (BlockingIOError, OSError):
            yield False
            return
        yield True
        try:
            _unlock_file(f)
        except OSError as exc:
            _log(f"unlock failed: {exc}")
    finally:
        f.close()


__all__ = ["update_lock"]
