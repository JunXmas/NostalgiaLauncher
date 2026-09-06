"""Bảng biến `${...}` mà Mojang chờ trong tham số khởi động.

Gom một chỗ, vì đây là **bảng đối chiếu** chứ không phải logic: rải nó vào chỗ dựng lệnh thì
mỗi lần thêm một đời game lại phải đi tìm. Mười tám biến dưới đây phủ toàn bộ những gì xuất
hiện trong JSON thật của 1.5 tới 1.21, kể cả các biến chỉ đời cũ mới dùng
(`user_properties`, `auth_session`, `game_assets`) và các biến chỉ bản mod mới dùng
(`library_directory`, `classpath_separator`).

Nhận đối số rời chứ không nhận một đối tượng ngữ cảnh: module này không được biết gì về
cách dựng lệnh, nhờ vậy nó không phụ thuộc ngược lên `command.py`.
"""

from __future__ import annotations

from pathlib import Path

from nostalgia.account.model import PlayerProfile
from nostalgia.version.meta import VersionMeta

# Đời ≤1.7 chờ một đối tượng JSON ở đây. Rỗng là hợp lệ; bỏ trống hẳn thì game đời đó đọc
# tham số kế tiếp làm giá trị và hỏng theo cách rất khó đoán.
EMPTY_USER_PROPERTIES = "{}"

DEFAULT_VERSION_TYPE = "release"


def build_launch_variables(
    version_meta: VersionMeta,
    player_profile: PlayerProfile,
    *,
    game_dir: Path,
    assets_root: Path,
    game_assets_dir: Path,
    natives_dir: Path,
    libraries_dir: Path,
    classpath_arg: str,
    classpath_separator: str,
    launcher_name: str,
    launcher_version: str,
    window_width: int | None = None,
    window_height: int | None = None,
) -> dict[str, str]:
    """Dựng bảng thay thế. Mọi giá trị đều là `str` — đây là biên với `argv`."""
    undashed_uuid = player_profile.undashed_uuid
    variables = {
        # Danh tính
        "auth_player_name": player_profile.player_name,
        "auth_uuid": undashed_uuid,
        "auth_access_token": player_profile.access_token,
        "auth_session": f"token:{player_profile.access_token}:{undashed_uuid}",
        "user_type": player_profile.user_type,
        "user_properties": EMPTY_USER_PROPERTIES,
        "clientid": "",
        "auth_xuid": "",
        # Phiên bản. `version_name` là mã bản SỞ HỮU client jar chứ không phải id của loader:
        # Forge dùng `-DignoreList=…,${version_name}.jar` để bỏ qua client jar khỏi module
        # path; đặt id Forge vào đây thì jar `1.20.1.jar` bị nạp thành module `_1._20._1` và
        # Java báo hai module cùng xuất `net.minecraft.data`. Với bản thuần hai id trùng nhau.
        "version_name": version_meta.jar_version_id or version_meta.version_id,
        "version_type": version_meta.release_type or DEFAULT_VERSION_TYPE,
        "profile_name": launcher_name,
        # Thư mục
        "game_directory": str(game_dir),
        "assets_root": str(assets_root),
        "game_assets": str(game_assets_dir),
        "assets_index_name": version_meta.assets_id or "",
        "natives_directory": str(natives_dir),
        "library_directory": str(libraries_dir),
        # Máy ảo
        "classpath": classpath_arg,
        "classpath_separator": classpath_separator,
        "launcher_name": launcher_name,
        "launcher_version": launcher_version,
    }
    if window_width is not None and window_height is not None:
        variables["resolution_width"] = str(window_width)
        variables["resolution_height"] = str(window_height)
    return variables
