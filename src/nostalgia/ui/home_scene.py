"""Ghép góc Minecraft nhỏ từ model vanilla, không vẽ khối hoặc texture thay thế."""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter, QPolygonF, QTransform

from nostalgia.ui.block_model import load_block_model
from nostalgia.ui.block_textures import shaded
from nostalgia.ui.blocks import FACE_SOURCE, _rotate


@dataclass(frozen=True, slots=True)
class SceneBlock:
    block: str
    position: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class SceneFace:
    depth: float
    layer: int
    texture: QImage
    vertices: tuple[tuple[float, float, float], ...]


def scene_blocks() -> tuple[SceneBlock, ...]:
    """Mảnh đất, cây sồi, bàn chế tạo và glowstone đều là các khối vanilla."""
    ground = tuple(
        SceneBlock("grass_block", (x * 2, 0, z * 2)) for x in (-1, 0, 1) for z in (-1, 0, 1)
    )
    return (
        *ground,
        SceneBlock("dirt", (0, 2, 0)),
        SceneBlock("dirt", (2, 2, 0)),
        SceneBlock("dirt", (0, 2, 2)),
        SceneBlock("stone", (0, 4, 0)),
        SceneBlock("oak_log", (0, -2, -2)),
        SceneBlock("oak_log", (0, -4, -2)),
        SceneBlock("oak_leaves", (0, -6, -2)),
        SceneBlock("oak_leaves", (-2, -6, -2)),
        SceneBlock("oak_leaves", (2, -6, -2)),
        SceneBlock("oak_leaves", (0, -6, 0)),
        SceneBlock("oak_leaves", (0, -8, -2)),
        SceneBlock("crafting_table", (-2, -2, 2)),
        SceneBlock("glowstone", (2, -2, 2)),
    )


def render_home_scene(size: int = 1024) -> QImage:
    """Vẽ ảnh trong suốt ở camera 3/4; geometry, UV và texel lấy từ model Minecraft."""
    faces: list[SceneFace] = []
    models = {placed.block: load_block_model(placed.block) for placed in scene_blocks()}
    for placed in scene_blocks():
        for surface in models[placed.block].surfaces:
            vertices = tuple(
                _rotate(
                    (
                        vertex[0] + placed.position[0],
                        vertex[1] + placed.position[1],
                        vertex[2] + placed.position[2],
                    ),
                    math.radians(225),
                    math.radians(30),
                )
                for vertex in surface.vertices
            )
            (x0, y0, _), (x1, y1, _), (x2, y2, _) = vertices[:3]
            front = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) < 0
            if not front:
                continue
            faces.append(
                SceneFace(
                    sum(v[2] for v in vertices) / 4,
                    surface.layer,
                    shaded(surface.texture, FACE_SOURCE[surface.face][1]),
                    vertices,
                )
            )
    xs = [v[0] for face in faces for v in face.vertices]
    ys = [v[1] for face in faces for v in face.vertices]
    scale = size * 0.84 / max(max(xs) - min(xs), max(ys) - min(ys))
    offset_x = size / 2 - (max(xs) + min(xs)) / 2 * scale
    offset_y = size / 2 - (max(ys) + min(ys)) / 2 * scale
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    for face in sorted(faces, key=lambda face: (-face.depth, face.layer)):
        source = QPolygonF(
            [
                QPointF(0, 0),
                QPointF(face.texture.width(), 0),
                QPointF(face.texture.width(), face.texture.height()),
                QPointF(0, face.texture.height()),
            ]
        )
        target = QPolygonF(
            [QPointF(v[0] * scale + offset_x, v[1] * scale + offset_y) for v in face.vertices]
        )
        transform = QTransform()
        if not QTransform.quadToQuad(source, target, transform):
            continue
        painter.save()
        painter.setTransform(transform)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(0, 0, face.texture)
        painter.restore()
    painter.end()
    return image
