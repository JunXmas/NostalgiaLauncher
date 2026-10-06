"""Thùng rác bản chơi: chuyển thư mục đăng ký, giữ nguyên thư mục ngoài."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, replace

from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance, check_instance_id
from nostalgia.instance.store import _parse_instance, list_instances, load_instance, save_instance
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.storage.paths import DataPaths

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TrashedInstance:
    trash_id: str
    instance_id: str
    display_name: str
    created_at: float


def list_trashed_instances(paths: DataPaths) -> tuple[TrashedInstance, ...]:
    trash_dir = paths.data_dir / "trash"
    if not trash_dir.is_dir():
        return ()
    rows = []
    for trash_folder in trash_dir.iterdir():
        metadata = trash_folder / "instance.json"
        if trash_folder.is_symlink() or metadata.is_symlink() or not metadata.is_file():
            continue
        try:
            fields = as_mapping(json.loads(metadata.read_bytes()))
            instance_id = as_string(fields.get("instance_id")) or ""
            check_instance_id(instance_id)
        except (OSError, ValueError, InstanceError):
            logger.warning("bỏ qua bản chơi hỏng trong thùng rác: %s", trash_folder)
            continue
        rows.append(
            TrashedInstance(
                trash_folder.name,
                instance_id,
                as_string(fields.get("display_name")) or instance_id,
                metadata.stat().st_mtime,
            )
        )
    return tuple(sorted(rows, key=lambda row: row.created_at, reverse=True))


def trash_instance(paths: DataPaths, instance_id: str) -> str:
    load_instance(paths, instance_id)
    source = paths.instance_dir(instance_id)
    if source.is_symlink():
        raise InstanceError("thư mục bản chơi là liên kết; không thể chuyển vào thùng rác")
    trash_dir = paths.data_dir / "trash"
    trash_dir.mkdir(parents=True, exist_ok=True)
    trash_id = uuid.uuid4().hex
    source.rename(trash_dir / trash_id)
    return trash_id


def restore_trashed_instance(paths: DataPaths, trash_id: str) -> Instance:
    check_instance_id(trash_id)
    source = paths.data_dir / "trash" / trash_id
    if source.is_symlink():
        raise InstanceError("thùng rác chứa liên kết không hợp lệ")
    metadata = source / "instance.json"
    if metadata.is_symlink() or not metadata.is_file():
        raise InstanceError("không còn bản chơi này trong thùng rác")
    try:
        fields = as_mapping(json.loads(metadata.read_bytes()))
    except (OSError, ValueError) as error:
        raise InstanceError(f"metadata thùng rác hỏng: {error}") from error
    original_id = as_string(fields.get("instance_id")) or ""
    check_instance_id(original_id)
    candidate = original_id
    counter = 2
    while paths.instance_dir(candidate).exists():
        candidate = original_id[:50] + f"-restore-{counter}"
        counter += 1
    instance = _parse_instance(fields, fallback_id=candidate)
    if instance is None:
        raise InstanceError("bản chơi trong thùng rác thiếu phiên bản")
    if instance.game_dir_override and any(
        i.game_dir_override == instance.game_dir_override for i in list_instances(paths)
    ):
        raise InstanceError("thư mục ngoài đã được một bản chơi khác sử dụng")
    destination = paths.instance_dir(candidate)
    source.rename(destination)
    try:
        save_instance(paths, replace(instance, instance_id=candidate))
    except Exception:
        destination.rename(source)
        raise
    return instance
