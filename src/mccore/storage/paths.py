"""Mọi đường dẫn mà launcher sở hữu, gom vào một đối tượng được truyền xuống.

Đây là luật số một của kho, và nó sinh ra từ một lỗi mất dữ liệu có thật: launcher tiền
nhiệm khai `CONFIG_DIR, CACHE_DIR, DEFAULT_GAME_DIR = _dirs()` ở **mức module**, tính từ
`Path.home()` ngay lúc import. Chỉ cần một dòng import sớm trong test là nó ghi đè config
thật của người dùng và xoá sạch danh sách bản cài.

Ở đây không có hằng `Path` nào ở mức module. Người gọi dựng một `DataPaths` rồi tiêm xuống;
muốn chạy trên thư mục tạm thì chỉ việc tiêm cái khác.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "mc-core"

# Hai biến này cho người dùng và cho test đè lên vị trí mặc định.
DATA_DIR_ENV = "MCCORE_DATA_DIR"
CONFIG_DIR_ENV = "MCCORE_CONFIG_DIR"


@dataclass(frozen=True, slots=True)
class DataPaths:
    """Hai gốc thư mục, và mọi đường dẫn dẫn xuất từ chúng.

    `data_dir` và `config_dir` **tách rời nhau có chủ ý**: đổi chỗ để dữ liệu game không
    được kéo theo cấu hình. Launcher tiền nhiệm gộp hai thứ này và hậu quả là trỏ thư mục
    game sang `/tmp` một lần là mất luôn danh sách bản cài.
    """

    data_dir: Path
    config_dir: Path

    @classmethod
    def for_root(cls, root: Path) -> DataPaths:
        """Đặt cả hai gốc dưới một thư mục — dùng cho test và cho chế độ chạy di động."""
        return cls(data_dir=root / "data", config_dir=root / "config")

    @classmethod
    def from_env(cls, platform_name: str, environ: Mapping[str, str] | None = None) -> DataPaths:
        """Vị trí mặc định theo quy ước của từng hệ điều hành.

        Nhận `environ` làm đối số thay vì đọc thẳng `os.environ`, để test dựng được mọi
        tình huống mà không phải vá biến môi trường toàn cục.
        """
        environment = os.environ if environ is None else environ
        data_dir = environment.get(DATA_DIR_ENV)
        config_dir = environment.get(CONFIG_DIR_ENV)
        default_data, default_config = _default_roots(platform_name, environment)
        return cls(
            data_dir=Path(data_dir) if data_dir else default_data,
            config_dir=Path(config_dir) if config_dir else default_config,
        )

    @property
    def versions_dir(self) -> Path:
        return self.data_dir / "versions"

    @property
    def libraries_dir(self) -> Path:
        return self.data_dir / "libraries"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def asset_indexes_dir(self) -> Path:
        return self.assets_dir / "indexes"

    @property
    def asset_objects_dir(self) -> Path:
        return self.assets_dir / "objects"

    @property
    def runtime_dir(self) -> Path:
        return self.data_dir / "runtime"

    def version_dir(self, version_id: str) -> Path:
        return self.versions_dir / version_id

    def version_json(self, version_id: str) -> Path:
        return self.version_dir(version_id) / f"{version_id}.json"

    def version_jar(self, version_id: str) -> Path:
        return self.version_dir(version_id) / f"{version_id}.jar"

    def natives_dir(self, version_id: str) -> Path:
        return self.version_dir(version_id) / "natives"

    def asset_index_json(self, asset_index_id: str) -> Path:
        return self.asset_indexes_dir / f"{asset_index_id}.json"

    def asset_object(self, asset_hash: str) -> Path:
        """Mojang lưu object theo hai ký tự đầu của hash — một chỗ duy nhất biết luật này."""
        return self.asset_objects_dir / asset_hash[:2] / asset_hash


def _default_roots(platform_name: str, environment: Mapping[str, str]) -> tuple[Path, Path]:
    """Vị trí mặc định khi người dùng không đặt biến môi trường nào."""
    home = Path(environment.get("HOME") or environment.get("USERPROFILE") or ".")
    if platform_name == "windows":
        base = Path(environment.get("APPDATA") or home / "AppData" / "Roaming")
        return base / APP_NAME / "data", base / APP_NAME / "config"
    if platform_name == "osx":
        support = home / "Library" / "Application Support" / APP_NAME
        return support / "data", support / "config"
    data_home = Path(environment.get("XDG_DATA_HOME") or home / ".local" / "share")
    config_home = Path(environment.get("XDG_CONFIG_HOME") or home / ".config")
    return data_home / APP_NAME, config_home / APP_NAME
