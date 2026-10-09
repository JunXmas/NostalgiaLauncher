"""Chọn dữ liệu modpack; không đóng gói tài khoản, log, cache hay liên kết ngoài."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import InstanceError

PACK_DIRECTORIES = (
    "mods",
    "resourcepacks",
    "shaderpacks",
    "config",
    "defaultconfigs",
    "kubejs",
    "scripts",
    "patchouli_books",
    "paxi",
    "openloader",
    "global_packs",
    "fancymenu",
)
PACK_FILES = ("options.txt", "optionsof.txt", "optionsshaders.txt")
MAX_EXPORT_BYTES = 16 * 1024**3
MAX_EXPORT_FILES = 100_000


@dataclass(frozen=True, slots=True)
class ExportFile:
    path: Path
    relative_path: str
    size_bytes: int
    modified_ns: int


def list_export_files(game_dir: Path, *, include_worlds: bool) -> tuple[ExportFile, ...]:
    if game_dir.is_symlink() or not game_dir.is_dir():
        raise InstanceError("thư mục chơi không tồn tại hoặc là liên kết")
    selected = (*PACK_DIRECTORIES, *(("saves",) if include_worlds else ()), *PACK_FILES)
    files: list[ExportFile] = []
    seen_paths: set[str] = set()
    total = 0

    def append_file(path: Path) -> None:
        nonlocal total
        status = path.lstat()
        if not stat.S_ISREG(status.st_mode):
            raise InstanceError("modpack chứa liên kết hoặc file đặc biệt: " + str(path))
        relative_path = path.relative_to(game_dir).as_posix()
        if any(part.startswith(".nostalgia") for part in path.relative_to(game_dir).parts):
            return
        if "\\" in relative_path or ":" in relative_path:
            raise InstanceError("tên file không tương thích giữa các hệ điều hành")
        if relative_path.casefold() in seen_paths:
            raise InstanceError("modpack có tên file trùng nhau khi đổi hệ điều hành")
        seen_paths.add(relative_path.casefold())
        total += status.st_size
        if total > MAX_EXPORT_BYTES or len(files) >= MAX_EXPORT_FILES:
            raise InstanceError("modpack vượt giới hạn 16 GiB / 100.000 file")
        files.append(ExportFile(path, relative_path, status.st_size, status.st_mtime_ns))

    for folder_name in selected:
        folder = game_dir / folder_name
        if folder.is_symlink():
            raise InstanceError("không xuất dữ liệu qua liên kết: " + str(folder))
        if not folder.exists():
            continue
        if folder.is_file():
            append_file(folder)
            continue
        for directory, directories, names in folder.walk(on_error=_walk_error):
            if any((directory / text).is_symlink() for text in directories):
                raise InstanceError("modpack chứa liên kết thư mục")
            for text in names:
                append_file(directory / text)
    return tuple(sorted(files, key=lambda exported_file: exported_file.relative_path))


def _walk_error(error: OSError) -> None:
    raise InstanceError(f"không đọc được dữ liệu modpack: {error}") from error
