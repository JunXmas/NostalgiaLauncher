"""Ảnh nền sinh bằng thuật toán.

Không dùng artwork của Mojang: EULA cấm phát tán nội dung của họ, và ảnh tự sinh
thì đổi màu theo mùa/theo instance được. Người dùng vẫn thay bằng ảnh riêng được.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap, QPolygonF

# Mỗi khối lấy 3 sắc độ: mặt trên hứng sáng, hai mặt bên tối dần.
BLOCKS = {
    "grass": (QColor(150, 214, 108), QColor(112, 176, 80), QColor(88, 144, 64)),
    "dirt": (QColor(150, 112, 78), QColor(118, 87, 60), QColor(96, 70, 48)),
    "stone": (QColor(146, 148, 152), QColor(116, 118, 122), QColor(94, 96, 100)),
    "water": (QColor(120, 186, 236), QColor(92, 156, 210), QColor(72, 128, 184)),
    "sand": (QColor(224, 210, 160), QColor(196, 182, 136), QColor(168, 154, 112)),
}

TW, TH, CH = 34, 17, 20  # bề ngang, bề sâu, chiều cao một khối trên màn hình

# Mây khối rải trên trời: cho tấm kính sidebar/topbar có hoạ tiết để làm mờ,
# nếu không kính nằm trên nền trời phẳng sẽ trông như mảng xám chết.
CLOUDS = [(0.02, 0.07, 7, 2), (0.58, 0.04, 8, 2), (0.30, 0.14, 5, 1)]


def _draw_clouds(p: QPainter, width: int, height: int) -> None:
    unit = max(14, width // 46)
    for fx, fy, cw, chh in CLOUDS:
        x0, y0 = fx * width, fy * height
        for row in range(chh):
            for col in range(cw):
                if (row * 7 + col * 3) % 5 == 4:
                    continue  # khoét vài ô cho rìa mây không thành hình chữ nhật
                p.fillRect(QRectF(x0 + col * unit, y0 + row * unit * 0.62, unit, unit * 0.62),
                           QColor(255, 255, 255, 10 if row else 15))


def _height(x: int, y: int) -> int:
    """Địa hình tất định — cùng seed thì cùng cảnh, tiện chụp lại để so sánh."""
    return round(2.6 + 1.7 * math.sin(x * 0.55) + 1.3 * math.cos(y * 0.42) + 0.6 * math.sin((x + y) * 0.3))


def _material(z: int, top: int) -> str:
    if top <= 1:
        return "water" if z == top else "sand"
    if z == top:
        return "grass"
    return "dirt" if z >= top - 1 else "stone"


HAZE = QColor(158, 176, 202)


def _mix(c: QColor, t: float) -> QColor:
    """Pha màu khối về phía màu không khí; t=0 gần, t=1 xa tít."""
    return QColor(
        round(c.red() + (HAZE.red() - c.red()) * t),
        round(c.green() + (HAZE.green() - c.green()) * t),
        round(c.blue() + (HAZE.blue() - c.blue()) * t),
    )


def _cube(p: QPainter, cx: float, cy: float, kind: str, haze: float = 0.0) -> None:
    top, left, right = (_mix(c, haze) for c in BLOCKS[kind])
    hw, hh = TW / 2, TH / 2

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(top))
    p.drawPolygon(QPolygonF([
        QPointF(cx, cy - hh), QPointF(cx + hw, cy),
        QPointF(cx, cy + hh), QPointF(cx - hw, cy),
    ]))
    p.setBrush(QBrush(left))
    p.drawPolygon(QPolygonF([
        QPointF(cx - hw, cy), QPointF(cx, cy + hh),
        QPointF(cx, cy + hh + CH), QPointF(cx - hw, cy + CH),
    ]))
    p.setBrush(QBrush(right))
    p.drawPolygon(QPolygonF([
        QPointF(cx + hw, cy), QPointF(cx, cy + hh),
        QPointF(cx, cy + hh + CH), QPointF(cx + hw, cy + CH),
    ]))


def render_hero(width: int, height: int, bg_path: str = "") -> QPixmap:
    # Có ảnh nền tuỳ chọn thì dùng nó (co giãn phủ kín), không thì dựng đảo voxel.
    if bg_path:
        from PySide6.QtGui import QPixmap as _P
        src = _P(bg_path)
        if not src.isNull():
            pm = QPixmap(width, height)
            p = QPainter(pm)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            scaled = src.scaled(width, height, Qt.KeepAspectRatioByExpanding,
                                Qt.SmoothTransformation)
            # canh giữa phần thừa
            x = (width - scaled.width()) // 2
            y = (height - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.end()
            return pm

    pm = QPixmap(width, height)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # Bầu trời hoàng hôn RỰC: xanh trong ở đỉnh, vàng cam sáng ở chân trời —
    # sáng để màu ánh lên qua kính, đúng chất ảnh mockup.
    sky = QLinearGradient(QPointF(0, 0), QPointF(0, height))
    sky.setColorAt(0.00, QColor(74, 128, 200))
    sky.setColorAt(0.34, QColor(120, 170, 224))
    sky.setColorAt(0.60, QColor(214, 206, 196))
    sky.setColorAt(0.80, QColor(255, 214, 150))
    sky.setColorAt(1.00, QColor(255, 176, 110))
    p.fillRect(0, 0, width, height, QBrush(sky))

    # Mặt trời sáng thấp bên phải + quầng lớn rực rỡ.
    sun = QPointF(width * 0.72, height * 0.60)
    for r, alpha in ((height * 0.55, 22), (height * 0.34, 34), (height * 0.18, 60),
                     (height * 0.08, 150)):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 240, 205, alpha)))
        p.drawEllipse(sun, r, r)
    p.setBrush(QBrush(QColor(255, 250, 230)))
    p.drawEllipse(sun, height * 0.05, height * 0.05)

    _draw_clouds(p, width, height)

    # Địa hình: vẽ từ xa tới gần để khối trước che khối sau.
    gx, gy = 18, 18
    ox, oy = width * 0.50, height * 0.34
    for sy in range(gy):
        for sx in range(gx):
            top = _height(sx, sy)
            cx = ox + (sx - sy) * (TW / 2)
            cy = oy + (sx + sy) * (TH / 2)
            haze = 0.50 * (1.0 - (sx + sy) / (gx + gy - 2))
            for z in range(0, top + 1):  # vẽ đủ cột, tránh khối lơ lửng ở chỗ dốc
                _cube(p, cx, cy - z * CH, _material(z, top), haze)

    # Phủ một lớp tối ở rìa để chữ trên kính luôn đọc được.
    vign = QLinearGradient(QPointF(0, height * 0.6), QPointF(0, height))
    vign.setColorAt(0.0, QColor(0, 0, 0, 0))
    vign.setColorAt(1.0, QColor(20, 30, 44, 55))
    p.fillRect(QRectF(0, height * 0.6, width, height * 0.4), QBrush(vign))

    p.end()
    return pm
