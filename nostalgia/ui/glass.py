"""Tấm kính Aero.

Thay vì xin compositor làm mờ nền desktop (KWin có, Cinnamon/Mint thì không, nên
kết quả tuỳ máy), ta làm mờ *ảnh nền của chính cửa sổ*. Hiệu ứng giống hệt, chạy
như nhau trên mọi máy, và ta kiểm soát được thứ nằm sau tấm kính.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .theme import (
    BEVEL_DARK, BEVEL_LIGHT, GLASS_TINT, GLASS_TINT_STRONG, diagonal_streak,
    gloss_gradient, noise_tile, sheen_gradient,
)


class GlassPanel(QWidget):
    """Vùng kính mờ lấy nền từ ảnh đã blur của cửa sổ cha."""

    def __init__(self, parent=None, *, strong: bool = False, edges: str = "",
                 gloss: float = 1.0, gloss_axis: str = "v", streak: float = 0.0):
        super().__init__(parent)
        self.strong = strong
        self.edges = edges  # tổ hợp các ký tự t/b/l/r cần vẽ viền vát
        self.gloss = gloss
        self.gloss_axis = gloss_axis  # "v" = vệt cắt giữa; "h" = ánh sáng hắt ngang
        self.streak = streak  # >0 = thêm vệt sáng xiên (port từ bản web)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _backdrop(self) -> QPixmap | None:
        w = self.window()
        return getattr(w, "blurred", None)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # 1. Nền mờ: cắt đúng phần ảnh nằm sau tấm kính này.
        backdrop = self._backdrop()
        if backdrop and not backdrop.isNull():
            origin = self.mapTo(self.window(), rect.topLeft())
            p.drawPixmap(rect, backdrop, QRect(origin, rect.size()))

        # 1b. Lớp exclusion (Fluent) — chỉ khi có nền để trộn.
        if backdrop and not backdrop.isNull():
            p.setCompositionMode(QPainter.CompositionMode_Exclusion)
            p.fillRect(rect, QColor(42, 56, 86, 46))
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 2. Sắc kính ám lam.
        p.fillRect(rect, GLASS_TINT_STRONG if self.strong else GLASS_TINT)

        # 2b. Lớp nhiễu hạt Acrylic — làm kính có hạt mịn thay vì phẳng lì.
        p.fillRect(rect, QBrush(noise_tile()))

        # 3. Ánh sáng trên mặt kính: vệt cắt giữa cho thanh ngang, hắt ngang cho panel cao.
        if self.gloss > 0:
            if self.gloss_axis == "h":
                p.fillRect(rect, sheen_gradient(rect.width(), self.gloss))
            else:
                p.fillRect(rect, gloss_gradient(rect.height(), self.gloss))

        # 3b. Vệt sáng xiên giả phản chiếu (port từ bản web).
        if self.streak > 0:
            p.fillRect(rect, diagonal_streak(rect.width(), rect.height(), self.streak))

        # 4. Viền vát cho tấm kính có bề dày.
        self._draw_bevel(p, rect)
        p.end()

    def _draw_bevel(self, p: QPainter, rect) -> None:
        # Viền vát hai lớp như bản web: ring sáng ngay sát mép trong tạo cảm giác
        # tấm kính cong lên, rồi cạnh sáng/tối theo hướng ánh sáng.
        pairs = {
            "t": ((rect.left(), rect.top(), rect.right(), rect.top()), BEVEL_LIGHT),
            "l": ((rect.left(), rect.top(), rect.left(), rect.bottom()), BEVEL_LIGHT),
            "b": ((rect.left(), rect.bottom(), rect.right(), rect.bottom()), BEVEL_DARK),
            "r": ((rect.right(), rect.top(), rect.right(), rect.bottom()), BEVEL_DARK),
        }
        inner = {  # highlight lùi vào 1px, chỉ vẽ cho cạnh sáng (trên/trái)
            "t": (rect.left() + 1, rect.top() + 1, rect.right() - 1, rect.top() + 1),
            "l": (rect.left() + 1, rect.top() + 1, rect.left() + 1, rect.bottom() - 1),
        }
        for ch in self.edges:
            if ch not in pairs:
                continue
            (x1, y1, x2, y2), color = pairs[ch]
            p.setPen(QPen(color, 1))
            p.drawLine(x1, y1, x2, y2)
            if ch in inner:  # lớp highlight trong, mờ hơn
                ix1, iy1, ix2, iy2 = inner[ch]
                p.setPen(QPen(QColor(255, 255, 255, 40), 1))
                p.drawLine(ix1, iy1, ix2, iy2)


def draw_glass_rect(p: QPainter, rect, *, radius: float = 3.0, tint: QColor | None = None,
                    gloss: float = 1.0, border: QColor | None = None) -> None:
    """Vẽ một mảnh kính nhỏ (ô chọn, viên thuốc, ô nhập) theo cùng công thức."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    path_rect = rect.adjusted(0.5, 0.5, -0.5, -0.5)

    p.setPen(Qt.NoPen)
    p.setBrush(tint or QColor(255, 255, 255, 28))
    p.drawRoundedRect(path_rect, radius, radius)

    if gloss > 0:
        p.setBrush(gloss_gradient(rect.height(), gloss * 0.7))
        p.drawRoundedRect(path_rect, radius, radius)

    # Nhiễu hạt Acrylic, cắt theo bo góc.
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(path_rect, radius, radius)
    p.setClipPath(clip)
    p.fillRect(path_rect, QBrush(noise_tile()))
    p.restore()

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(border or QColor(255, 255, 255, 60), 1))
    p.drawRoundedRect(path_rect, radius, radius)
    p.restore()
