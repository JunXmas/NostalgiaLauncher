"""Chép JAR cục bộ, không chạy/extract; kiểm cả lô trước khi ghi và hoàn tác nếu lỗi."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from nostalgia.content.installed import LEDGER_FILE_NAME, load_ledger, save_ledger
from nostalgia.errors import ContentError
from nostalgia.model.local_mod import LocalModImport
from nostalgia.storage.files import resolve_child

MAX_MOD_BYTES = 512 * 1024**2
MAX_BATCH_BYTES = 2 * 1024**3
MAX_MOD_FILES = 256


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _directory(parent_dir: Path, name: str) -> Path:
    directory = resolve_child(parent_dir, name)
    if directory.is_symlink():
        raise ContentError(f"không cài mod vào thư mục liên kết: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _backup_directory(game_dir: Path) -> Path:
    private = _directory(game_dir, ".nostalgia")
    backups = _directory(private, "local-mod-backups")
    return _directory(backups, uuid.uuid4().hex)


def install_local_mods(
    game_dir: Path, sources: tuple[Path, ...], *, replace_existing: bool = False
) -> LocalModImport:
    """Không mạng. Thay file phải chủ động bật; giữ trạng thái tắt và sao lưu file cũ."""
    if not sources or len(sources) > MAX_MOD_FILES:
        raise ContentError(f"hãy chọn từ 1 đến {MAX_MOD_FILES} file mod JAR")
    if game_dir.is_symlink():
        raise ContentError("không cài mod vào thư mục chơi là liên kết")
    unique: dict[str, Path] = {}
    total = 0
    for source in sources:
        if source.suffix.lower() != ".jar" or not source.is_file():
            raise ContentError(f"file mod không tồn tại hoặc không phải JAR: {source.name}")
        size = source.stat().st_size
        if size <= 0 or size > MAX_MOD_BYTES:
            raise ContentError(f"file mod vượt giới hạn 512 MiB hoặc rỗng: {source.name}")
        if not zipfile.is_zipfile(source):
            raise ContentError(f"file không phải JAR hợp lệ: {source.name}")
        name = source.stem + ".jar"
        key = name.casefold()
        if key in unique:
            if _digest(unique[key]) != _digest(source):
                raise ContentError(f"hai mod khác nhau trùng tên {name}; đổi tên rồi thả lại")
            continue
        unique[key] = source
        total += size
    if total > MAX_BATCH_BYTES:
        raise ContentError("tổng file mod vượt giới hạn 2 GiB; hãy chia thành nhiều lượt")
    directory = _directory(game_dir, "mods")
    installed: list[str] = []
    skipped: list[str] = []
    committed: list[tuple[Path, Path | None]] = []
    backup_dir: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix=".nostalgia-local-", dir=directory) as temporary:
            staging = Path(temporary)
            changes: list[tuple[Path, Path]] = []
            for source in unique.values():
                name = source.stem + ".jar"
                active = resolve_child(directory, name)
                disabled = resolve_child(directory, name + ".disabled")
                if active.is_symlink() or disabled.is_symlink():
                    raise ContentError(f"file mod đích là liên kết: {name}")
                if active.exists() and disabled.exists():
                    raise ContentError(f"{name} có cả bản bật và tắt; hãy gỡ bản trùng trước")
                target = disabled if disabled.exists() else active
                if target.exists() and (not replace_existing or _digest(source) == _digest(target)):
                    skipped.append(name)
                    continue
                staged = staging / name
                shutil.copyfile(source, staged)
                if staged.stat().st_size != source.stat().st_size or not zipfile.is_zipfile(staged):
                    raise ContentError(f"file mod thay đổi trong lúc chép: {name}")
                changes.append((staged, target))
            for staged, target in changes:
                saved = None
                if target.exists():
                    if backup_dir is None:
                        backup_dir = _backup_directory(game_dir)
                    saved = backup_dir / target.name
                    shutil.copyfile(target, saved)
                if saved is None:
                    # Tạo độc quyền: không ghi đè file được thêm ngoài launcher giữa tác vụ.
                    with target.open("xb") as stream:
                        committed.append((target, None))
                        with staged.open("rb") as source_stream:
                            shutil.copyfileobj(source_stream, stream, 256 * 1024)
                else:
                    committed.append((target, saved))
                    staged.replace(target)
                installed.append(target.name)
            ledger = load_ledger(directory)
            names = {name.removesuffix(".disabled") for name in installed}
            remaining = {pid: row for pid, row in ledger.items() if row.file_name not in names}
            if len(remaining) != len(ledger):
                backup_dir = backup_dir or _backup_directory(game_dir)
                ledger_path = directory / LEDGER_FILE_NAME
                if ledger_path.is_symlink():
                    raise ContentError("sổ nội dung mod là liên kết; không thay đổi")
                saved_ledger = backup_dir / LEDGER_FILE_NAME
                shutil.copyfile(ledger_path, saved_ledger)
                committed.append((ledger_path, saved_ledger))
                save_ledger(directory, remaining)
    except Exception:
        for target, saved in reversed(committed):
            if saved:
                try:
                    saved.replace(target)
                except OSError:
                    shutil.copyfile(saved, target)
            else:
                target.unlink(missing_ok=True)
        raise
    return LocalModImport(tuple(installed), tuple(skipped), backup_dir)
