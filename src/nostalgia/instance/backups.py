"""Sao lưu dữ liệu chơi và khôi phục sang bản mới, không ghi đè thế giới hiện có."""

from __future__ import annotations

import json
import shutil
import stat
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance, check_instance_id
from nostalgia.instance.store import _parse_instance, game_dir_of, load_instance, save_instance
from nostalgia.model.json_value import as_mapping
from nostalgia.storage.paths import DataPaths

MAX_BACKUP_BYTES = 16 * 1024**3
MAX_BACKUP_FILES = 100_000


@dataclass(frozen=True, slots=True)
class InstanceBackup:
    path: Path
    display_name: str
    created_at: float
    size_bytes: int


def list_instance_backups(paths: DataPaths) -> tuple[InstanceBackup, ...]:
    folder = paths.data_dir / "backups"
    if not folder.is_dir():
        return ()
    return tuple(
        InstanceBackup(p, p.stem, p.stat().st_mtime, p.stat().st_size)
        for p in sorted(folder.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if p.is_file() and not p.is_symlink()
    )


def create_instance_backup(paths: DataPaths, instance_id: str) -> InstanceBackup:
    instance = load_instance(paths, instance_id)
    source = game_dir_of(paths, instance)
    if source.is_symlink():
        raise InstanceError("không sao lưu thư mục chơi là liên kết; chọn thư mục thật")
    folder = paths.data_dir / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{instance_id}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    target = folder / f"{name}.zip"
    temporary = folder / f"{name}.partial"
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            temporary.chmod(0o600)
            fields = json.loads(paths.instance_json(instance_id).read_bytes())
            archive.writestr("manifest.json", json.dumps({"format": 1, "instance": fields}))
            total = 0
            count = 0
            for parent, directories, names in source.walk(
                follow_symlinks=False, on_error=_walk_error
            ):
                if any((parent / d).is_symlink() for d in directories):
                    raise InstanceError("bản chơi chứa liên kết thư mục; sao lưu đã dừng")
                for name in names:
                    path = parent / name
                    if path.is_symlink() or not path.is_file():
                        raise InstanceError("bản chơi chứa liên kết hoặc file đặc biệt")
                    relative = path.relative_to(source)
                    if relative.as_posix() == "instance.json":
                        continue
                    total += path.stat().st_size
                    count += 1
                    if total > MAX_BACKUP_BYTES or count > MAX_BACKUP_FILES:
                        raise InstanceError("bản sao lưu vượt giới hạn 16 GiB / 100.000 file")
                    archive.write(path, "game/" + relative.as_posix())
        temporary.replace(target)
    except (OSError, zipfile.BadZipFile) as error:
        raise InstanceError(f"không tạo được bản sao lưu: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return InstanceBackup(target, instance.label, target.stat().st_mtime, target.stat().st_size)


def restore_instance_backup(paths: DataPaths, backup: Path, instance_id: str) -> Instance:
    check_instance_id(instance_id)
    destination = paths.instance_dir(instance_id)
    if destination.exists() or destination.is_symlink():
        raise InstanceError(f"đã có thư mục {instance_id!r}; hãy chọn mã khác")
    paths.instances_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(backup) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_BACKUP_FILES + 1:
                raise InstanceError("bản sao lưu có quá nhiều file")
            if sum(zip_entry.file_size for zip_entry in entries) > MAX_BACKUP_BYTES:
                raise InstanceError("bản sao lưu vượt giới hạn 16 GiB")
            if archive.getinfo("manifest.json").file_size > 128 * 1024:
                raise InstanceError("metadata bản sao lưu quá lớn")
            fields = as_mapping(json.loads(archive.read("manifest.json")))
            if fields.get("format") != 1:
                raise InstanceError("định dạng bản sao lưu không được hỗ trợ")
            original = _parse_instance(as_mapping(fields.get("instance")), fallback_id=instance_id)
            if original is None:
                raise InstanceError("bản sao lưu thiếu phiên bản Minecraft")
            instance = replace(
                original, game_dir_override="", display_name=original.label + " (restore)"
            )
            with tempfile.TemporaryDirectory(prefix="restore-", dir=paths.instances_dir) as staging:
                stage = Path(staging) / "game"
                stage.mkdir()
                seen: set[str] = set()
                for zip_entry in entries:
                    if zip_entry.filename == "manifest.json":
                        continue
                    parts = PurePosixPath(zip_entry.filename)
                    if (
                        parts.is_absolute()
                        or ".." in parts.parts
                        or "\\" in zip_entry.filename
                        or ":" in zip_entry.filename
                        or not parts.parts
                        or parts.parts[0] != "game"
                        or stat.S_ISLNK(zip_entry.external_attr >> 16)
                    ):
                        raise InstanceError("bản sao lưu có đường dẫn không an toàn")
                    relative = PurePosixPath(*parts.parts[1:])
                    key = relative.as_posix().casefold()
                    if key in seen or key == "instance.json":
                        raise InstanceError("bản sao lưu có đường dẫn trùng hoặc ghi đè metadata")
                    seen.add(key)
                    target = stage.joinpath(*relative.parts)
                    if zip_entry.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(zip_entry) as source, target.open("wb") as output:
                            shutil.copyfileobj(source, output)
                stage.rename(destination)
                try:
                    save_instance(paths, instance)
                except Exception:
                    shutil.rmtree(destination)
                    raise
        return instance
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        raise InstanceError(f"không khôi phục được bản sao lưu: {error}") from error


def _walk_error(error: OSError) -> None:
    raise error
