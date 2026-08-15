"""Các thành phần giao diện vẽ tay theo phong cách Aero."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient,
)
from PySide6.QtWidgets import QAbstractButton, QWidget

from .glass import draw_glass_rect
from .theme import (
    ACCENT, GREEN_BOT, GREEN_EDGE, GREEN_GLOW, GREEN_LOW, GREEN_MID, GREEN_TOP,
    TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font,
)


# ---------- biểu tượng vẽ tay ----------

def draw_cube_icon(p: QPainter, rect: QRectF, top: QColor, side: QColor) -> None:
    """Khối lập phương phối cảnh — dùng cho mục phiên bản và mục game."""
    cx, cy = rect.center().x(), rect.center().y()
    hw, hh, ch = rect.width() * 0.5, rect.width() * 0.25, rect.height() * 0.32
    p.setPen(Qt.NoPen)
    p.setBrush(top)
    p.drawPolygon(QPolygonF([
        QPointF(cx, cy - hh - ch * 0.5), QPointF(cx + hw, cy - ch * 0.5),
        QPointF(cx, cy + hh - ch * 0.5), QPointF(cx - hw, cy - ch * 0.5)]))
    p.setBrush(side)
    p.drawPolygon(QPolygonF([
        QPointF(cx - hw, cy - ch * 0.5), QPointF(cx, cy + hh - ch * 0.5),
        QPointF(cx, cy + hh + ch), QPointF(cx - hw, cy + ch)]))
    p.setBrush(side.darker(122))
    p.drawPolygon(QPolygonF([
        QPointF(cx + hw, cy - ch * 0.5), QPointF(cx, cy + hh - ch * 0.5),
        QPointF(cx, cy + hh + ch), QPointF(cx + hw, cy + ch)]))


def draw_gear_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    p.save()
    p.setPen(QPen(color, 1.6))
    p.setBrush(Qt.NoBrush)
    c, r = rect.center(), rect.width() * 0.28
    p.drawEllipse(c, r, r)
    for i in range(6):
        from math import cos, pi, sin
        a = i * pi / 3
        p.drawLine(
            QPointF(c.x() + cos(a) * r * 1.25, c.y() + sin(a) * r * 1.25),
            QPointF(c.x() + cos(a) * r * 1.85, c.y() + sin(a) * r * 1.85),
        )
    p.restore()


def draw_news_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    p.save()
    p.setPen(QPen(color, 1.4))
    p.setBrush(Qt.NoBrush)
    body = rect.adjusted(rect.width() * 0.14, rect.height() * 0.2,
                         -rect.width() * 0.14, -rect.height() * 0.2)
    p.drawRect(body)
    for i in range(3):
        y = body.top() + body.height() * (0.28 + i * 0.24)
        p.drawLine(QPointF(body.left() + 3, y), QPointF(body.right() - 3, y))
    p.restore()


# ---------- nút CHƠI ----------

# Mỗi tông là 5 chặng của cùng một công thức: sáng -> cắt ở 50% -> hắt sáng lại.
TONES = {
    "green": (GREEN_TOP, GREEN_MID, GREEN_LOW, GREEN_BOT, GREEN_EDGE, GREEN_GLOW),
    "neutral": (QColor(150, 168, 190), QColor(96, 114, 138), QColor(72, 88, 110),
                QColor(104, 122, 146), QColor(38, 48, 64), QColor(180, 200, 224)),
    "danger": (QColor(226, 126, 118), QColor(190, 78, 70), QColor(158, 58, 52),
               QColor(196, 86, 78), QColor(92, 30, 26), QColor(240, 150, 142)),
}


class AeroButton(QAbstractButton):
    """Nút thuỷ tinh Vista: nửa trên sáng, cắt phựt ở giữa, nửa dưới hắt sáng ngược."""

    def __init__(self, text: str, parent=None, *, height: int = 46, tone: str = "green"):
        super().__init__(parent)
        self.setText(text)
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.tone = tone
        self._hover = False

    def enterEvent(self, e):  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        top, mid, low, bot, edge, glow_c = TONES.get(self.tone, TONES["green"])
        enabled = self.isEnabled()
        lift = 16 if (self._hover and enabled) else 0
        if not enabled:
            top, mid, low, bot = (c.darker(135) for c in (top, mid, low, bot))

        # Quầng sáng toả ra ngoài khi rê chuột — Win7 gọi là hot-tracking glow.
        if self._hover and enabled:
            glow = QRadialGradient(r.center(), r.width() * 0.6)
            glow.setColorAt(0.0, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), 70))
            glow.setColorAt(1.0, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), 0))
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(r.adjusted(-8, -8, 8, 8), 10, 10)

        g = QLinearGradient(r.topLeft(), QPointF(r.left(), r.bottom()))
        g.setColorAt(0.00, top.lighter(100 + lift))
        g.setColorAt(0.49, mid.lighter(100 + lift))
        g.setColorAt(0.4999, mid.lighter(100 + lift))
        g.setColorAt(0.50, low.lighter(100 + lift))
        g.setColorAt(1.00, bot.lighter(100 + lift))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 3, 3)

        # Gờ sáng chạy sát mép trong: làm mặt nút trông cong lên.
        p.setPen(QPen(QColor(255, 255, 255, 120), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 2.5, 2.5)
        p.setPen(QPen(edge, 1))
        p.drawRoundedRect(r, 3, 3)

        f = ui_font(13 if self.height() >= 44 else 9, bold=True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.6 if self.height() >= 44 else 1.0)
        p.setFont(f)
        p.setPen(QColor(0, 20, 8, 120))
        p.drawText(self.rect().adjusted(0, 2, 0, 2), Qt.AlignCenter, self.text())
        p.setPen(QColor(255, 255, 255, 255 if enabled else 150))
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


# ---------- thanh tiến trình ----------

class AeroProgress(QWidget):
    """Thanh tiến trình xác định, luôn kèm số đếm — người dùng chờ vài phút tải assets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self.value = 0.0
        self.caption = ""

    def set_progress(self, value: float, caption: str = "") -> None:
        self.value = max(0.0, min(1.0, value))
        self.caption = caption
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(6, 12, 20, 150))
        p.drawRoundedRect(r, 3, 3)

        if self.value > 0:
            fill = QRectF(r.left(), r.top(), r.width() * self.value, r.height())
            g = QLinearGradient(fill.topLeft(), QPointF(fill.left(), fill.bottom()))
            g.setColorAt(0.00, GREEN_TOP)
            g.setColorAt(0.49, GREEN_MID)
            g.setColorAt(0.50, GREEN_LOW)
            g.setColorAt(1.00, GREEN_BOT)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(fill, 3, 3)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 55), 1))
        p.drawRoundedRect(r, 3, 3)
        p.end()


# ---------- mục sidebar ----------

class SidebarItem(QAbstractButton):
    def __init__(self, text: str, icon: str, parent=None, *, subtitle: str = ""):
        super().__init__(parent)
        self.setText(text)
        self.icon_kind = icon
        self.subtitle = subtitle
        self.setCheckable(True)
        self.setFixedHeight(46 if subtitle else 38)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

    def enterEvent(self, e):  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())

        if self.isChecked():
            draw_glass_rect(p, r.adjusted(4, 2, -4, -2), tint=QColor(255, 255, 255, 34), gloss=0.9)
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(QRectF(r.left() + 4, r.top() + 6, 3, r.height() - 12), 1.5, 1.5)
        elif self._hover:
            draw_glass_rect(p, r.adjusted(4, 2, -4, -2), tint=QColor(255, 255, 255, 16), gloss=0.5)

        icon_rect = QRectF(r.left() + 16, r.center().y() - 9, 18, 18)
        color = TEXT if (self.isChecked() or self._hover) else TEXT_DIM
        if self.icon_kind == "cube":
            draw_cube_icon(p, icon_rect, QColor(126, 190, 92), QColor(150, 112, 78))
        elif self.icon_kind == "gear":
            draw_gear_icon(p, icon_rect, color)
        elif self.icon_kind == "news":
            draw_news_icon(p, icon_rect, color)

        text_left = int(r.left() + 44)
        if self.subtitle:
            f = ui_font(7)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
            p.setFont(f)
            p.setPen(TEXT_DIM if (self.isChecked() or self._hover) else TEXT_FAINT)
            p.drawText(QRect(text_left, int(r.top() + 8), self.width() - 50, 11),
                       Qt.AlignLeft | Qt.AlignTop, self.text())
            p.setFont(ui_font(10, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(text_left, int(r.top() + 24), self.width() - 50, 18),
                       Qt.AlignLeft | Qt.AlignTop, self.subtitle)
        else:
            p.setFont(ui_font(9))
            p.setPen(color)
            p.drawText(QRect(text_left, int(r.top()), self.width() - 50, int(r.height())),
                       Qt.AlignLeft | Qt.AlignVCenter, self.text())
        p.end()


# ---------- tab ngang ----------

class TabBar(QWidget):
    changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.labels = labels
        self.current = 0
        self._hover = -1
        self.setFixedHeight(30)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._widths: list[int] = []

    def _layout(self, p: QPainter) -> None:
        p.setFont(ui_font(9))
        fm = p.fontMetrics()
        self._widths = [fm.horizontalAdvance(t) + 28 for t in self.labels]

    def _index_at(self, x: int) -> int:
        acc = 0
        for i, w in enumerate(self._widths):
            if acc <= x < acc + w:
                return i
            acc += w
        return -1

    def mouseMoveEvent(self, e):  # noqa: N802
        idx = self._index_at(e.position().x())
        if idx != self._hover:
            self._hover = idx
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        idx = self._index_at(e.position().x())
        if idx >= 0:
            self.current = idx
            self.changed.emit(idx)
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._layout(p)
        x = 0
        for i, label in enumerate(self.labels):
            w = self._widths[i]
            active = i == self.current
            p.setFont(ui_font(9, bold=active))
            p.setPen(TEXT if active else (TEXT_DIM if i == self._hover else TEXT_FAINT))
            p.drawText(QRect(x, 0, w, self.height() - 4), Qt.AlignCenter, label)
            if active:
                p.setPen(Qt.NoPen)
                p.setBrush(ACCENT)
                p.drawRoundedRect(QRectF(x + 10, self.height() - 3, w - 20, 3), 1.5, 1.5)
            x += w
        p.end()
