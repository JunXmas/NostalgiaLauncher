"""Biến manifest của một bản Java thành danh sách việc phải làm trên đĩa.

Theo đúng luật của kho: module lập kế hoạch **không tải và không ghi** — nó chỉ đọc trạng
thái hiện có để biết việc nào còn phải làm. Nhờ vậy toàn bộ logic chọn bản nén, bỏ qua file
đã đúng và kiểm an toàn đường dẫn đều kiểm được offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mccore.errors import UnsafePathError
from mccore.java.runtime_manifest import RuntimeFile, RuntimeLayout
from mccore.model.download import DownloadTask
from mccore.net.download import is_already_correct
from mccore.storage.files import resolve_within

# Đuôi cho file nén tải tạm về. Nó bị xoá ngay sau khi bung xong, nhưng phải có tên khác
# file thật để một lần chạy đứt gánh không để lại bản nén nằm đúng chỗ file thô.
ARCHIVE_SUFFIX = ".lzma"


@dataclass(frozen=True, slots=True)
class CompressedFile:
    """Một file phải bung sau khi tải. `sha1`/`size` là của bản **thô**, tức sau khi bung."""

    archive_path: Path
    destination: Path
    sha1: str | None = None
    size: int | None = None


@dataclass(frozen=True, slots=True)
class RuntimeLink:
    """Một liên kết tượng trưng. Giữ cả đích tương đối lẫn đích đã phân giải.

    `target` là thứ đưa cho `symlink` — giữ nguyên dạng tương đối để cây thư mục di chuyển
    được. `resolved_target` chỉ dùng cho đường lùi chép file khi hệ thống không cho tạo liên
    kết, và cho việc kiểm an toàn lúc lập kế hoạch.
    """

    link_path: Path
    target: str
    resolved_target: Path


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    """Toàn bộ việc phải làm, tách theo loại vì thứ tự thi hành có ý nghĩa."""

    directories: tuple[Path, ...]
    downloads: tuple[DownloadTask, ...]
    archives_to_decode: tuple[CompressedFile, ...]
    links: tuple[RuntimeLink, ...]
    executables: tuple[Path, ...]
    stale_archives: tuple[Path, ...]


def plan_runtime(layout: RuntimeLayout, runtime_root: Path) -> RuntimePlan:
    """Lập kế hoạch cài một bản Java vào `runtime_root`.

    Ba quyết định nằm ở đây:

    1. **File đã đúng thì bỏ hẳn**, kể cả bản có nén. Nếu không kiểm đích thật mà chỉ dựa
       vào bộ tải, thì lần cài thứ hai sẽ tải lại toàn bộ 51 MB bản nén — vì bản nén đã bị
       xoá sau khi bung, nên với bộ tải nó luôn là "chưa có".
    2. **Có bản nén thì lấy bản nén**, tải về `<đích>.lzma` rồi bung.
    3. **Đường dẫn từ manifest đều không tin được**, kể cả đích của liên kết — đích liên kết
       là đường tương đối và hợp lệ khi chứa `..` (bản thật có `../libjsig.so`), nên không
       cấm `..` được mà phải kiểm kết quả có còn nằm trong `runtime_root` hay không.
    """
    directories = tuple(resolve_within(runtime_root, name) for name in layout.directories)
    downloads: list[DownloadTask] = []
    archives_to_decode: list[CompressedFile] = []
    executables: list[Path] = []
    stale_archives: list[Path] = []

    for runtime_file in layout.files:
        destination = resolve_within(runtime_root, runtime_file.relative_path)
        if runtime_file.is_executable:
            executables.append(destination)
        final_task = runtime_file.raw.to_task(destination)
        if is_already_correct(final_task):
            _note_stale_archive(runtime_file, destination, stale_archives)
            continue
        if runtime_file.compressed is None:
            downloads.append(final_task)
            continue
        archive_path = _archive_path(destination)
        downloads.append(runtime_file.compressed.to_task(archive_path))
        archives_to_decode.append(
            CompressedFile(
                archive_path=archive_path,
                destination=destination,
                sha1=runtime_file.raw.sha1,
                size=runtime_file.raw.size,
            )
        )

    return RuntimePlan(
        directories=directories,
        downloads=tuple(downloads),
        archives_to_decode=tuple(archives_to_decode),
        links=tuple(
            _plan_link(runtime_root, name, target) for name, target in layout.links.items()
        ),
        executables=tuple(executables),
        stale_archives=tuple(stale_archives),
    )


def _archive_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ARCHIVE_SUFFIX)


def _note_stale_archive(
    runtime_file: RuntimeFile, destination: Path, stale_archives: list[Path]
) -> None:
    """Bản nén còn sót lại khi một lượt chạy bị ngắt giữa lúc bung xong và lúc xoá."""
    if runtime_file.compressed is None:
        return
    archive_path = _archive_path(destination)
    if archive_path.exists():
        stale_archives.append(archive_path)


def _plan_link(runtime_root: Path, relative_path: str, target: str) -> RuntimeLink:
    link_path = resolve_within(runtime_root, relative_path)
    # `normpath` là phép biến đổi thuần chuỗi: nó gộp `..` mà không hỏi hệ thống file, nên
    # kết quả không phụ thuộc vào việc file đã tồn tại hay chưa.
    resolved_target = Path(os.path.normpath(link_path.parent / target))
    if not resolved_target.is_relative_to(runtime_root):
        message = f"liên kết {relative_path!r} trỏ ra ngoài bản Java: {target!r}"
        raise UnsafePathError(message)
    return RuntimeLink(link_path=link_path, target=target, resolved_target=resolved_target)
