"""Mã pack thuộc bản đăng ký, không phụ thuộc tên, nguồn tải hay mã phòng."""

import re
import uuid

from nostalgia.errors import MultiplayerError, NostalgiaError
from nostalgia.model.json_value import as_mapping
from nostalgia.storage.files import atomic_write_json, read_json
from nostalgia.storage.paths import DataPaths

IDENTITY_FILE = ".nostalgia-host-pack.json"


def ensure_sync_pack_id(paths: DataPaths, instance_id: str) -> str:
    path = paths.instance_dir(instance_id) / IDENTITY_FILE
    if path.is_symlink():
        raise MultiplayerError("Sync identity cannot be a symbolic link.")
    try:
        fields = (
            as_mapping(read_json(path)) if path.is_file() and path.stat().st_size < 1024 else {}
        )
        pack_id = fields.get("pack_id")
        if (
            fields.get("instance_id") == instance_id
            and isinstance(pack_id, str)
            and re.fullmatch(r"[0-9a-f]{32}", pack_id)
        ):
            return pack_id
    except (NostalgiaError, OSError):
        pass
    pack_id = uuid.uuid4().hex
    atomic_write_json(path, {"instance_id": instance_id, "pack_id": pack_id}, private=True)
    return pack_id


def remove_sync_pack_id(paths: DataPaths, instance_id: str) -> None:
    (paths.instance_dir(instance_id) / IDENTITY_FILE).unlink(missing_ok=True)
