"""Sinh dải sprite khối Minecraft xoay, dùng làm icon thanh bên.

Vì sao sinh sẵn thay vì xoay lúc chạy: xoay một khối lập phương thật cần Qt3D hoặc
shader, mà `MicaBackdrop.qml` đã ghi rõ hiệu ứng dựng bằng shader không vẽ được dưới GL
phần mềm. Một dải ảnh + `AnimatedSprite` thì chỉ là một `Image` đổi khung — chạy ở mọi
nơi, và không tính gì lúc chạy.

**Giấy phép.** Texture là tài sản của Mojang. Ở đây chỉ ĐỌC jar mà chính người dùng đã
tải về máy họ, và ảnh sinh ra nằm trong thư mục cache của họ — không bao giờ nằm trong
kho mã nguồn hay trong gói phát hành. Không có jar thì rơi về texture vẽ bằng code, nên
launcher vẫn chạy đủ chức năng trước khi cài bản chơi đầu tiên.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter, QPolygonF, QTransform

from nostalgia.ui.block_textures import (
    BLOCK_TEXTURES,
    BlockFaces,
    faces_from_jar,
    fallback_faces,
    shaded,
)

logger = logging.getLogger(__name__)

FRAME_SIZE = 64  # cạnh mỗi khung, px
FRAME_COUNT = 48  # số khung một vòng
SUPERSAMPLE = 3  # vẽ gấp 3 rồi thu nhỏ: cạnh khối hết răng cưa
TILT_DEGREES = 22.0  # nghiêng xuống, giống icon vật phẩm trong game
START_DEGREES = 45.0  # khung 0 nhìn 3/4, không nhìn thẳng mặt

# Khối đơn vị tâm ở gốc; mỗi mặt là 4 đỉnh thuận chiều kim đồng hồ khi nhìn từ ngoài.
CUBE_FACES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "front": ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
    "back": ((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)),
    "right": ((1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)),
    "left": ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
    "top": ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
    "bottom": ((-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)),
}
# Mặt nào lấy texture nào, và độ sáng — giống cách game tô: trên sáng nhất, hai bên tối dần.
FACE_SOURCE: dict[str, tuple[str, float]] = {
    "top": ("top", 1.00),
    "bottom": ("top", 0.55),
    "front": ("side", 0.80),
    "back": ("side", 0.80),
    "right": ("side", 0.62),
    "left": ("side", 0.62),
}


def _rotate(
    point: tuple[float, float, float], yaw: float, pitch: float
) -> tuple[float, float, float]:
    x, y, z = point
    cosine, sine = math.cos(yaw), math.sin(yaw)
    x, z = x * cosine + z * sine, -x * sine + z * cosine
    cosine, sine = math.cos(pitch), math.sin(pitch)
    y, z = y * cosine - z * sine, y * sine + z * cosine
    return x, y, z


def _project(point: tuple[float, float, float], size: int) -> tuple[float, float, float]:
    x, y, z = point
    scale = size * 0.33  # ở 0,33 khối xoay vẫn không chạm mép khung
    return size / 2 + x * scale, size / 2 + y * scale, z


def render_frame(faces: BlockFaces, angle_degrees: float, size: int) -> QImage:
    """Vẽ một khung của khối xoay ở góc `angle_degrees`."""
    yaw = math.radians(angle_degrees)
    pitch = math.radians(TILT_DEGREES)
    frame = QImage(size, size, QImage.Format.Format_ARGB32)
    frame.fill(Qt.GlobalColor.transparent)

    visible: list[tuple[float, str, list[tuple[float, float]]]] = []
    for name, vertices in CUBE_FACES.items():
        projected = [_project(_rotate(vertex, yaw, pitch), size) for vertex in vertices]
        (x0, y0, _), (x1, y1, _), (x2, y2, _) = projected[0], projected[1], projected[2]
        # Mặt có quay ra ngoài không? Tích có hướng 2D của hai cạnh đầu. Màn hình có trục y
        # hướng XUỐNG, nên mặt trước cho tích ÂM — dấu ngược lại là khối lộn ngược.
        if (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) >= 0:
            continue
        depth = sum(point[2] for point in projected) / 4
        visible.append((depth, name, [(point[0], point[1]) for point in projected]))

    painter = QPainter(frame)
    # Xa vẽ trước, gần vẽ sau — không có z-buffer nên thứ tự chính là độ sâu.
    for _, name, quad in sorted(visible, key=lambda face: face[0], reverse=True):
        source_key, brightness = FACE_SOURCE[name]
        texture = shaded(faces.top if source_key == "top" else faces.side, brightness)
        transform = QTransform()
        source_quad = QPolygonF(
            [
                QPointF(0, 0),
                QPointF(texture.width(), 0),
                QPointF(texture.width(), texture.height()),
                QPointF(0, texture.height()),
            ]
        )
        target_quad = QPolygonF([QPointF(x, y) for x, y in quad])
        if not QTransform.quadToQuad(source_quad, target_quad, transform):
            continue
        painter.save()
        painter.setClipRect(frame.rect())
        painter.setTransform(transform)
        # NEAREST: texel phải vuông, làm mượt ở đây là mất luôn nét pixel của Minecraft.
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(0, 0, texture)
        painter.restore()
    painter.end()
    return frame


def render_strip(faces: BlockFaces) -> QImage:
    """Dải ngang `FRAME_COUNT` khung, mỗi khung `FRAME_SIZE` px, khép kín một vòng."""
    strip = QImage(FRAME_SIZE * FRAME_COUNT, FRAME_SIZE, QImage.Format.Format_ARGB32)
    strip.fill(Qt.GlobalColor.transparent)
    painter = QPainter(strip)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    for index in range(FRAME_COUNT):
        angle = START_DEGREES + index * 360 / FRAME_COUNT
        # Vẽ to gấp SUPERSAMPLE rồi thu nhỏ: cạnh khối mượt mà texel vẫn vuông. Đây là
        # cách khử răng cưa duy nhất áp được cho ảnh sinh sẵn — MSAA chỉ lo cảnh đang vẽ.
        large = render_frame(faces, angle, FRAME_SIZE * SUPERSAMPLE)
        small = large.scaled(
            FRAME_SIZE,
            FRAME_SIZE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(index * FRAME_SIZE, 0, small)
    painter.end()
    return strip


def ensure_strips(cache_dir: Path, jar_path: Path | None) -> dict[str, Path]:
    """Sinh (nếu thiếu) dải sprite cho mọi khối, trả về map tên khối -> đường dẫn ảnh.

    Có sẵn thì không vẽ lại: sinh một dải tốn khoảng một giây, và thanh bên dựng ở mỗi
    lần mở launcher.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    source = "jar" if jar_path is not None and jar_path.is_file() else "code"
    strips: dict[str, Path] = {}
    for block in BLOCK_TEXTURES:
        target = cache_dir / f"{block}_{source}.png"
        strips[block] = target
        if target.is_file():
            continue
        faces = (
            faces_from_jar(jar_path, block) if jar_path is not None and source == "jar" else None
        )
        if faces is None:
            faces = fallback_faces(block)
        # Đuôi `.png` đã đủ cho Qt chọn định dạng (xem ghi chú ở `loadFromData`).
        if not render_strip(faces).save(str(target)):
            logger.warning("không ghi được dải sprite khối: %s", target)
            strips.pop(block)
    return strips
