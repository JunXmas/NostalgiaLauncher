"""Preview skin và model bằng cùng hệ tọa độ rig, chỉ dựng ở worker."""

import math
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt, QUrl
from PySide6.QtGui import (
    QImage,
    QImageReader,
    QMatrix4x4,
    QPainter,
    QPainterPath,
    QQuaternion,
    QTransform,
    QVector3D,
)

from nostalgia.model.cosmetic import CosmeticAsset
from nostalgia.ui.skin_mesh import normalize_skin, skin_surfaces


@dataclass(frozen=True, slots=True)
class MarketFace:
    points: tuple[tuple[float, ...], ...]
    texture: QImage
    double_sided: bool = False


def build_market_faces(
    source: str, slim: bool, cosmetic: CosmeticAsset | tuple[CosmeticAsset, ...] | None
) -> tuple[MarketFace, ...]:
    url = QUrl(source)
    path = (
        Path(url.toLocalFile())
        if url.isLocalFile()
        else Path(__file__).resolve().parents[1] / "skin/defaults/steve.png"
    )
    if not path.is_file() or path.stat().st_size > 512_000:
        path = Path(__file__).resolve().parents[1] / "skin/defaults/steve.png"
    reader = QImageReader(str(path), b"png")
    size = reader.size()
    if size.width() > 1024 or size.height() > 1024 or size.width() < 64:
        raise ValueError("Invalid preview skin dimensions")
    skin = reader.read()
    if skin.isNull():
        raise ValueError("Unable to decode preview skin")
    faces = [
        MarketFace(
            tuple(
                (*v, u, w)
                for v, (u, w) in zip(
                    surface.vertices, ((0, 0), (1, 0), (1, 1), (0, 1)), strict=True
                )
            ),
            surface.texture,
        )
        for surface in skin_surfaces(normalize_skin(skin), slim)
    ]
    if cosmetic is None:
        return tuple(faces)
    cosmetics = cosmetic if isinstance(cosmetic, tuple) else (cosmetic,)
    for cosmetic in cosmetics:
        buffer = QBuffer()
        buffer.setData(cosmetic.texture_png)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        reader = QImageReader(buffer, b"png")
        size = reader.size()
        if not 0 < size.width() <= 512 or not 0 < size.height() <= 512:
            raise ValueError("Cosmetic texture dimensions exceed limit")
        texture = reader.read()
        if texture.isNull():
            raise ValueError("Unable to decode cosmetic texture")
        offsets = {
            "head": (0, 0, 0),
            "body": (0, 0, 0),
            "right_arm": (-5, 2, 0),
            "left_arm": (5, 2, 0),
            "right_leg": (-1.9, 12, 0),
            "left_leg": (1.9, 12, 0),
        }
        for part in cosmetic.parts:
            matrices: list[QMatrix4x4] = []
            for node in part.nodes:
                matrix = (
                    QMatrix4x4(matrices[node.parent_index])
                    if node.parent_index >= 0
                    else QMatrix4x4()
                )
                matrix.translate(*node.translation)
                x, y, z, w = node.rotation
                matrix.rotate(QQuaternion(w, x, y, z))
                matrices.append(matrix)
                ox, oy, oz = offsets[part.bone]
                for p in range(0, len(node.vertices), 32):
                    points: list[tuple[float, ...]] = []
                    for k in range(4):
                        values = node.vertices[p + k * 8 : p + k * 8 + 8]
                        position = matrix.map(QVector3D(*values[:3]))
                        points.append(
                            (
                                position.x() * 16 + ox,
                                16 - position.y() * 16 + oy,
                                position.z() * 16 + oz,
                                values[3],
                                values[4],
                            )
                        )
                    faces.append(MarketFace(tuple(points), texture, True))
    return tuple(faces)


def draw_triangle(
    painter: QPainter, texture: QImage, vertices: tuple[tuple[float, ...], ...]
) -> None:
    (x0, y0, u0, v0), (x1, y1, u1, v1), (x2, y2, u2, v2) = vertices
    u0, u1, u2 = u0 * texture.width(), u1 * texture.width(), u2 * texture.width()
    v0, v1, v2 = v0 * texture.height(), v1 * texture.height(), v2 * texture.height()
    du1, du2, dv1, dv2 = u1 - u0, u2 - u0, v1 - v0, v2 - v0
    determinant = du1 * dv2 - du2 * dv1
    if abs(determinant) < 1e-8:
        return
    a = ((x1 - x0) * dv2 - (x2 - x0) * dv1) / determinant
    c = ((x2 - x0) * du1 - (x1 - x0) * du2) / determinant
    b = ((y1 - y0) * dv2 - (y2 - y0) * dv1) / determinant
    d = ((y2 - y0) * du1 - (y1 - y0) * du2) / determinant
    clip = QPainterPath()
    clip.moveTo(x0, y0)
    clip.lineTo(x1, y1)
    clip.lineTo(x2, y2)
    clip.closeSubpath()
    painter.save()
    painter.setClipPath(clip)
    painter.setTransform(QTransform(a, b, c, d, x0 - a * u0 - c * v0, y0 - b * u0 - d * v0))
    painter.drawImage(0, 0, texture)
    painter.restore()


def render_market(faces: tuple[MarketFace, ...], yaw: float) -> QImage:
    image = QImage(512, 640, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    angle, pitch = math.radians(yaw), math.radians(-12)
    projected: list[tuple[float, MarketFace, tuple[tuple[float, ...], ...]]] = []
    for face in faces:
        points = []
        depth = 0.0
        for x, y, z, u, v in face.points:
            rx, rz = (
                x * math.cos(angle) + z * math.sin(angle),
                -x * math.sin(angle) + z * math.cos(angle),
            )
            ry, rz = (
                y * math.cos(pitch) - rz * math.sin(pitch),
                y * math.sin(pitch) + rz * math.cos(pitch),
            )
            points.append((256 + rx * 15, 320 + ry * 15, u, v))
            depth += rz
        a, b, c = points[:3]
        if (
            not face.double_sided
            and (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0
        ):
            continue
        projected.append((depth, face, tuple(points)))
    painter = QPainter(image)
    for _, face, projected_points in sorted(projected, key=lambda face: face[0]):
        for indices in ((0, 1, 2), (0, 2, 3)):
            draw_triangle(painter, face.texture, tuple(projected_points[k] for k in indices))
    painter.end()
    return image
