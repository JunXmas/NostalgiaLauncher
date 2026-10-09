"""Kết quả chép mod cục bộ; file cũ được giữ riêng khi thay trùng tên."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LocalModImport:
    installed: tuple[str, ...]
    skipped: tuple[str, ...]
    backup_dir: Path | None = None
