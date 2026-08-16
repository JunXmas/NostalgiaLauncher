"""Danh sách cuộn, thanh trượt và công tắc, vẽ tay theo cùng ngôn ngữ Aero."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .theme import (
    ACCENT, GREEN_BOT, GREEN_LOW, GREEN_MID, GREEN_TOP, TEXT, TEXT_DIM, TEXT_FAINT,
    gloss_gradient, ui_font,
)


@dataclass
class Row:
    title: str
    subtitle: str = ""
    right: str = ""
    checked: bool = False
    action: str = ""          # "" | "delete"
    badge: str = ""           # nhãn pill bấm được bên phải (ON/OFF, INSTALL…)
    badge_on: bool = False    # True = pill xanh (đang bật / kêu gọi cài)
    icon: object = None       # QPixmap ảnh preview bên trái (tùy chọn)
    data: object = None


class ListView(QWidget):
    """Danh sách hàng có cuộn bằng con lăn, hover, một pill và một nút bên phải."""

    activated = Signal(object)
    action_clicked = Signal(object)
    badge_clicked = Signal(object)

    ROW_H = 52
    BADGE_W = 62

    def __init__(self, parent=None, *, empty_text: str = "Nothing here yet."):
        super().__init__(parent)
        self.rows: list[Row] = []
        self.empty_text = empty_text
        self.scroll = 0
        self._hover = -1
        self._hover_action = False
        self._hover_badge = False
        self.setMouseTracking(True)

    def set_rows(self, rows: list[Row]) -> None:
        self.rows = rows
        self.scroll = min(self.scroll, max(0, self._content_h() - self.height()))
        self.update()

    def _content_h(self) -> int:
        return len(self.rows) * self.ROW_H

    def _rect_of(self, i: int) -> QRect:
        return QRect(0, i * self.ROW_H - self.scroll, self.width(), self.ROW_H)

    def _action_rect(self, row_rect: QRect) -> QRect:
        return QRect(row_rect.right() - 46, row_rect.center().y() - 14, 30, 28)

    def _badge_rect(self, row: Row, row_rect: QRect) -> QRect:
        right = row_rect.right() - (46 if row.action else 16)
        return QRect(right - self.BADGE_W, row_rect.center().y() - 13, self.BADGE_W, 26)

    def _index_at(self, pos) -> int:
        i = (pos.y() + self.scroll) // self.ROW_H
        return i if 0 <= i < len(self.rows) else -1

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        i = self._index_at(pos)
        act = badge = False
        if i >= 0:
            r = self._rect_of(i)
            act = bool(self.rows[i].action) and self._action_rect(r).contains(pos)
            badge = bool(self.rows[i].badge) and self._badge_rect(self.rows[i], r).contains(pos)
        if (i, act, badge) != (self._hover, self._hover_action, self._hover_badge):
            self._hover, self._hover_action, self._hover_badge = i, act, badge
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover, self._hover_action, self._hover_badge = -1, False, False
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        i = self._index_at(pos)
        if i < 0:
            return
        row = self.rows[i]
        r = self._rect_of(i)
        if row.action and self._action_rect(r).contains(pos):
            self.action_clicked.emit(row.data)
        elif row.badge and self._badge_rect(row, r).contains(pos):
            self.badge_clicked.emit(row.data)
        else:
            self.activated.emit(row.data)

    def wheelEvent(self, e):  # noqa: N802
        overflow = self._content_h() - self.height()
        if overflow > 0:
            self.scroll = max(0, min(overflow, self.scroll - e.angleDelta().y()))
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if not self.rows:
            p.setFont(ui_font(9))
            p.setPen(TEXT_FAINT)
            p.drawText(self.rect(), Qt.AlignCenter, self.empty_text)
            p.end()
            return

        for i, row in enumerate(self.rows):
            r = self._rect_of(i)
            if r.bottom() < 0 or r.top() > self.height():
                continue
            self._paint_row(p, row, r, i, i == self._hover)

        # Thanh cuộn mảnh, chỉ hiện khi có gì để cuộn.
        overflow = self._content_h() - self.height()
        if overflow > 0:
            frac = self.height() / self._content_h()
            bar_h = max(28, int(self.height() * frac))
            y = int((self.height() - bar_h) * (self.scroll / overflow))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 60))
            p.drawRoundedRect(QRectF(self.width() - 5, y, 3, bar_h), 1.5, 1.5)
        p.end()

    def _paint_row(self, p: QPainter, row: Row, r: QRect, index: int, hovered: bool) -> None:
        body = QRectF(r.adjusted(0, 1, -10, -1))
        if row.checked:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 30))
            p.drawRoundedRect(body, 3, 3)
            p.setBrush(ACCENT)
            p.drawRoundedRect(QRectF(body.left(), body.top() + 8, 3, body.height() - 16), 1.5, 1.5)
        elif hovered:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 16))
            p.drawRoundedRect(body, 3, 3)

        # Ảnh preview bên trái (bo góc) nếu có; đẩy phần chữ sang phải.
        icon = row.icon
        if icon is not None and not icon.isNull():
            d = 34
            ir = QRectF(r.left() + 12, r.center().y() - d / 2, d, d)
            path = QPainterPath()
            path.addRoundedRect(ir, 6, 6)
            p.save()
            p.setClipPath(path)
            p.drawPixmap(ir.toRect(), icon)
            p.restore()
            p.setPen(QPen(QColor(255, 255, 255, 45), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(ir, 6, 6)
            left = r.left() + 12 + d + 12
        else:
            left = r.left() + 16
        # Chừa chỗ bên phải chỉ khi hàng thật sự có cột phải hoặc nút hành động,
        # nếu không tiêu đề bị cắt oan trong danh sách hẹp.
        reserved = 0
        if row.right:
            reserved += 120
        if row.badge:
            reserved += self.BADGE_W + 10
        if row.action:
            reserved += 46
        text_w = max(60, r.right() - left - reserved - 10)

        p.setFont(ui_font(10, bold=row.checked))
        p.setPen(TEXT)
        p.drawText(QRect(left, r.top() + 8, text_w, 18),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(row.title, Qt.ElideRight, text_w))
        if row.subtitle:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(left, r.top() + 27, text_w, 16),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       p.fontMetrics().elidedText(row.subtitle, Qt.ElideRight, text_w))
        if row.right:
            shift = (self.BADGE_W + 10) if row.badge else 0
            p.setFont(ui_font(8))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(r.right() - 172 - shift, r.top(), 112, r.height()),
                       Qt.AlignRight | Qt.AlignVCenter, row.right)

        if row.badge:
            self._paint_badge(p, row, self._badge_rect(row, r),
                              hovered and self._hover_badge)

        if row.action == "delete":
            a = self._action_rect(r)
            if hovered and self._hover_action:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(210, 84, 78, 150))
                p.drawRoundedRect(QRectF(a), 3, 3)
            p.setPen(QPen(TEXT if (hovered and self._hover_action) else TEXT_DIM, 1.4))
            c = a.center()
            p.drawLine(c.x() - 5, c.y() - 5, c.x() + 5, c.y() + 5)
            p.drawLine(c.x() + 5, c.y() - 5, c.x() - 5, c.y() + 5)

    def _paint_badge(self, p: QPainter, row: Row, a: QRect, hot: bool) -> None:
        box = QRectF(a)
        p.setPen(Qt.NoPen)
        if row.badge_on:
            g = QLinearGradient(box.topLeft(), QPointF(box.left(), box.bottom()))
            g.setColorAt(0.0, GREEN_TOP)
            g.setColorAt(0.49, GREEN_MID)
            g.setColorAt(0.5, GREEN_LOW)
            g.setColorAt(1.0, GREEN_BOT)
            p.setBrush(QBrush(g))
            text_pen = QPen(QColor(12, 26, 16), 1)
        else:
            p.setBrush(QColor(255, 255, 255, 40 if hot else 24))
            text_pen = QPen(TEXT if hot else TEXT_DIM, 1)
        p.drawRoundedRect(box, 4, 4)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 90 if hot else 55), 1))
        p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
        p.setFont(ui_font(8, bold=True))
        p.setPen(text_pen)
        p.drawText(a, Qt.AlignCenter, row.badge)


class AeroSlider(QWidget):
    """Thanh trượt: rãnh lõm, phần đã chọn tô gradient xanh, núm kính."""

    changed = Signal(int)

    def __init__(self, minimum: int, maximum: int, value: int, step: int = 1, parent=None):
        super().__init__(parent)
        self.minimum, self.maximum, self.step = minimum, maximum, step
        self.value = value
        self.setFixedHeight(26)
        self.setCursor(Qt.PointingHandCursor)
        self._drag = False

    @property
    def _frac(self) -> float:
        span = self.maximum - self.minimum
        return (self.value - self.minimum) / span if span else 0.0

    def _set_from_x(self, x: float) -> None:
        span = self.maximum - self.minimum
        raw = self.minimum + span * max(0.0, min(1.0, (x - 8) / max(1, self.width() - 16)))
        snapped = int(round(raw / self.step) * self.step)
        snapped = max(self.minimum, min(self.maximum, snapped))
        if snapped != self.value:
            self.value = snapped
            self.changed.emit(snapped)
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        self._drag = True
        self._set_from_x(e.position().x())

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._drag:
            self._set_from_x(e.position().x())

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._drag = False

    def wheelEvent(self, e):  # noqa: N802
        delta = self.step * (1 if e.angleDelta().y() > 0 else -1)
        self.value = max(self.minimum, min(self.maximum, self.value + delta))
        self.changed.emit(self.value)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cy = self.height() / 2
        groove = QRectF(8, cy - 3, self.width() - 16, 6)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(6, 12, 20, 150))
        p.drawRoundedRect(groove, 3, 3)

        fill = QRectF(groove.left(), groove.top(), groove.width() * self._frac, groove.height())
        g = QLinearGradient(fill.topLeft(), QPointF(fill.left(), fill.bottom()))
        g.setColorAt(0.0, GREEN_TOP)
        g.setColorAt(0.49, GREEN_MID)
        g.setColorAt(0.5, GREEN_LOW)
        g.setColorAt(1.0, GREEN_BOT)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(fill, 3, 3)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.drawRoundedRect(groove, 3, 3)

        x = groove.left() + groove.width() * self._frac
        knob = QRectF(x - 7, cy - 10, 14, 20)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(226, 236, 248))
        p.drawRoundedRect(knob, 3, 3)
        p.setBrush(gloss_gradient(knob.height(), 1.0))
        p.drawRoundedRect(knob, 3, 3)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(30, 44, 62, 170), 1))
        p.drawRoundedRect(knob, 3, 3)
        p.end()


class AeroToggle(QWidget):
    """Công tắc bật/tắt nhỏ, cùng công thức kính."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.checked = checked
        self.setFixedSize(44, 22)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):  # noqa: N802
        self.checked = not self.checked
        self.toggled.emit(self.checked)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(6, 12, 20, 150))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        if self.checked:
            g = QLinearGradient(r.topLeft(), QPointF(r.left(), r.bottom()))
            g.setColorAt(0.0, GREEN_TOP)
            g.setColorAt(0.49, GREEN_MID)
            g.setColorAt(0.5, GREEN_LOW)
            g.setColorAt(1.0, GREEN_BOT)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        d = r.height() - 6
        x = r.right() - d - 3 if self.checked else r.left() + 3
        knob = QRectF(x, r.top() + 3, d, d)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(230, 238, 248))
        p.drawEllipse(knob)
        p.setPen(QPen(QColor(30, 44, 62, 150), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(knob)
        p.end()
