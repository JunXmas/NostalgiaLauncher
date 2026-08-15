"""Menu thả xuống bằng kính Aero.

Làm widget con phủ kín cửa sổ thay vì popup top-level: nhờ vậy menu dùng chung
ảnh nền đã blur của cửa sổ nên chất kính khớp hệt các tấm khác, và cú click ra
ngoài để đóng menu bắt ngay trên chính lớp phủ.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .theme import ACCENT, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font

ROW_H = 34
ROW_H_SUB = 46
SEP_H = 9
HEADER_H = 26
PAD = 6


@dataclass
class MenuItem:
    label: str = ""
    sublabel: str = ""
    checked: bool = False
    enabled: bool = True
    kind: str = "item"  # item | separator | header
    data: object = None

    @property
    def height(self) -> int:
        if self.kind == "separator":
            return SEP_H
        if self.kind == "header":
            return HEADER_H
        return ROW_H_SUB if self.sublabel else ROW_H

    @property
    def selectable(self) -> bool:
        return self.kind == "item" and self.enabled


class GlassMenu(QWidget):
    """Lớp phủ kín cửa sổ, vẽ một hộp menu kính ở vị trí được neo."""

    chosen = Signal(object)  # phát ra MenuItem.data

    def __init__(self, parent: QWidget, items: list[MenuItem], *, width: int = 240,
                 max_height: int = 380):
        super().__init__(parent)
        self.items = items
        self.box_width = width
        self.max_height = max_height
        self.scroll = 0
        self._hover = -1
        self.setMouseTracking(True)
        self.setGeometry(parent.rect())
        self.raise_()

    # ---------- hình học ----------

    @property
    def content_height(self) -> int:
        return sum(i.height for i in self.items) + PAD * 2

    def anchor_below(self, widget_rect: QRect) -> None:
        """Neo dưới một vùng (toạ độ của cửa sổ), tự lật lên nếu tràn đáy."""
        h = min(self.content_height, self.max_height)
        x = widget_rect.left()
        y = widget_rect.bottom() + 4
        if y + h > self.height() - 8:
            y = max(8, widget_rect.top() - h - 4)
        x = max(8, min(x, self.width() - self.box_width - 8))
        self._box = QRect(x, y, self.box_width, h)
        self.update()

    def anchor_above(self, widget_rect: QRect) -> None:
        h = min(self.content_height, self.max_height)
        x = max(8, min(widget_rect.left(), self.width() - self.box_width - 8))
        y = max(8, widget_rect.top() - h - 4)
        self._box = QRect(x, y, self.box_width, h)
        self.update()

    def _row_rects(self) -> list[tuple[int, QRect]]:
        out, y = [], self._box.top() + PAD - self.scroll
        for idx, item in enumerate(self.items):
            out.append((idx, QRect(self._box.left() + PAD, y,
                                   self._box.width() - PAD * 2, item.height)))
            y += item.height
        return out

    def _index_at(self, pos) -> int:
        if not self._box.contains(pos):
            return -1
        for idx, rect in self._row_rects():
            if rect.contains(pos) and self.items[idx].selectable:
                return idx
        return -1

    # ---------- tương tác ----------

    def mouseMoveEvent(self, e):  # noqa: N802
        idx = self._index_at(e.position().toPoint())
        if idx != self._hover:
            self._hover = idx
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        if not self._box.contains(pos):
            self.close_menu()
            return
        idx = self._index_at(pos)
        if idx >= 0:
            self.chosen.emit(self.items[idx].data)
            self.close_menu()

    def wheelEvent(self, e):  # noqa: N802
        overflow = self.content_height - self._box.height()
        if overflow > 0:
            self.scroll = max(0, min(overflow, self.scroll - e.angleDelta().y()))
            self.update()

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self.close_menu()

    def close_menu(self) -> None:
        self.hide()
        self.deleteLater()

    # ---------- vẽ ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Làm tối phần còn lại của cửa sổ để mắt dồn vào menu.
        p.fillRect(self.rect(), QColor(0, 0, 0, 60))

        box = QRectF(self._box)
        backdrop = getattr(self.window(), "blurred", None)
        p.save()
        p.setClipRect(box)
        if backdrop and not backdrop.isNull():
            p.drawPixmap(self._box, backdrop, self._box)
        p.fillRect(box, QColor(18, 28, 44, 214))
        p.fillRect(box, gloss_gradient(box.height() if box.height() < 120 else 120, 0.9))
        p.restore()

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 96), 1))
        p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)

        p.setClipRect(self._box.adjusted(0, PAD - 2, 0, -PAD + 2))
        for idx, rect in self._row_rects():
            self._paint_row(p, self.items[idx], rect, idx == self._hover)
        p.end()

    def _paint_row(self, p: QPainter, item: MenuItem, rect: QRect, hovered: bool) -> None:
        if item.kind == "separator":
            y = rect.center().y()
            p.setPen(QPen(QColor(255, 255, 255, 34), 1))
            p.drawLine(rect.left() + 6, y, rect.right() - 6, y)
            return

        if item.kind == "header":
            p.setFont(ui_font(7, bold=True))
            p.setPen(TEXT_FAINT)
            p.drawText(rect.adjusted(10, 0, 0, 0), Qt.AlignLeft | Qt.AlignVCenter,
                       item.label.upper())
            return

        if hovered:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 30))
            p.drawRoundedRect(QRectF(rect), 3, 3)

        if item.checked:
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(QRectF(rect.left() + 3, rect.top() + 7, 3,
                                     rect.height() - 14), 1.5, 1.5)

        color = TEXT if item.enabled else TEXT_FAINT
        left = rect.left() + 14
        if item.sublabel:
            p.setFont(ui_font(9, bold=item.checked))
            p.setPen(color)
            p.drawText(QRect(left, rect.top() + 6, rect.width() - 20, 16),
                       Qt.AlignLeft | Qt.AlignTop, item.label)
            p.setFont(ui_font(7))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(left, rect.top() + 24, rect.width() - 20, 14),
                       Qt.AlignLeft | Qt.AlignTop, item.sublabel)
        else:
            p.setFont(ui_font(9, bold=item.checked))
            p.setPen(color)
            p.drawText(QRect(left, rect.top(), rect.width() - 20, rect.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, item.label)


def popup(parent: QWidget, items: list[MenuItem], anchor: QRect, on_choose: Callable,
          *, width: int = 240, above: bool = False) -> GlassMenu:
    menu = GlassMenu(parent, items, width=width)
    (menu.anchor_above if above else menu.anchor_below)(anchor)
    menu.chosen.connect(on_choose)
    menu.show()
    menu.setFocus()
    return menu
