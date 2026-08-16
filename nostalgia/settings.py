"""Cấu hình người dùng: RAM, thư mục game, đường dẫn Java, phiên bản đang chọn."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import CONFIG_DIR, DEFAULT_GAME_DIR, LEGACY_GAME_DIR

CONFIG_PATH = CONFIG_DIR / "settings.json"
CLIENTS_PATH = CONFIG_DIR / "clients.json"

# Client ID mặc định dùng khi chưa có biến môi trường hay file clients.json.
# Client ID của public client không phải bí mật, nên nhúng sẵn ở đây để chạy
# được ngay. Đổi sang ID chính thức thì chỉ cần sửa đúng một chỗ này.
#   - microsoft: 4765445b-... là client ID công khai của Prism Launcher, dùng
#     cho kiểm thử nội bộ luồng Microsoft OAuth device code.
DEFAULT_CLIENT_IDS = {
    "microsoft": "4765445b-32ee-4b92-b7e2-aebd308c57d2",
}


def client_id(name: str, env_var: str) -> str:
    """Lấy OAuth client ID: ưu tiên biến môi trường, rồi tới file cấu hình cục
    bộ, cuối cùng là giá trị mặc định nhúng sẵn trong DEFAULT_CLIENT_IDS.

    Client ID của public client không phải bí mật (mọi launcher mã nguồn mở đều
    công khai của mình), nhưng để ngoài repo thì mỗi người tự dùng ID riêng và
    không ai vô tình commit nhầm.
    """
    value = os.environ.get(env_var, "").strip()
    if value:
        return value
    if CLIENTS_PATH.exists():
        try:
            saved = json.loads(CLIENTS_PATH.read_text()).get(name, "").strip()
        except (json.JSONDecodeError, OSError):
            saved = ""
        if saved:
            return saved
    return DEFAULT_CLIENT_IDS.get(name, "")


def save_client_id(name: str, value: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if CLIENTS_PATH.exists():
        try:
            data = json.loads(CLIENTS_PATH.read_text())
        except json.JSONDecodeError:
            pass
    data[name] = value
    fd = os.open(CLIENTS_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)


@dataclass
class Settings:
    memory_mb: int = 2048
    game_dir: str = str(DEFAULT_GAME_DIR)
    java_path: str = ""            # rỗng = tự dò theo javaVersion của phiên bản
    selected_version: str = ""     # rỗng = lấy bản release mới nhất
    show_snapshots: bool = False
    background_path: str = ""     # ảnh nền tuỳ chọn; rỗng = đảo voxel
    close_on_launch: bool = False
    _path: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or CONFIG_PATH
        if not path.exists():
            return cls(_path=path)
        raw = json.loads(path.read_text())
        raw.pop("_path", None)
        # Cấu hình cũ ghi cứng thư mục game theo tên cũ; đưa về mặc định mới.
        if raw.get("game_dir") == LEGACY_GAME_DIR:
            raw["game_dir"] = str(DEFAULT_GAME_DIR)
        known = {f for f in cls.__dataclass_fields__ if not f.startswith("_")}
        return cls(**{k: v for k, v in raw.items() if k in known}, _path=path)

    def save(self) -> None:
        path = self._path or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)

    @property
    def game_path(self) -> Path:
        return Path(self.game_dir).expanduser()
