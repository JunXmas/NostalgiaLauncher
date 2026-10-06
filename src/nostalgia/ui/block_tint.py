"""Tô cỏ/lá bằng colormap Minecraft, với nhiệt độ và độ ẩm quần xã plains."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QColor, QImage, QPainter


def load_biome_tint(reader: Callable[[str], bytes], block: str) -> QColor:
    """Công thức colormap vanilla: temperature=0.8, downfall=0.4 của plains."""
    colourmap = "foliage" if block.endswith("leaves") else "grass"
    image = QImage()
    if not image.loadFromData(reader(f"textures/colormap/{colourmap}.png")):
        raise ValueError("invalid Minecraft biome colormap")
    return image.pixelColor(int((1 - 0.8) * 255), int((1 - 0.4 * 0.8) * 255))


def tinted(image: QImage, colour: QColor) -> QImage:
    """Nhân màu như tintindex trong model, giữ lại alpha của texture gốc."""
    out = image.convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(out)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    painter.fillRect(out.rect(), colour)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return out
