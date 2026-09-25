"""升级包下载、完整性校验、安全解压。

根据文件后缀在 tar 与 zip 之间分发:
- ``.tar.gz`` / ``.tgz`` / ``.tar`` → :mod:`tarfile`
- ``.zip``                          → :mod:`zipfile`

两条路径共享同一组路径逃逸防护(拒绝绝对路径、拒绝成员名路径片段含 ``..``)。
"""
from __future__ import annotations

import shutil
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import config


# URL / 文件后缀 → 内部归档类型 tag
TAR_SUFFIXES = (".tar.gz", ".tgz", ".tar")
ZIP_SUFFIXES = (".zip",)
SUPPORTED_SUFFIXES = TAR_SUFFIXES + ZIP_SUFFIXES


def _log(msg: str) -> None:
    print(f"[updater:tarball] {msg}", file=sys.stderr)


def classify(path_or_url: str | Path) -> str | None:
    """按后缀判定归档类型。返回 ``"tar"`` / ``"zip"`` / ``None``。

    用于 URL(主流程按 ``download_url`` 分发)和文件路径(verify/safe_extract
    按实际磁盘路径)两个场景。匹配是小写后缀 endswith。
    """
    name = str(path_or_url).lower()
    if name.endswith(TAR_SUFFIXES):
        return "tar"
    if name.endswith(ZIP_SUFFIXES):
        return "zip"
    return None


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=config.DOWNLOAD_TIMEOUT_SECONDS) as resp:
            if not (200 <= resp.status < 300):
                _log(f"download status {resp.status}")
                return False
            with dest.open("wb") as fh:
                shutil.copyfileobj(resp, fh)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _log(f"download error: {exc}")
        return False
    return True


def _is_unsafe_member(name: str) -> bool:
    """拒绝绝对路径和路径片段含 ``..`` 的成员名。

    tar 与 zip 共用:两种格式的 zip-slip / tar-traversal 攻击面相同。
    """
    if name.startswith("/"):
        return True
    # 用 PurePosixPath 切,免得宿主机是 Windows 时被当作盘符解析
    return ".." in Path(name).parts


def _verify_tar(path: Path) -> bool:
    try:
        with tarfile.open(path, "r:*") as tf:
            for _ in tf:
                pass
    except (tarfile.TarError, OSError) as exc:
        _log(f"verify failed (tar): {exc}")
        return False
    return True


def _verify_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                _log(f"verify failed (zip): bad crc in {bad}")
                return False
    except (zipfile.BadZipFile, OSError) as exc:
        _log(f"verify failed (zip): {exc}")
        return False
    return True


def verify(archive_path: Path) -> bool:
    """结构完整性检查。按文件后缀选 tar/zip;后缀不在白名单返回 False。"""
    kind = classify(archive_path)
    if kind == "tar":
        return _verify_tar(archive_path)
    if kind == "zip":
        return _verify_zip(archive_path)
    _log(f"verify failed: unsupported archive suffix: {archive_path}")
    return False


def _extract_tar(path: Path, target: Path) -> bool:
    try:
        with tarfile.open(path, "r:*") as tf:
            for member in tf.getmembers():
                if _is_unsafe_member(member.name):
                    _log(f"reject unsafe tar member: {member.name}")
                    return False
            tf.extractall(path=target)
    except (tarfile.TarError, OSError) as exc:
        _log(f"extract error (tar): {exc}")
        return False
    return True


def _extract_zip(path: Path, target: Path) -> bool:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            for info in zf.infolist():
                if _is_unsafe_member(info.filename):
                    _log(f"reject unsafe zip member: {info.filename}")
                    return False
            zf.extractall(path=target)
    except (zipfile.BadZipFile, OSError) as exc:
        _log(f"extract error (zip): {exc}")
        return False
    return True


def safe_extract(archive_path: Path, target: Path) -> bool:
    """按后缀选 tar/zip 解压,共享路径逃逸防护。失败返回 False。"""
    target.mkdir(parents=True, exist_ok=True)
    kind = classify(archive_path)
    if kind == "tar":
        return _extract_tar(archive_path, target)
    if kind == "zip":
        return _extract_zip(archive_path, target)
    _log(f"extract error: unsupported archive suffix: {archive_path}")
    return False


__all__ = [
    "download",
    "verify",
    "safe_extract",
    "classify",
    "TAR_SUFFIXES",
    "ZIP_SUFFIXES",
    "SUPPORTED_SUFFIXES",
]
