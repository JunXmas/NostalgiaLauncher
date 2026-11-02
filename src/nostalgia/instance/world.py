"""Thế giới của một bản chơi — dữ liệu cho cửa sổ chọn world khi bấm Chơi.

Chỉ đọc đĩa. Liệt kê `saves/*/level.dat`, đọc tên / mốc chơi cuối / chế độ / hardcore / cheat
bằng bộ đọc NBT tối giản và `icon.png` đã kiểm. `level.dat` hỏng vẫn được liệt kê bằng tên thư
mục và mtime — vẫn vào chơi được, game tự dựng lại file. Gọi từ luồng nền: trăm thế giới là
trăm lần mở file.
"""

from __future__ import annotations

import base64
import os
import struct
from dataclasses import dataclass
from pathlib import Path

from nostalgia.instance.nbt import load_level_summary
from nostalgia.instance.server_list import PNG_SIGNATURE
from nostalgia.instance.stats import LEVEL_FILE_NAME, SAVES_DIR_NAME

MINUTE_SECONDS = 60
HOUR_SECONDS = 60 * MINUTE_SECONDS
DAY_SECONDS = 24 * HOUR_SECONDS
MONTH_SECONDS = 30 * DAY_SECONDS
ICON_FILE_NAME = "icon.png"
# Game ghi icon 64x64 (vài KB). Trần byte chặn file khổng lồ; trần cạnh chặn PNG nhỏ khai kích
# thước khổng lồ (bom giải nén) trước khi QML kịp giải mã.
MAX_ICON_BYTES = 256 * 1024
MAX_ICON_SIDE = 512
PNG_HEADER_BYTES = 24  # chữ ký 8 + độ dài 4 + "IHDR" 4 + rộng 4 + cao 4


@dataclass(frozen=True, slots=True)
class SavedWorld:
    """Một thế giới trong `saves/`. `world_folder` là tên thư mục — chính là giá trị Minecraft
    nhận ở `--quickPlaySingleplayer`. `game_type`: 0 sinh tồn, 1 sáng tạo, 2 phiêu lưu, 3 khán
    giả. `icon_url` là URL `data:` cho `Image` của QML hoặc rỗng."""

    world_folder: str
    world_name: str
    last_played_at: int
    last_played_text: str
    game_type: int
    hardcore: bool
    cheats: bool
    icon_url: str


def format_time_ago(seconds: int) -> str:
    """ "vừa xong" / "N phút trước" / "N giờ trước" / "N ngày trước" / "N tháng trước"."""
    if seconds < MINUTE_SECONDS:
        return "vừa xong"
    if seconds < HOUR_SECONDS:
        return f"{seconds // MINUTE_SECONDS} phút trước"
    if seconds < DAY_SECONDS:
        return f"{seconds // HOUR_SECONDS} giờ trước"
    if seconds < MONTH_SECONDS:
        return f"{seconds // DAY_SECONDS} ngày trước"
    return f"{seconds // MONTH_SECONDS} tháng trước"


def world_icon_url(world_dir: Path) -> str:
    """`icon.png` thành URL `data:`; thiếu, quá to, không phải PNG hay khai kích thước quá cỡ →
    rỗng (QML hiện ảnh mặc định)."""
    try:
        with (world_dir / ICON_FILE_NAME).open("rb") as stream:
            payload = stream.read(MAX_ICON_BYTES + 1)
    except OSError:
        return ""
    if len(payload) > MAX_ICON_BYTES or len(payload) < PNG_HEADER_BYTES:
        return ""
    if not payload.startswith(PNG_SIGNATURE) or payload[12:16] != b"IHDR":
        return ""
    width, height = struct.unpack(">II", payload[16:PNG_HEADER_BYTES])
    if not (0 < width <= MAX_ICON_SIDE and 0 < height <= MAX_ICON_SIDE):
        return ""
    return "data:image/png;base64," + base64.b64encode(payload).decode("ascii")


def _level_files(game_dir: Path) -> list[tuple[float, Path]]:
    """`(mtime, đường dẫn level.dat)` của mọi thế giới; thư mục không có level.dat bị bỏ qua."""
    saves_dir = game_dir / SAVES_DIR_NAME
    if not saves_dir.is_dir():
        return []
    found: list[tuple[float, Path]] = []
    with os.scandir(saves_dir) as listing:
        for candidate in listing:
            if not candidate.is_dir():
                continue
            level_path = Path(candidate.path) / LEVEL_FILE_NAME
            try:
                found.append((level_path.stat().st_mtime, level_path))
            except OSError:
                continue
    return found


def list_worlds(game_dir: Path, *, now: float) -> tuple[SavedWorld, ...]:
    """Thế giới của một bản chơi, chơi gần nhất trước."""
    worlds: list[SavedWorld] = []
    for modified_at, level_path in _level_files(game_dir):
        summary = load_level_summary(level_path)
        if summary is not None and summary.last_played_ms > 0:
            last_played_at = summary.last_played_ms // 1000
        else:
            last_played_at = int(modified_at)
        worlds.append(
            SavedWorld(
                world_folder=level_path.parent.name,
                world_name=(summary.world_name if summary else "") or level_path.parent.name,
                last_played_at=last_played_at,
                last_played_text=format_time_ago(max(0, int(now) - last_played_at)),
                game_type=summary.game_type if summary else 0,
                hardcore=summary is not None and summary.hardcore,
                cheats=summary is not None and summary.cheats,
                icon_url=world_icon_url(level_path.parent),
            )
        )
    worlds.sort(key=lambda world: world.last_played_at, reverse=True)
    return tuple(worlds)
