"""Tấm kính Aero.

Thay vì xin compositor làm mờ nền desktop (KWin có, Cinnamon/Mint thì không, nên
kết quả tuỳ máy), ta làm mờ *ảnh nền của chính cửa sổ*. Hiệu ứng giống hệt, chạy
như nhau trên mọi máy, và ta kiểm soát được thứ nằm sau tấm kính.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .theme import (
    BEVEL_DARK, BEVEL_LIGHT, GLASS_TINT, GLASS_TINT_STRONG, gloss_gradient, sheen_gradient,
)


class GlassPanel(QWidget):
    """Vùng kính mờ lấy nền từ ảnh đã blur của cửa sổ cha."""

    def __init__(self, parent=None, *, strong: bool = False, edges: str = "",
                 gloss: float = 1.0, gloss_axis: str = "v"):
        super().__init__(parent)
        self.strong = strong
        self.edges = edges  # tổ hợp các ký tự t/b/l/r cần vẽ viền vát
        self.gloss = gloss
        self.gloss_axis = gloss_axis  # "v" = vệt cắt giữa; "h" = ánh sáng hắt ngang
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

        # 2. Sắc kính ám lam.
        p.fillRect(rect, GLASS_TINT_STRONG if self.strong else GLASS_TINT)

        # 3. Ánh sáng trên mặt kính: vệt cắt giữa cho thanh ngang, hắt ngang cho panel cao.
        if self.gloss > 0:
            if self.gloss_axis == "h":
                p.fillRect(rect, sheen_gradient(rect.width(), self.gloss))
            else:
                p.fillRect(rect, gloss_gradient(rect.height(), self.gloss))

        # 4. Viền vát cho tấm kính có bề dày.
        self._draw_bevel(p, rect)
        p.end()

    def _draw_bevel(self, p: QPainter, rect) -> None:
        pairs = {
            "t": ((rect.left(), rect.top(), rect.right(), rect.top()), BEVEL_LIGHT),
            "l": ((rect.left(), rect.top(), rect.left(), rect.bottom()), BEVEL_LIGHT),
            "b": ((rect.left(), rect.bottom(), rect.right(), rect.bottom()), BEVEL_DARK),
            "r": ((rect.right(), rect.top(), rect.right(), rect.bottom()), BEVEL_DARK),
        }
        for ch in self.edges:
            if ch not in pairs:
                continue
            (x1, y1, x2, y2), color = pairs[ch]
            p.setPen(QPen(color, 1))
            p.drawLine(x1, y1, x2, y2)


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

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(border or QColor(255, 255, 255, 60), 1))
    p.drawRoundedRect(path_rect, radius, radius)
    p.restore()
