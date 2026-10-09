"""Mọi icon dùng model/texture Minecraft thật; thiếu client thì dùng bản vanilla đóng kèm."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter

from nostalgia.ui.block_model import BlockModel, load_block_model

# Tên dùng ở giao diện ánh xạ tới tên model Minecraft, không dựng khối bằng màu giả.
BLOCK_MODELS: dict[str, str] = {
    "grass": "grass_block",
    "crafting": "crafting_table",
    "bookshelf": "bookshelf",
    "diamond": "diamond_block",
    "amethyst": "amethyst_block",
    "command": "command_block",
    "barrel": "barrel",
    "redstone": "redstone_block",
    "beacon": "beacon",
}


@dataclass(frozen=True, slots=True)
class BlockFaces:
    """Texture đại diện cho test/renderer cũ; mọi icon thật có các mặt/UV trong model."""

    top: QImage
    side: QImage
    model: BlockModel | None = None


def _model_faces(block: str, jar_path: Path | None = None) -> BlockFaces:
    model = load_block_model(BLOCK_MODELS[block], jar_path)
    tops = [s.texture for s in model.surfaces if s.face == "top" and s.layer == 1]
    sides = [s.texture for s in model.surfaces if s.face == "front" and s.layer == 1]
    top = tops[-1] if tops else next(s.texture for s in model.surfaces if s.face == "top")
    side = sides[-1] if sides else next(s.texture for s in model.surfaces if s.face == "front")
    return BlockFaces(top=top, side=side, model=model)


def shaded(image: QImage, factor: float) -> QImage:
    """Nhân độ sáng mặt khối, giữ alpha và nét texture gốc."""
    out = image.convertToFormat(QImage.Format.Format_ARGB32)
    level = int(255 * factor)
    painter = QPainter(out)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(out.rect(), QColor(level, level, level))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return out


def faces_from_jar(jar_path: Path, block: str) -> BlockFaces | None:
    """Ưu tiên tài nguyên client; phần thiếu lấy từ model/texture vanilla gốc đóng kèm."""
    return _model_faces(block, jar_path) if block in BLOCK_MODELS else None


def fallback_faces(block: str) -> BlockFaces:
    """Chưa có game vẫn dùng Minecraft Java 1.20.1 thật, không sinh texture giả."""
    return _model_faces(block)
