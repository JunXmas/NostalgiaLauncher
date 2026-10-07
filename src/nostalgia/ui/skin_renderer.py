"""Chiếu mesh skin 3D và tô texture bằng QPainter; dùng được cả khi thiếu driver GPU."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter, QPolygonF, QTransform

from nostalgia.ui.skin_mesh import SkinSurface

FRAME_WIDTH = 128
FRAME_HEIGHT = 256
FRAME_COUNT = 72
SUPERSAMPLE = 2


def render_skin(surfaces: tuple[SkinSurface, ...], frame_index: int) -> QImage:
    """Đủ 360° theo bước 5°; cull mặt khuất, sắp độ sâu cả thân và lớp ngoài."""
    yaw = math.radians(frame_index * 360 / FRAME_COUNT)
    pitch = math.radians(-12)
    cosine, sine = math.cos(yaw), math.sin(yaw)
    pitch_cosine, pitch_sine = math.cos(pitch), math.sin(pitch)
    width, height = FRAME_WIDTH * SUPERSAMPLE, FRAME_HEIGHT * SUPERSAMPLE
    scale = height / 37
    visible: list[tuple[float, QImage, QPolygonF]] = []
    for surface in surfaces:
        projected: list[tuple[float, float, float]] = []
        for x, y, z in surface.vertices:
            rx, rz = x * cosine + z * sine, -x * sine + z * cosine
            ry, rz = y * pitch_cosine - rz * pitch_sine, y * pitch_sine + rz * pitch_cosine
            projected.append((width / 2 + rx * scale, height / 2 + ry * scale, rz))
        a, b, c = projected[:3]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0:
            continue
        quad = QPolygonF([QPointF(x, y) for x, y, _z in projected])
        visible.append((sum(p[2] for p in projected) / 4, surface.texture, quad))
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    for _depth, texture, quad in sorted(visible, key=lambda face: face[0]):
        source_quad = QPolygonF(
            [
                QPointF(0, 0),
                QPointF(texture.width(), 0),
                QPointF(texture.width(), texture.height()),
                QPointF(0, texture.height()),
            ]
        )
        transform = QTransform()
        if QTransform.quadToQuad(source_quad, quad, transform):
            painter.setTransform(transform)
            painter.drawImage(0, 0, texture)
    painter.end()
    return image.scaled(
        FRAME_WIDTH,
        FRAME_HEIGHT,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
