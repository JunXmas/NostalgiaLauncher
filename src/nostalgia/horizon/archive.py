"""Bung gói vào vùng tạm; từ chối liên kết, đường dẫn thoát và gói quá lớn."""

from __future__ import annotations

import shutil
import stat
import tarfile
import zipfile
from pathlib import Path

from nostalgia.errors import IntegrityError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import resolve_within, set_executable

MAX_FILES = 10_000
MAX_EXPANDED_BYTES = 512 * 1024 * 1024


def extract_horizon_bundle(
    archive_path: Path, staging_dir: Path, cancel_token: CancelToken | None = None
) -> Path:
    """Bản dựng chính thức có đúng một thư mục gốc, giữ nguyên exporter và lock."""
    total = 0
    count = 0
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                count += 1
                total += member.file_size
                _check_limits(count, total, cancel_token)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise IntegrityError("Horizon archive contains a symbolic link")
                destination = _destination(staging_dir, member.filename)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("xb") as output:
                        shutil.copyfileobj(source, output, 64 * 1024)
                    if mode & 0o111:
                        set_executable(destination)
    else:
        with tarfile.open(archive_path, "r:gz") as archive:
            for tar_member in archive:
                count += 1
                total += tar_member.size
                _check_limits(count, total, cancel_token)
                destination = _destination(staging_dir, tar_member.name)
                if tar_member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif tar_member.isfile():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    tar_source = archive.extractfile(tar_member)
                    if tar_source is None:
                        raise IntegrityError("Horizon archive has an unreadable file")
                    with tar_source, destination.open("xb") as output:
                        shutil.copyfileobj(tar_source, output, 64 * 1024)
                    if tar_member.mode & 0o111:
                        set_executable(destination)
                else:
                    raise IntegrityError("Horizon archive contains a link or special file")
    children = list(staging_dir.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        raise IntegrityError("Horizon archive must contain one build directory")
    build_dir = children[0]
    if not (build_dir / "research-lock.json").is_file() or not (build_dir / "exporters").is_dir():
        raise IntegrityError("Horizon archive is missing its lock or exporters")
    return build_dir


def _destination(staging_dir: Path, text: str) -> Path:
    if "\\" in text or ":" in text or text.startswith("/"):
        raise IntegrityError("Unsafe Horizon archive path")
    return resolve_within(staging_dir, text.rstrip("/"))


def _check_limits(count: int, total: int, cancel_token: CancelToken | None) -> None:
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    if count > MAX_FILES or total > MAX_EXPANDED_BYTES:
        raise IntegrityError("Horizon archive exceeds extraction limits")
