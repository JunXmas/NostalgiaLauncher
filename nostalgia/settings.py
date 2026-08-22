"""Cấu hình người dùng: RAM, thư mục game, đường dẫn Java, phiên bản đang chọn."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import CONFIG_DIR, DEFAULT_GAME_DIR, LEGACY_GAME_DIR

CONFIG_PATH = CONFIG_DIR / "settings.json"
CLIENTS_PATH = CONFIG_DIR / "clients.json"


# Client ID mặc định: app Azure "Nostalgia Launcher" đã được Microsoft duyệt
# (Supported account types = Personal Microsoft accounts). Đây là *public client*
# dùng luồng device-code — KHÔNG có client secret, nên Client ID là công khai và
# nhúng vào mã/binary là an toàn, đúng chuẩn (giống PrismLauncher).
DEFAULT_CLIENT_IDS = {"microsoft": "868f1ec1-fa81-46de-a1f3-599156f2edd7"}


def client_id(name: str, env_var: str) -> str:
    """Lấy OAuth client ID.

    Microsoft: LUÔN dùng client ID của launcher (app Azure đã duyệt) — không cho
    người chơi đổi, để mọi đăng nhập đi qua đúng app này. Các dịch vụ khác (vd
    Google) vẫn cho override qua env / file cấu hình.
    """
    if name == "microsoft":
        return DEFAULT_CLIENT_IDS["microsoft"]
    value = os.environ.get(env_var, "").strip()
    if value:
        return value
    if CLIENTS_PATH.exists():
        try:
            saved = json.loads(CLIENTS_PATH.read_text()).get(name, "").strip()
            if saved:
                return saved
        except (json.JSONDecodeError, OSError):
            pass
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
    _atomic_write_json(CLIENTS_PATH, data)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Ghi JSON an toàn: file tạm + os.replace, không bao giờ để lại file cắt dở."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


@dataclass
class Settings:
    memory_mb: int = 2048
    game_dir: str = str(DEFAULT_GAME_DIR)
    java_path: str = ""            # rỗng = tự dò theo javaVersion của phiên bản
    selected_version: str = ""     # rỗng = lấy bản release mới nhất
    show_snapshots: bool = False
    background_path: str = ""     # ảnh nền tuỳ chọn; rỗng = ảnh lá xanh mặc định
    close_on_launch: bool = False
    check_updates: bool = True    # tự tìm bản mới trên GitHub khi khởi động
    aero_ui: bool = True          # lắp & khoá resource pack Aero UI mỗi lần chạy
    seen_welcome: bool = False    # đã hiện onboarding lần đầu chưa (khỏi hiện lại)
    menu_dark: bool = False       # panorama menu: False=ngày (light), True=đêm (dark)
    panorama_theme: str = ""      # id theme panorama đã chọn (rỗng = day/night theo menu_dark)
    # Backend chung (Cloudflare Worker): upload skin + khôi phục danh tính.
    backend_url: str = "https://nostalgia-backend.junbob.workers.dev"
    language: str = "en"          # mã ngôn ngữ giao diện (xem nostalgia/i18n.py)
    curseforge_key: str = ""      # API key CurseForge (tuỳ chọn) để duyệt/tìm modpack
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
        obj = cls(**{k: v for k, v in raw.items() if k in known}, _path=path)
        obj._heal_game_dir()
        return obj

    def _heal_game_dir(self) -> None:
        """Lùi game_dir về mặc định nếu nó trỏ vào chỗ không dùng được.

        Kho game (versions/libraries/assets/instances) phải nằm ở nơi bền vững.
        Nếu game_dir trỏ vào một thư mục tạm của hệ điều hành (bị xoá mỗi lần khởi
        động lại) hoặc một đường dẫn đã biến mất, thì PLAY sẽ trỏ vào một kho rỗng
        và "không launch được game" mà không rõ lý do. Trường hợp đó ta âm thầm
        dùng lại thư mục mặc định — nơi dữ liệu thường vẫn còn — thay vì chịu chết.
        Chỉ sửa trong bộ nhớ; không tự ghi đè file để khỏi bất ngờ ép đường dẫn.
        """
        default = str(DEFAULT_GAME_DIR)
        if self.game_dir == default:
            return
        try:
            here = Path(self.game_dir).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            self.game_dir = default
            return
        tmp_root = Path(tempfile.gettempdir()).resolve()
        under_tmp = here == tmp_root or tmp_root in here.parents
        if under_tmp or not here.exists():
            self.game_dir = default

    def save(self) -> None:
        path = self._path or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        _atomic_write_json(path, data)

    @property
    def game_path(self) -> Path:
        return Path(self.game_dir).expanduser()
