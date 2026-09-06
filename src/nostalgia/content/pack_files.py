"""Chép một thư mục con của file zip modpack vào thư mục bản chơi.

Dùng chung cho `overrides/` của mrpack và của manifest CurseForge. Mọi tên entry đi qua
`resolve_within`; không bao giờ tạo symlink từ nội dung archive.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from nostalgia.storage.files import ensure_dir, resolve_within


def copy_prefixed_members(zip_path: Path, game_dir: Path, prefixes: tuple[str, ...]) -> int:
    """Chép entry dưới từng `prefix` (theo thứ tự; cái sau đè cái trước). Trả số file đã ghi."""
    written = 0
    with zipfile.ZipFile(zip_path) as archive:
        for prefix in prefixes:
            normalised = prefix.rstrip("/") + "/"
            for member in archive.infolist():
                if not member.filename.startswith(normalised) or member.is_dir():
                    continue
                destination = resolve_within(game_dir, member.filename[len(normalised) :])
                ensure_dir(destination.parent)
                with archive.open(member) as source, destination.open("wb") as target:
                    target.write(source.read())
                written += 1
    return written
