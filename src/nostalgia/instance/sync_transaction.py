"""Cập nhật có bản sao lưu và journal: lỗi/cancel giữ lại bộ mod trước đó."""

import os
import re
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping
from nostalgia.multiplayer.sync_manifest import sync_path
from nostalgia.storage.files import atomic_write_json, read_json, sync_directory

JOURNAL_FILE = ".nostalgia-sync-pending.json"
METADATA_FILES = ("instance.json", ".nostalgia-sync-receipt.json")


def safe_sync_target(game_dir: Path, relative_path: str) -> Path:
    target = game_dir / sync_path(relative_path)
    current = target
    while current != game_dir.parent:
        if current.is_symlink() or (
            current.exists() and current != target and not current.is_dir()
        ):
            raise MultiplayerError("Đường dẫn đồng bộ chứa symlink hoặc xung đột thư mục.")
        current = current.parent
    if target.exists() and not target.is_file():
        raise MultiplayerError("File đồng bộ trùng với một thư mục trên máy khách.")
    return target


def replace_sync_bytes(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".sync-")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as stream:
            shutil.copyfileobj(stream, output)
            output.flush()
            os.fsync(output.fileno())
        temporary_path.replace(target)
        sync_directory(target.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def recover_sync_update(registry_dir: Path, game_dir: Path) -> None:
    journal = registry_dir / JOURNAL_FILE
    if not journal.exists():
        return
    if journal.is_symlink() or journal.stat().st_size > 2 * 1024**2:
        raise MultiplayerError("Journal cập nhật không an toàn.")
    fields = as_mapping(read_json(journal))
    if fields.get("game_dir") != str(game_dir):
        raise MultiplayerError("Thư mục chơi khác với journal; dừng phục hồi để tránh ghi nhầm.")
    backup_id = fields.get("backup_id")
    if not isinstance(backup_id, str) or not re.fullmatch(r"[0-9a-f]{32}", backup_id):
        raise MultiplayerError("Journal cập nhật không hợp lệ.")
    backup = registry_dir / ".nostalgia-sync-backups" / backup_id
    if backup.is_symlink() or backup.parent.is_symlink():
        raise MultiplayerError("Bản sao lưu đồng bộ chứa symlink.")
    if fields.get("committed") is not True:
        for raw in as_list(fields.get("paths")):
            record = as_mapping(raw)
            relative_path = record.get("path")
            if not isinstance(relative_path, str):
                raise MultiplayerError("Journal thiếu đường dẫn.")
            target = safe_sync_target(game_dir, relative_path)
            saved = safe_sync_target(backup / "game", relative_path)
            if record.get("existed") is True:
                replace_sync_bytes(saved, target)
            else:
                target.unlink(missing_ok=True)
                sync_directory(target.parent)
        for name in METADATA_FILES:
            saved = backup / "metadata" / name
            target = registry_dir / name
            if target.is_symlink() or saved.is_symlink():
                raise MultiplayerError("Metadata cập nhật chứa symlink.")
            if saved.is_file():
                replace_sync_bytes(saved, target)
            else:
                target.unlink(missing_ok=True)
                sync_directory(target.parent)
    journal.unlink()
    sync_directory(registry_dir)


@contextmanager
def sync_transaction(
    registry_dir: Path, game_dir: Path, touched_paths: frozenset[str]
) -> Iterator[None]:
    backup_id = uuid.uuid4().hex
    backup = registry_dir / ".nostalgia-sync-backups" / backup_id
    if backup.parent.is_symlink():
        raise MultiplayerError("Kho bản sao lưu chứa symlink.")
    records: list[JsonValue] = []
    for relative_path in sorted(touched_paths):
        target = safe_sync_target(game_dir, relative_path)
        existed = target.is_file()
        records.append({"path": relative_path, "existed": existed})
        if existed:
            replace_sync_bytes(target, safe_sync_target(backup / "game", relative_path))
    for name in METADATA_FILES:
        target = registry_dir / name
        if target.is_symlink():
            raise MultiplayerError("Metadata cập nhật chứa symlink.")
        if target.is_file():
            replace_sync_bytes(target, backup / "metadata" / name)
    journal = registry_dir / JOURNAL_FILE
    document: dict[str, JsonValue] = {
        "backup_id": backup_id,
        "game_dir": str(game_dir),
        "paths": records,
        "committed": False,
    }
    atomic_write_json(journal, document, private=True)
    try:
        yield
        document["committed"] = True
        atomic_write_json(journal, document, private=True)
    except BaseException:
        recover_sync_update(registry_dir, game_dir)
        raise
    journal.unlink()
    sync_directory(registry_dir)
