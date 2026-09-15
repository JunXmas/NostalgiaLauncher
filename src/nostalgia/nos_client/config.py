"""Đọc/ghi cấu hình Nos Client cho mỗi bản chơi.

File `config/nos-client.json` nằm trong thư mục chơi (game_dir) của từng instance.
Launcher ghi file này TRƯỚC khi launch; mod đọc nó khi game bắt đầu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.model.json_value import JsonValue, as_boolean, as_mapping
from nostalgia.storage.files import atomic_write_json, ensure_dir, read_json
from nostalgia.errors import DataFileError

CONFIG_FILE = "config/nos-client.json"


@dataclass(frozen=True, slots=True)
class NosClientConfig:
    """Cấu hình 6 HUD toggle của Nos Client."""

    coords: bool = True
    direction: bool = True
    day: bool = True
    fps: bool = False
    ping: bool = False
    cps: bool = False


def load_nos_client_config(game_dir: Path) -> NosClientConfig:
    """Đọc cấu hình từ thư mục chơi; thiếu hoặc hỏng thì trả mặc định."""
    path = game_dir / CONFIG_FILE
    if not path.is_file():
        return NosClientConfig()
    try:
        fields = as_mapping(read_json(path))
    except DataFileError:
        return NosClientConfig()
    return NosClientConfig(
        coords=as_boolean(fields.get("coords"), default=True),
        direction=as_boolean(fields.get("direction"), default=True),
        day=as_boolean(fields.get("day"), default=True),
        fps=as_boolean(fields.get("fps"), default=False),
        ping=as_boolean(fields.get("ping"), default=False),
        cps=as_boolean(fields.get("cps"), default=False),
    )


def save_nos_client_config(game_dir: Path, config: NosClientConfig) -> None:
    """Ghi cấu hình vào thư mục chơi. Tạo thư mục config/ nếu chưa có."""
    path = game_dir / CONFIG_FILE
    ensure_dir(path.parent)
    document: JsonValue = {
        "coords": config.coords,
        "direction": config.direction,
        "day": config.day,
        "fps": config.fps,
        "ping": config.ping,
        "cps": config.cps,
    }
    atomic_write_json(path, document)
