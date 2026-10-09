"""Áo choàng vanilla 10x16x1, UV 64x32, đặt và nghiêng sau lưng nhân vật."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from nostalgia.ui.block_model import CUBE_FACES
from nostalgia.ui.block_textures import shaded
from nostalgia.ui.skin_mesh import SkinSurface


def cape_surfaces(image: QImage) -> tuple[SkinSurface, ...]:
    image = image.scaled(64, 32, Qt.AspectRatioMode.IgnoreAspectRatio)
    uv = {
        "top": (1, 0, 10, 1),
        "bottom": (11, 0, 10, 1),
        "left": (0, 1, 1, 16),
        "front": (1, 1, 10, 16),
        "right": (11, 1, 1, 16),
        "back": (12, 1, 10, 16),
    }
    angle = math.radians(10)
    surfaces = []
    for face, corners in CUBE_FACES.items():
        vertices = tuple(
            (
                x * 5,
                -8 + (y + 1) * 8 * math.cos(angle) + z * 0.5 * math.sin(angle),
                -2.8 - (y + 1) * 8 * math.sin(angle) + z * 0.5 * math.cos(angle),
            )
            for x, y, z in corners
        )
        # Mặt ngoài lưng dùng hoạ tiết chính của cape.
        texture = image.copy(
            *uv["front" if face == "back" else "back" if face == "front" else face]
        )
        surfaces.append(SkinSurface(vertices, shaded(texture, 0.85)))
    return tuple(surfaces)
