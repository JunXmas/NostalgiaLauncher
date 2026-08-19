"""Vẽ một wallpaper Aero GỐC (Windows 7 style) 100% bằng QPainter — không dùng
ảnh bản quyền. Nền xanh gradient + tia sáng + ruy-băng ánh sáng phát quang.

Chạy:  python aero-ui/make_wallpaper.py  ->  aero-ui/wallpaper.png
"""
from __future__ import annotations
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)
from PySide6.QtWidgets import QApplication

W, H = 1920, 1200
OUT = Path(__file__).resolve().parent / "wallpaper.png"


def ribbon(cx1, cy1, c1, c2, c3, c4):
    """Đường cong mềm (cubic bezier) làm khung cho một dải ánh sáng."""
    path = QPainterPath()
    path.moveTo(cx1, cy1)
    path.cubicTo(c1[0], c1[1], c2[0], c2[1], c3[0], c3[1])
    path.cubicTo(c3[0] + 260, c3[1] - 120, c4[0] - 200, c4[1] + 40, c4[0], c4[1])
    return path


def glow(p: QPainter, path: QPainterPath, rgb, steps):
    """Tô đường thành dải sáng phát quang: nhiều nét chồng (rộng-mờ -> mảnh-sáng),
    trộn cộng (Plus) để ra ánh sáng thật."""
    p.setCompositionMode(QPainter.CompositionMode_Plus)
    p.setBrush(Qt.NoBrush)
    for width, alpha in steps:
        pen = QPen(QColor(rgb[0], rgb[1], rgb[2], alpha))
        pen.setWidthF(width); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen); p.drawPath(path)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)


GLOW_SOFT = [(90, 8), (60, 12), (38, 20), (22, 32), (12, 52), (6, 96), (2.5, 170)]
GLOW_THIN = [(40, 10), (22, 20), (11, 40), (5, 90), (2, 160)]


def main():
    QApplication([])
    img = QImage(W, H, QImage.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)

    # 1) Nền xanh Aero: gradient dọc đậm dần xuống đáy.
    g = QLinearGradient(0, 0, W * 0.25, H)
    g.setColorAt(0.0, QColor(46, 104, 180))
    g.setColorAt(0.45, QColor(28, 74, 146))
    g.setColorAt(1.0, QColor(9, 28, 66))
    p.fillRect(0, 0, W, H, g)

    # 2) Nguồn sáng dịu phía trên-giữa.
    rg = QRadialGradient(W * 0.52, H * 0.02, W * 0.7)
    rg.setColorAt(0.0, QColor(150, 200, 255, 120))
    rg.setColorAt(0.4, QColor(90, 150, 230, 40))
    rg.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(0, 0, W, H, rg)

    # 3) Tia sáng dọc mờ (light shafts) hơi nghiêng.
    p.save(); p.translate(W * 0.55, 0); p.rotate(8)
    for i, x in enumerate((-120, 40, 210, 360)):
        beam = QLinearGradient(x, 0, x + 70, 0)
        beam.setColorAt(0, QColor(255, 255, 255, 0))
        beam.setColorAt(0.5, QColor(210, 232, 255, 26 - i * 3))
        beam.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(x, -100, 90, H + 200), beam)
    p.restore()

    # 4) Ruy-băng ánh sáng aurora (chữ ký Aero) — quét từ dư-trái sang phải-trên.
    r1 = ribbon(180, 1080, (620, 1010), (980, 760), (1360, 690),
                (1980, 430))
    glow(p, r1, (120, 205, 255), GLOW_SOFT)           # xanh cyan chủ đạo
    r2 = ribbon(150, 1140, (640, 1080), (1080, 900), (1520, 800),
                (1990, 560))
    glow(p, r2, (150, 235, 170), GLOW_THIN)           # điểm xanh lá
    r3 = ribbon(240, 1010, (700, 900), (1120, 640), (1560, 600),
                (1990, 300))
    glow(p, r3, (235, 248, 255), GLOW_THIN)           # lõi trắng mảnh
    r4 = ribbon(120, 1170, (560, 1120), (1000, 1000), (1480, 900),
                (1980, 690))
    glow(p, r4, (90, 150, 235), [(120, 10), (70, 16), (40, 22)])  # dải rộng rất mờ

    # 5) Vài đốm sáng bokeh nhỏ.
    p.setCompositionMode(QPainter.CompositionMode_Plus)
    for x, y, r, a in ((1500, 560, 5, 150), (1620, 470, 3, 120), (1360, 690, 4, 130),
                       (1720, 380, 6, 90), (1240, 780, 3, 90)):
        dot = QRadialGradient(x, y, r * 3)
        dot.setColorAt(0, QColor(230, 245, 255, a)); dot.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(dot); p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(x, y), r * 3, r * 3)
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)

    # 6) Vignette tối 4 góc cho chiều sâu.
    vg = QRadialGradient(W * 0.5, H * 0.5, W * 0.72)
    vg.setColorAt(0.0, QColor(0, 0, 0, 0)); vg.setColorAt(0.75, QColor(0, 0, 0, 0))
    vg.setColorAt(1.0, QColor(0, 6, 20, 130))
    p.fillRect(0, 0, W, H, vg)

    p.end()
    img.save(str(OUT), "PNG")
    print("wallpaper ->", OUT)


if __name__ == "__main__":
    main()
