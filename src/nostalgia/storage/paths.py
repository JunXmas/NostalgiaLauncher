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
from dataclasses import dataclass, field
from pathlib import Path

from nostalgia.storage.files import resolve_child

APP_NAME = "nostalgia"

# Hai biến này cho người dùng và cho test đè lên vị trí mặc định.
DATA_DIR_ENV = "NOSTALGIA_DATA_DIR"
CONFIG_DIR_ENV = "NOSTALGIA_CONFIG_DIR"


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
    def for_root(cls, root_dir: Path) -> DataPaths:
        """Đặt cả hai gốc dưới một thư mục — dùng cho test và cho chế độ chạy di động."""
        return cls(data_dir=root_dir / "data", config_dir=root_dir / "config")

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

    versions_dir: Path = field(init=False)
    libraries_dir: Path = field(init=False)
    assets_dir: Path = field(init=False)
    asset_indexes_dir: Path = field(init=False)
    asset_objects_dir: Path = field(init=False)
    runtime_dir: Path = field(init=False)
    instances_dir: Path = field(init=False)
    skins_dir: Path = field(init=False)
    # Kho tài khoản nằm ở `config_dir`, KHÔNG ở `data_dir`: xoá dữ liệu game để lấy chỗ
    # trống thì không được mất tài khoản theo.
    accounts_json: Path = field(init=False)

    def __post_init__(self) -> None:
        """Tính sẵn các thư mục dẫn xuất một lần, thay vì mỗi lần truy cập.

        Chúng từng là `property`, tức mỗi lần đọc lại nối `Path` từ đầu. Đo được:
        `asset_objects_dir` tốn 5,95 µs mỗi lần, và khi lập kế hoạch tải 3.575 asset thì nó
        bị gọi 3.575 lần — 21 ms thuần lặp lại. Lớp vẫn `frozen`; `object.__setattr__` là
        cách chính thức để gán trong `__post_init__`.
        """
        assets_dir = self.data_dir / "assets"
        for name, value in (
            ("versions_dir", self.data_dir / "versions"),
            ("libraries_dir", self.data_dir / "libraries"),
            ("assets_dir", assets_dir),
            ("asset_indexes_dir", assets_dir / "indexes"),
            ("asset_objects_dir", assets_dir / "objects"),
            ("runtime_dir", self.data_dir / "runtime"),
            ("instances_dir", self.data_dir / "instances"),
            ("skins_dir", self.data_dir / "skins"),
            ("accounts_json", self.config_dir / "accounts.json"),
        ):
            object.__setattr__(self, name, value)

    def version_dir(self, version_id: str) -> Path:
        """Mã phiên bản đến từ dòng lệnh, nên phải kiểm trước khi ghép vào đường dẫn."""
        return resolve_child(self.versions_dir, version_id)

    def version_json(self, version_id: str) -> Path:
        return resolve_child(self.version_dir(version_id), f"{version_id}.json")

    def version_jar(self, version_id: str) -> Path:
        return resolve_child(self.version_dir(version_id), f"{version_id}.jar")

    def instance_dir(self, instance_id: str) -> Path:
        """Thư mục chơi của một instance. Mã instance do người dùng gõ nên phải kiểm.

        Nằm trong `data_dir` chứ không nằm cạnh kho tải: thế giới, tuỳ chọn và ảnh chụp là
        dữ liệu của người chơi, còn `versions/`, `libraries/`, `assets/`, `runtime/` là kho
        dùng chung mà mọi instance chia nhau — chép chúng cho từng instance là nhân 700 MB
        lên theo số bản chơi.
        """
        return resolve_child(self.instances_dir, instance_id)

    def instance_json(self, instance_id: str) -> Path:
        return resolve_child(self.instance_dir(instance_id), "instance.json")

    def natives_dir(self, version_id: str) -> Path:
        return self.version_dir(version_id) / "natives"

    def asset_index_json(self, asset_index_id: str) -> Path:
        return resolve_child(self.asset_indexes_dir, f"{asset_index_id}.json")

    def java_runtime_dir(self, java_component: str, runtime_os_key: str) -> Path:
        """Bố trí `runtime/<component>/<khoá hệ điều hành>`, theo đúng cách Mojang chia.

        Tách theo khoá hệ điều hành vì cùng một máy có thể giữ cả bản arm64 lẫn bản x64 lùi
        về — bản Apple Silicon không có `jre-legacy` nên phải dùng bản x64 cho 1.8.9.
        """
        return resolve_child(resolve_child(self.runtime_dir, java_component), runtime_os_key)

    def virtual_assets_dir(self, asset_index_id: str) -> Path:
        """Cây asset theo TÊN cho đời 1.6 — nằm trong kho, dùng chung giữa các bản cài."""
        return resolve_child(self.assets_dir / "virtual", asset_index_id)

    def asset_object(self, asset_hash: str) -> Path:
        """Mojang lưu object theo hai ký tự đầu của hash — một chỗ duy nhất biết luật này.

        Hash đến từ chỉ mục asset, tức từ JSON tải về, nên cũng không tin được.
        """
        bucket = resolve_child(self.asset_objects_dir, asset_hash[:2])
        return resolve_child(bucket, asset_hash)


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
