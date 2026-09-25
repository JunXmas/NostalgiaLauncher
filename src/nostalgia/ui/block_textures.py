"""Đọc texture mặt trên/mặt bên của khối: từ jar client của người dùng, hoặc vẽ bằng code.

Tách khỏi `blocks.py` vì hai việc khác hẳn nhau: ở đây là NGUỒN ảnh (đọc zip, tô màu cỏ,
màu dự phòng), còn bên kia là HÌNH HỌC (xoay, chiếu, ghép dải).

**Giấy phép.** Texture là tài sản của Mojang. Chỉ ĐỌC jar mà chính người dùng đã tải về
máy họ; ảnh sinh ra nằm trong cache của họ, không bao giờ vào kho mã hay gói phát hành.
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter

logger = logging.getLogger(__name__)

TEXTURE_SIZE = 16

# Tên texture trong jar, cho cả hai cách đặt tên: `textures/block/` (1.13 trở lên) và
# `textures/blocks/` (trước đó). Nhiều lựa chọn cách nhau bằng `|`, lấy cái đầu tìm thấy.
BLOCK_TEXTURES: dict[str, tuple[str, str]] = {
    "grass": ("grass_block_top|grass_top", "grass_block_side|grass_side"),
    "crafting": ("crafting_table_top", "crafting_table_side|crafting_table_front"),
    "bookshelf": ("bookshelf", "bookshelf"),
    "diamond": ("diamond_block", "diamond_block"),
    "command": ("command_block_front|command_block", "command_block_side|command_block"),
    "chest": ("oak_planks|planks_oak", "oak_planks|planks_oak"),
    "redstone": ("redstone_block", "redstone_block"),
}

# Mojang lưu cỏ ở dạng XÁM rồi tô màu theo quần xã lúc chạy. Không tô thì mặt trên ra xám.
GRASS_TINT = QColor(0x79, 0xC0, 0x5A)
TINTED_NAMES = frozenset(
    {"grass_block_top", "grass_top", "grass_block_side_overlay", "grass_side_overlay"}
)

# Màu dự phòng khi chưa có jar: (mặt trên, mặt bên). Vẽ bằng code, không phải của Mojang.
FALLBACK_COLOURS: dict[str, tuple[QColor, QColor]] = {
    "grass": (QColor(0x5B, 0x8F, 0x3A), QColor(0x8B, 0x6A, 0x4A)),
    "crafting": (QColor(0xA0, 0x7A, 0x4E), QColor(0x8B, 0x69, 0x43)),
    "bookshelf": (QColor(0x8B, 0x69, 0x43), QColor(0x77, 0x5B, 0x3C)),
    "diamond": (QColor(0x4D, 0xD0, 0xD8), QColor(0x45, 0xBC, 0xC4)),
    "command": (QColor(0xC2, 0x8A, 0x5C), QColor(0xA8, 0x74, 0x4C)),
    "chest": (QColor(0xA0, 0x7A, 0x4E), QColor(0x8B, 0x69, 0x43)),
    "redstone": (QColor(0xD4, 0x24, 0x24), QColor(0xBA, 0x1E, 0x1E)),
}

@dataclass(frozen=True)
class BlockFaces:
    """Hai texture vuông của một khối: mặt trên và mặt bên."""

    top: QImage
    side: QImage


def _tinted(image: QImage, colour: QColor) -> QImage:
    """Nhân từng kênh màu với `colour`, giữ nguyên alpha."""
    out = image.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(out)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(out.rect(), colour)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return out


def shaded(image: QImage, factor: float) -> QImage:
    """Nhân độ sáng. Dùng `Multiply` của QPainter chứ không lặp từng pixel: 16x16 nhân
    6 mặt nhân 48 khung là 74 nghìn lần gọi `setPixelColor`, đủ để việc sinh dải mất
    hàng chục giây."""
    out = image.convertToFormat(QImage.Format.Format_ARGB32)
    level = int(255 * factor)
    painter = QPainter(out)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(out.rect(), QColor(level, level, level))
    # Multiply cũng nhân alpha; lấy lại alpha gốc để mép texture trong suốt không dày lên.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return out


def faces_from_jar(jar_path: Path, block: str) -> BlockFaces | None:
    """Đọc texture mặt trên/bên của một khối từ jar client. `None` nếu không có.

    Chỉ đọc, không bao giờ ghi vào jar. Tên entry lấy từ chính jar nên không ghép vào
    đường dẫn hệ thống file nào — ảnh đi thẳng vào bộ nhớ.
    """
    names = BLOCK_TEXTURES.get(block)
    if names is None:
        return None
    top_choices, side_choices = names

    try:
        with zipfile.ZipFile(jar_path) as archive:
            index: dict[str, str] = {}
            for zip_path in archive.namelist():
                if zip_path.endswith(".png") and "/textures/block" in zip_path:
                    index.setdefault(zip_path.rsplit("/", 1)[1][:-4], zip_path)

            def grab(choices: str) -> QImage | None:
                for key in choices.split("|"):
                    zip_path = index.get(key)
                    if zip_path is None:
                        continue
                    image = QImage()
                    # Không truyền tên định dạng: stub PySide6 khai `bytes`, bản chạy thật đòi `str`
                    # — chiều nào cũng có một bên đỏ. Qt tự nhận dạng từ chính dữ liệu.
                    if not image.loadFromData(archive.read(zip_path)):
                        continue
                    # Texture động (nước, lửa) là một dải dọc nhiều khung — cắt lấy khung đầu.
                    image = image.copy(0, 0, image.width(), image.width())
                    image = image.convertToFormat(QImage.Format.Format_ARGB32)
                    return _tinted(image, GRASS_TINT) if key in TINTED_NAMES else image
                return None

            top, side = grab(top_choices), grab(side_choices)
            if top is None or side is None:
                return None
            if block == "grass":
                overlay = grab("grass_block_side_overlay|grass_side_overlay")
                if overlay is not None:
                    side = side.copy()
                    painter = QPainter(side)
                    painter.drawImage(side.rect(), overlay)
                    painter.end()
            return BlockFaces(top=top, side=side)
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        # Cả một bước hỏng (không có khối nào bóc được) → `warning`, không nuốt im lặng.
        logger.warning("không đọc được texture khối từ %s: %s", jar_path, error)
        return None


def fallback_faces(block: str) -> BlockFaces:
    """Texture vẽ bằng code, dùng khi chưa cài bản chơi nào. Không phải asset của Mojang."""
    top_colour, side_colour = FALLBACK_COLOURS.get(
        block, (QColor(0x7E, 0x7E, 0x7E), QColor(0x6B, 0x6B, 0x6B))
    )

    def plate(base: QColor) -> QImage:
        image = QImage(TEXTURE_SIZE, TEXTURE_SIZE, QImage.Format.Format_ARGB32)
        image.fill(base)
        # Nhiễu tất định theo toạ độ: cùng một khối luôn ra cùng một ảnh, nên ảnh cache
        # không đổi giữa hai lần chạy và không sinh ghi đĩa thừa.
        for y in range(TEXTURE_SIZE):
            for x in range(TEXTURE_SIZE):
                jitter = ((x * 7 + y * 13) % 11 - 5) * 3
                image.setPixelColor(
                    x,
                    y,
                    QColor(
                        max(0, min(255, base.red() + jitter)),
                        max(0, min(255, base.green() + jitter)),
                        max(0, min(255, base.blue() + jitter)),
                    ),
                )
        return image

    return BlockFaces(top=plate(top_colour), side=plate(side_colour))
