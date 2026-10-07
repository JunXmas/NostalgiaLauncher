"""Hộp và UV đúng bố cục skin Minecraft; lớp áo/mũ có hình học riêng, giữ alpha."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QTransform

from nostalgia.ui.block_model import CUBE_FACES
from nostalgia.ui.block_textures import shaded


@dataclass(frozen=True, slots=True)
class SkinSurface:
    vertices: tuple[tuple[float, float, float], ...]
    texture: QImage


def normalize_skin(image: QImage) -> QImage:
    """Chuẩn hoá skin HD và skin 64x32 cũ; chân/tay trái cũ phải phản chiếu đúng UV."""
    legacy = image.height() * 2 == image.width()
    image = image.scaled(
        64,
        32 if legacy else 64,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    if not legacy:
        return image
    result = QImage(64, 64, QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawImage(0, 0, image)
    # Đổi trước/sau giữ nguyên; hai mặt bên hoán đổi khi đối xứng một chi.
    for ox, target_x, target_y in ((0, 16, 48), (40, 32, 48)):
        for sx, sy, width, height, tx, ty in (
            (4, 0, 4, 4, 4, 0),
            (8, 0, 4, 4, 8, 0),
            (8, 4, 4, 12, 0, 4),
            (4, 4, 4, 12, 4, 4),
            (0, 4, 4, 12, 8, 4),
            (12, 4, 4, 12, 12, 4),
        ):
            crop = image.copy(ox + sx, 16 + sy, width, height).transformed(
                QTransform().scale(-1, 1)
            )
            painter.drawImage(target_x + tx, target_y + ty, crop)
    painter.end()
    return result


def skin_surfaces(image: QImage, slim: bool) -> tuple[SkinSurface, ...]:
    """Sáu bộ phận Steve/Alex và lớp ngoài, cùng tỉ lệ vanilla 8/12/12 pixel."""
    arm = 3 if slim else 4
    surfaces: list[SkinSurface] = []
    # x,y,z là tâm hộp; y hướng xuống, chân ở y=16, đầu ở y=-16.
    for x, y, z, width, height, depth, ox, oy, ax, ay in (
        (0, -12, 0, 8, 8, 8, 0, 0, 32, 0),
        (0, -2, 0, 8, 12, 4, 16, 16, 16, 32),
        (-4 - arm / 2, -2, 0, arm, 12, 4, 40, 16, 40, 32),
        (4 + arm / 2, -2, 0, arm, 12, 4, 32, 48, 48, 48),
        (-2, 10, 0, 4, 12, 4, 0, 16, 0, 32),
        (2, 10, 0, 4, 12, 4, 16, 48, 0, 48),
    ):
        for ux, uy, dilation in ((ox, oy, 0.0), (ax, ay, 0.5 if oy == 0 else 0.25)):
            uv = {
                "top": (ux + depth, uy, width, depth),
                "bottom": (ux + depth + width, uy, width, depth),
                "left": (ux, uy + depth, depth, height),
                "front": (ux + depth, uy + depth, width, height),
                "right": (ux + depth + width, uy + depth, depth, height),
                "back": (ux + depth * 2 + width, uy + depth, width, height),
            }
            for face, corners in CUBE_FACES.items():
                vertices = tuple(
                    (
                        x + vx * (width / 2 + dilation),
                        y + vy * (height / 2 + dilation),
                        z + vz * (depth / 2 + dilation),
                    )
                    for vx, vy, vz in corners
                )
                texture = image.copy(*uv[face])
                texture = shaded(
                    texture, 1.0 if face == "top" else 0.85 if face in ("front", "back") else 0.65
                )
                surfaces.append(SkinSurface(vertices, texture))
    return tuple(surfaces)
