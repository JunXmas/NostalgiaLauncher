"""Render skin Minecraft theo kiểu 2.5D (isometric) bằng QPainter — không cần OpenGL.

Chiếu SONG SONG (orthographic): sau khi xoay, mỗi mặt hộp chiếu ra một hình bình
hành, nên có thể map texture bằng affine (QTransform) chính xác. Sắp xếp mặt theo
độ sâu (painter's algorithm), cull mặt quay lưng, và đổ bóng nhẹ theo hướng sáng.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QTransform

# (tên, tâm x,y,z, kích thước w,h,d, offset texture lớp gốc, offset lớp phủ)
# Gốc toạ độ ở giữa người; y+ hướng lên. Đơn vị = pixel trên skin 64x64.
_BOXES = [
    ("head", (0, 12, 0), (8, 8, 8), (0, 0), (32, 0)),
    ("torso", (0, 2, 0), (8, 12, 4), (16, 16), (16, 32)),
    ("rarm", (-6, 2, 0), (4, 12, 4), (40, 16), (40, 32)),
    ("larm", (6, 2, 0), (4, 12, 4), (32, 48), (48, 48)),
    ("rleg", (-2, -10, 0), (4, 12, 4), (0, 16), (0, 32)),
    ("lleg", (2, -10, 0), (4, 12, 4), (16, 48), (0, 48)),
]
_LIGHT = (-0.30, 0.62, 0.72)   # hướng nguồn sáng (đã chuẩn hoá xấp xỉ)


def _rotator(yaw: float, pitch: float):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cx, sx = math.cos(pitch), math.sin(pitch)

    def f(p):
        x, y, z = p
        x, z = x * cy + z * sy, -x * sy + z * cy      # xoay quanh Y
        y, z = y * cx - z * sx, y * sx + z * cx        # xoay quanh X
        return (x, y, z)
    return f


def _box_faces(name, center, size, tex, overlay, slim):
    w, h, d = size
    cx, cyc, cz = center
    if slim and name in ("rarm", "larm"):
        w = 3
        cx += 0.5 if name == "rarm" else -0.5          # tay slim ép sát thân
    faces = []
    for layer, off in ((0, tex), (1, overlay)):
        if off is None:
            continue
        ox, oy = off
        infl = 0.30 if layer else 0.0                  # lớp phủ phồng nhẹ để vẽ đè
        ex, ey, ez = w / 2 + infl, h / 2 + infl, d / 2 + infl

        def c(sx, sy, sz):
            return (cx + sx * ex, cyc + sy * ey, cz + sz * ez)

        uv = {
            "front": (ox + d, oy + d, w, h),
            "back": (ox + d + w + d, oy + d, w, h),
            "right": (ox, oy + d, d, h),
            "left": (ox + d + w, oy + d, d, h),
            "top": (ox + d, oy, w, d),
            "bottom": (ox + d + w, oy, w, d),
        }
        geom = {
            "front": ([c(-1, 1, 1), c(1, 1, 1), c(1, -1, 1), c(-1, -1, 1)], (0, 0, 1)),
            "back": ([c(1, 1, -1), c(-1, 1, -1), c(-1, -1, -1), c(1, -1, -1)], (0, 0, -1)),
            "right": ([c(-1, 1, -1), c(-1, 1, 1), c(-1, -1, 1), c(-1, -1, -1)], (-1, 0, 0)),
            "left": ([c(1, 1, 1), c(1, 1, -1), c(1, -1, -1), c(1, -1, 1)], (1, 0, 0)),
            "top": ([c(-1, 1, -1), c(1, 1, -1), c(1, 1, 1), c(-1, 1, 1)], (0, 1, 0)),
            "bottom": ([c(-1, -1, 1), c(1, -1, 1), c(1, -1, -1), c(-1, -1, -1)], (0, -1, 0)),
        }
        for fn, (corners, normal) in geom.items():
            faces.append((corners, normal, uv[fn], layer))
    return faces


def _shade(rn) -> QColor | None:
    inten = max(0.0, rn[0] * _LIGHT[0] + rn[1] * _LIGHT[1] + rn[2] * _LIGHT[2])
    inten = 0.60 + 0.40 * inten          # 0.60..1.00
    if inten >= 0.99:
        return None
    return QColor(0, 0, 0, int((1.0 - inten) * 150))


_CACHE: dict = {}     # (img.cacheKey(), slim) -> [(corners, normal, subimg)]


def _fully_transparent(sub) -> bool:
    for y in range(sub.height()):
        for x in range(sub.width()):
            if sub.pixelColor(x, y).alpha() != 0:
                return False
    return True


def _prepare(img, slim):
    """Cắt sẵn texture từng mặt thành ảnh con nhỏ (cache) — tránh vẽ lại cả ảnh
    64x64 + clip cho mỗi mặt mỗi frame. Bỏ luôn mặt lớp phủ trong suốt hoàn toàn."""
    key = (img.cacheKey(), slim)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    faces = []
    for name, center, size, tex, ov in _BOXES:
        for corners, normal, uv, layer in _box_faces(name, center, size, tex, ov, slim):
            u, v, w, h = (int(round(x)) for x in uv)
            sub = img.copy(u, v, w, h)
            if layer == 1 and _fully_transparent(sub):
                continue
            faces.append((corners, normal, sub))
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[key] = faces
    return faces


def render(p: QPainter, img, cx: float, cy: float, scale: float,
           yaw_deg: float, pitch_deg: float, slim: bool = False) -> None:
    """Vẽ model skin vào tâm (cx, cy). yaw/pitch tính bằng độ."""
    if img is None or img.width() < 64:
        return
    rot = _rotator(math.radians(yaw_deg), math.radians(pitch_deg))
    drawable = []
    for corners, normal, sub in _prepare(img, slim):
        rn = rot(normal)
        if rn[2] <= 0.02:                # quay lưng -> bỏ
            continue
        rc = [rot(c) for c in corners]
        depth = sum(c[2] for c in rc) / 4
        drawable.append((depth, rc, sub, rn))
    drawable.sort(key=lambda t: t[0])    # xa (z nhỏ) vẽ trước

    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    for _depth, rc, sub, rn in drawable:
        scr = [(cx + c[0] * scale, cy - c[1] * scale) for c in rc]
        tl, tr, _br, bl = scr
        w, h = sub.width(), sub.height()
        ax, ay = (tr[0] - tl[0]) / w, (tr[1] - tl[1]) / w
        bx, by = (bl[0] - tl[0]) / h, (bl[1] - tl[1]) / h
        p.save()
        p.setTransform(QTransform(ax, ay, bx, by, tl[0], tl[1]))
        p.drawImage(0, 0, sub)           # chỉ vẽ ảnh con nhỏ, không cần clip
        sh = _shade(rn)
        if sh:
            p.fillRect(QRectF(0, 0, w, h), sh)
        p.restore()
    p.setTransform(QTransform())
