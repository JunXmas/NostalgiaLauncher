"""Kho instance trên đĩa: mỗi bản chơi một file `instance.json` nằm trong thư mục của nó.

Không dùng một file danh sách tập trung, có lý do: xoá thư mục là xoá luôn instance, không
để lại bản ghi mồ côi; và một file hỏng chỉ làm mất đúng bản chơi đó chứ không kéo theo cả
danh sách. Đây cũng đúng cách `versions/` đang làm, nên có một quy ước thay vì hai.

Liệt kê bằng `os.scandir` chứ không `Path.iterdir`: `scandir` đọc sẵn kiểu mục từ dirent nên
bớt một `stat` mỗi mục — cùng lý do đã đo ở `repo/version_repo.py`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from nostalgia.errors import DataFileError, InstanceError
from nostalgia.instance.model import Instance, check_instance_id
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, ensure_dir, read_json
from nostalgia.storage.paths import DataPaths

FORMAT_VERSION = 1
INSTANCE_FILE_NAME = "instance.json"

logger = logging.getLogger(__name__)


def create_instance(paths: DataPaths, instance: Instance) -> Instance:
    """Đăng ký một bản chơi mới. Trùng mã thì báo lỗi chứ không ghi đè.

    Ghi đè lặng lẽ ở đây nghĩa là một lệnh gõ nhầm có thể trỏ thư mục thế giới của người chơi
    sang phiên bản khác.
    """
    check_instance_id(instance.instance_id)
    if paths.instance_json(instance.instance_id).exists():
        message = f"đã có instance {instance.instance_id!r}"
        raise InstanceError(message)
    save_instance(paths, instance)
    return instance


def save_instance(paths: DataPaths, instance: Instance) -> None:
    """Ghi cấu hình của một bản chơi, tạo sẵn thư mục chơi cho nó."""
    check_instance_id(instance.instance_id)
    ensure_dir(paths.instance_dir(instance.instance_id))
    document: JsonValue = {
        "format": FORMAT_VERSION,
        "instance_id": instance.instance_id,
        "version_id": instance.version_id,
        "display_name": instance.display_name,
        "max_heap_megabytes": instance.max_heap_megabytes,
        "window_width": instance.window_width,
        "window_height": instance.window_height,
    }
    atomic_write_json(paths.instance_json(instance.instance_id), document)


def load_instance(paths: DataPaths, instance_id: str) -> Instance:
    """Đọc một bản chơi. Chưa có thì lỗi nêu ĐÚNG đường dẫn còn thiếu."""
    check_instance_id(instance_id)
    path = paths.instance_json(instance_id)
    if not path.is_file():
        message = f"chưa có instance {instance_id!r}: không có {path}"
        raise InstanceError(message)
    instance = _parse_instance(as_mapping(read_json(path)), fallback_id=instance_id)
    if instance is None:
        message = f"cấu hình instance {instance_id!r} thiếu phiên bản game: {path}"
        raise InstanceError(message)
    return instance


def list_instances(paths: DataPaths) -> tuple[Instance, ...]:
    """Mọi bản chơi đã đăng ký, xếp theo mã. Bản hỏng bị bỏ qua kèm cảnh báo."""
    if not paths.instances_dir.is_dir():
        return ()
    instances: list[Instance] = []
    with os.scandir(paths.instances_dir) as entries:
        for child in entries:
            if not child.is_dir():
                continue
            instance = _read_if_usable(Path(child.path, INSTANCE_FILE_NAME), child.name)
            if instance is not None:
                instances.append(instance)
    return tuple(sorted(instances, key=lambda instance: instance.instance_id))


def unregister_instance(paths: DataPaths, instance_id: str) -> Path:
    """Bỏ đăng ký nhưng **giữ nguyên thế giới**, và trả về thư mục còn lại.

    Xoá thế giới của người chơi vì một lệnh gõ nhầm là mất mát không lấy lại được. Ai thật
    sự muốn xoá thì phải nói rõ ở tầng trên; ở đây chỉ gỡ cấu hình.
    """
    check_instance_id(instance_id)
    path = paths.instance_json(instance_id)
    if not path.is_file():
        message = f"chưa có instance {instance_id!r}"
        raise InstanceError(message)
    path.unlink()
    return paths.instance_dir(instance_id)


def _read_if_usable(path: Path, fallback_id: str) -> Instance | None:
    if not path.is_file():
        return None
    try:
        fields = as_mapping(read_json(path))
    except DataFileError:
        logger.warning("bỏ qua instance hỏng: %s", path)
        return None
    instance = _parse_instance(fields, fallback_id=fallback_id)
    if instance is None:
        logger.warning("bỏ qua instance thiếu phiên bản game: %s", path)
    return instance


def _parse_instance(fields: dict[str, JsonValue], *, fallback_id: str) -> Instance | None:
    version_id = as_string(fields.get("version_id"))
    if not version_id:
        return None
    return Instance(
        # Tên thư mục là nguồn đáng tin hơn trường trong file: đổi tên thư mục thì bản chơi
        # đi theo, còn một trường lệch sẽ khiến `load` và `list` nói hai chuyện khác nhau.
        instance_id=fallback_id,
        version_id=version_id,
        display_name=as_string(fields.get("display_name")) or "",
        max_heap_megabytes=as_integer(fields.get("max_heap_megabytes")),
        window_width=as_integer(fields.get("window_width")),
        window_height=as_integer(fields.get("window_height")),
    )
