"""Chỉ xóa thư mục ngoài khi người chơi chọn rõ; bảo vệ kho và bản chơi dùng chung."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance
from nostalgia.storage.paths import DataPaths


def remove_external_game_dir(
    paths: DataPaths,
    instance: Instance,
    other_instances: Iterable[Instance],
) -> None:
    chosen = Path(instance.game_dir_override)
    if not chosen.is_absolute() or chosen.is_symlink() or chosen.is_junction():
        raise InstanceError("không xóa thư mục game ngoài qua liên kết hoặc đường dẫn tương đối")
    target = chosen.resolve()
    if target.parent == target:
        raise InstanceError("không xóa thư mục gốc của ổ đĩa")
    protected = [paths.data_dir.resolve(), paths.config_dir.resolve()]
    protected.extend(
        Path(other.game_dir_override).resolve()
        if other.game_dir_override
        else paths.instance_dir(other.instance_id).resolve()
        for other in other_instances
        if other.instance_id != instance.instance_id
    )
    if any(target.is_relative_to(folder) or folder.is_relative_to(target) for folder in protected):
        raise InstanceError("thư mục game chứa kho launcher hoặc được bản chơi khác sử dụng")
    if chosen.exists():
        if not chosen.is_dir():
            raise InstanceError("đường dẫn game ngoài không phải thư mục")
        shutil.rmtree(chosen)
