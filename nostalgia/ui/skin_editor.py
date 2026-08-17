"""Trình vẽ skin ngay trong launcher: tô từng pixel trên bản đồ UV 64×64.

Công cụ: bút, tẩy, xô đổ màu, hút màu; bảng màu + chọn màu tuỳ ý; undo/redo;
lưới & khung hướng dẫn từng mặt; xem trước 3D xoay được cập nhật ngay khi vẽ.
Bấm LƯU sẽ áp skin qua luồng đổi skin sẵn có (cục bộ + Mojang + backend chung).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QColorDialog

from .dialogs import GlassDialog
from .theme import ACCENT, TEXT, TEXT_DIM, TEXT_FAINT, ui_font
from .widgets import AeroButton

TS = 8                     # cỡ một texel trên canvas (px)
GRID = 64                  # skin 64×64

# Bảng màu dựng sẵn: da/tóc/cơ bản/xám — đủ để vẽ nhanh, còn lại dùng "màu khác".
PALETTE = [
    "#000000", "#3d3d3d", "#7a7a7a", "#b5b5b5", "#e8e8e8", "#ffffff",
    "#7c4a2d", "#a9683c", "#c98a54", "#e5b98b", "#f4d5b0", "#ffe0bd",
    "#2b1a10", "#4a2f1a", "#6b4423", "#a0651f", "#d1a04a", "#f2d16b",
    "#7a1f1f", "#c02f2f", "#e85d5d", "#e07a2f", "#f0b24a", "#f6e05e",
    "#1f5a2f", "#2f9e46", "#5fd07a", "#1f5f7a", "#2f9ec0", "#5fd0e0",
    "#20306a", "#2f52c0", "#5f7ce0", "#4a2f7a", "#7a4ac0", "#b06fe0",
]

# Khung hướng dẫn: mặt TRƯỚC của từng bộ phận trên atlas (x, y, w, h, nhãn).
GUIDE_FACES = [
    (8, 8, 8, 8, "HEAD"),
    (20, 20, 8, 12, "BODY"),
    (44, 20, 4, 12, "R-ARM"),
    (36, 52, 4, 12, "L-ARM"),
    (4, 20, 4, 12, "R-LEG"),
    (20, 52, 4, 12, "L-LEG"),
]


def to_canvas(img: QImage | None) -> QImage:
    """Chuẩn hoá về ARGB32 64×64 để vẽ; nếu không có nguồn thì tạo nền trong suốt."""
    out = QImage(GRID, GRID, QImage.Format_ARGB32)
    out.fill(Qt.transparent)
    if img is not None and not img.isNull() and img.width() >= 64:
        src = img.convertToFormat(QImage.Format_ARGB32)
        p = QPainter(out)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        # Chép phần 64×64 (skin cũ 64×32 chỉ có nửa trên — phần dưới để trong suốt).
        p.drawImage(0, 0, src, 0, 0, 64, min(64, src.height()))
        p.end()
    return out


class SkinEditorDialog(GlassDialog):
    """Hộp thoại vẽ skin. Phát tín hiệu `saved(png_bytes, variant)` khi bấm LƯU."""

    saved = Signal(bytes, str)

    def __init__(self, parent, start_img: QImage | None = None, variant: str = "classic"):
        super().__init__(parent, "Draw skin", width=940, height=648)
        self.img = to_canvas(start_img)
        self.variant = variant
        self.color = QColor("#a9683c")
        self.tool = "pencil"                 # pencil | eraser | fill | pick
        self.show_grid = True
        self.show_guide = True
        self._undo: list[QImage] = []
        self._redo: list[QImage] = []
        self._mode = None                    # "paint" | "rotate"
        self._last = None                    # texel cuối khi kéo bút
        self._yaw, self._pitch = -28.0, 10.0
        self._drag_from = None
        self._hit: list[tuple[QRect, str, object]] = []

        self.save_btn = AeroButton("SAVE", self, height=40, tone="green")
        self.cancel_btn = AeroButton("CANCEL", self, height=40, tone="neutral")
        self.save_btn.clicked.connect(self._do_save)
        self.cancel_btn.clicked.connect(self.dismiss)
        self.setFocus()

    # ---------- hình học ----------

    def _geo(self) -> dict:
        c = self.card
        top = c.top() + 52
        tools_x = c.left() + 18
        canvas = QRect(tools_x + 60, top, GRID * TS, GRID * TS)
        right_x = canvas.right() + 20
        right_w = c.right() - 18 - right_x
        preview = QRect(right_x, top, right_w, 236)
        return {"card": c, "top": top, "tools_x": tools_x,
                "canvas": canvas, "right_x": right_x, "right_w": right_w,
                "preview": preview}

    def place(self) -> None:
        g = self._geo()
        bw = (g["right_w"] - 10) // 2
        by = g["card"].bottom() - 54
        self.cancel_btn.setGeometry(g["right_x"], by, bw, 40)
        self.save_btn.setGeometry(g["right_x"] + bw + 10, by, g["right_w"] - bw - 10, 40)

    # ---------- undo/redo ----------

    def _snapshot(self) -> None:
        self._undo.append(self.img.copy())
        if len(self._undo) > 40:
            self._undo.pop(0)
        self._redo.clear()

    def _undo_step(self) -> None:
        if self._undo:
            self._redo.append(self.img.copy())
            self.img = self._undo.pop()
            self.update()

    def _redo_step(self) -> None:
        if self._redo:
            self._undo.append(self.img.copy())
            self.img = self._redo.pop()
            self.update()

    # ---------- vẽ pixel ----------

    def _texel_at(self, pos: QPoint):
        cv = self._geo()["canvas"]
        if not cv.contains(pos):
            return None
        return ((pos.x() - cv.left()) // TS, (pos.y() - cv.top()) // TS)

    def _paint_color(self) -> QColor:
        return QColor(0, 0, 0, 0) if self.tool == "eraser" else self.color

    def _set(self, tx: int, ty: int) -> None:
        if 0 <= tx < GRID and 0 <= ty < GRID:
            self.img.setPixelColor(tx, ty, self._paint_color())

    def _line(self, a, b) -> None:
        """Bresenham giữa hai texel để nét không đứt khi kéo nhanh."""
        x0, y0 = a
        x1, y1 = b
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._set(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def _flood(self, tx: int, ty: int) -> None:
        target = self.img.pixelColor(tx, ty)
        new = self._paint_color()
        if target == new:
            return
        tr = target.rgba()
        stack = [(tx, ty)]
        while stack:
            x, y = stack.pop()
            if not (0 <= x < GRID and 0 <= y < GRID):
                continue
            if self.img.pixelColor(x, y).rgba() != tr:
                continue
            self.img.setPixelColor(x, y, new)
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # ---------- chuột ----------

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        # bắt đầu vẽ trên canvas
        t = self._texel_at(pos)
        if t is not None:
            tx, ty = t
            if self.tool == "pick":
                col = self.img.pixelColor(tx, ty)
                if col.alpha() > 0:
                    self.color = col
                    self.update()
                return
            self._snapshot()
            if self.tool == "fill":
                self._flood(tx, ty)
            else:
                self._set(tx, ty)
                self._last = t
                self._mode = "paint"
            self.update()
            return
        # xoay preview
        if self._geo()["preview"].contains(pos):
            self._drag_from = pos
            self._mode = "rotate"
            return
        # các nút/ô bấm khác
        for rect, kind, data in self._hit:
            if rect.contains(pos):
                self._handle(kind, data)
                return
        # bấm ra ngoài thẻ: không đóng (tránh mất công vẽ) — chỉ Esc/CANCEL mới đóng

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        if self._mode == "paint" and self.tool in ("pencil", "eraser"):
            t = self._texel_at(pos)
            if t is not None:
                self._line(self._last or t, t)
                self._last = t
                self.update()
        elif self._mode == "rotate" and self._drag_from is not None:
            self._yaw += (pos.x() - self._drag_from.x()) * 0.6
            self._pitch = max(-32.0, min(32.0,
                              self._pitch - (pos.y() - self._drag_from.y()) * 0.5))
            self._drag_from = pos
            self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._mode = None
        self._last = None
        self._drag_from = None

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self.dismiss()
        elif e.matches(e.StandardKey.Undo) or (
                e.modifiers() & Qt.ControlModifier and e.key() == Qt.Key_Z
                and not (e.modifiers() & Qt.ShiftModifier)):
            self._undo_step()
        elif e.matches(e.StandardKey.Redo) or (
                e.modifiers() & Qt.ControlModifier
                and e.key() in (Qt.Key_Y, Qt.Key_Z)):
            self._redo_step()

    def _handle(self, kind: str, data) -> None:
        if kind == "tool":
            self.tool = data
        elif kind == "color":
            self.color = QColor(data)
            if self.tool in ("eraser",):
                self.tool = "pencil"
        elif kind == "custom":
            col = QColorDialog.getColor(self.color, self, "Pick a colour")
            if col.isValid():
                self.color = col
                self.tool = "pencil"
        elif kind == "grid":
            self.show_grid = not self.show_grid
        elif kind == "guide":
            self.show_guide = not self.show_guide
        elif kind == "undo":
            self._undo_step()
        elif kind == "redo":
            self._redo_step()
        elif kind == "clear":
            self._snapshot()
            self.img.fill(Qt.transparent)
        elif kind == "variant":
            self.variant = data
        self.update()

    # ---------- lưu ----------

    def _do_save(self) -> None:
        from PySide6.QtCore import QBuffer, QByteArray
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.WriteOnly)
        self.img.save(buf, "PNG")
        buf.close()
        self.saved.emit(bytes(ba), self.variant)
        self.dismiss()

    # ---------- vẽ giao diện ----------

    def paint_body(self, p: QPainter) -> None:
        self._hit = []
        g = self._geo()
        self._paint_tools(p, g)
        self._paint_canvas(p, g)
        self._paint_right(p, g)

    def _chip(self, p, rect, active, hovered=False):
        p.setPen(Qt.NoPen)
        if active:
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 210))
        else:
            p.setBrush(QColor(255, 255, 255, 22))
        p.drawRoundedRect(QRectF(rect), 6, 6)
        if active:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)

    def _paint_tools(self, p, g) -> None:
        x = g["tools_x"]
        y = g["top"]
        tools = [("pencil", "tool", "pencil"), ("eraser", "tool", "eraser"),
                 ("fill", "tool", "fill"), ("pick", "tool", "pick"),
                 ("undo", "undo", None), ("redo", "redo", None),
                 ("grid", "grid", None), ("guide", "guide", None),
                 ("clear", "clear", None)]
        for name, kind, data in tools:
            r = QRect(x, y, 46, 40)
            active = (kind == "tool" and self.tool == data) or \
                     (kind == "grid" and self.show_grid) or \
                     (kind == "guide" and self.show_guide)
            self._chip(p, r, active)
            self._tool_glyph(p, r, name, active)
            self._hit.append((r, kind, data))
            y += 46

    def _tool_glyph(self, p, r: QRect, name: str, active: bool) -> None:
        cx, cy = r.center().x(), r.center().y()
        col = QColor(255, 255, 255) if active else TEXT_DIM
        p.setPen(QPen(col, 2))
        p.setBrush(Qt.NoBrush)
        if name == "pencil":
            p.drawLine(cx - 7, cy + 7, cx + 6, cy - 6)
            p.drawLine(cx + 6, cy - 6, cx + 9, cy - 3)
            p.drawLine(cx - 7, cy + 7, cx - 4, cy + 9)
        elif name == "eraser":
            p.setBrush(col if not active else QColor(255, 255, 255))
            p.drawRoundedRect(QRectF(cx - 8, cy - 4, 16, 10), 2, 2)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(18, 28, 44), 1))
            p.drawLine(cx - 2, cy - 4, cx - 2, cy + 6)
        elif name == "fill":
            p.setBrush(col)
            pts = [QPoint(cx - 8, cy), QPoint(cx, cy - 8),
                   QPoint(cx + 8, cy), QPoint(cx, cy + 8)]
            from PySide6.QtGui import QPolygon
            p.drawPolygon(QPolygon(pts))
            p.setPen(QPen(col, 2))
            p.drawLine(cx + 9, cy + 1, cx + 9, cy + 7)
        elif name == "pick":
            p.drawLine(cx - 7, cy + 7, cx + 3, cy - 3)
            p.setBrush(col)
            p.drawEllipse(QPoint(cx + 5, cy - 5), 3, 3)
        elif name == "undo":
            p.drawArc(cx - 8, cy - 7, 16, 14, 40 * 16, 260 * 16)
            p.setBrush(col)
            p.drawLine(cx - 8, cy - 2, cx - 8, cy - 8)
            p.drawLine(cx - 8, cy - 8, cx - 2, cy - 8)
        elif name == "redo":
            p.drawArc(cx - 8, cy - 7, 16, 14, -100 * 16, 260 * 16)
            p.setBrush(col)
            p.drawLine(cx + 8, cy - 2, cx + 8, cy - 8)
            p.drawLine(cx + 8, cy - 8, cx + 2, cy - 8)
        elif name == "grid":
            for i in range(-1, 2):
                p.drawLine(cx + i * 5, cy - 7, cx + i * 5, cy + 7)
                p.drawLine(cx - 7, cy + i * 5, cx + 7, cy + i * 5)
        elif name == "guide":
            p.setBrush(Qt.NoBrush)
            p.drawRect(cx - 7, cy - 8, 14, 16)
            p.drawLine(cx - 7, cy, cx + 7, cy)
        elif name == "clear":
            p.drawLine(cx - 7, cy - 7, cx + 7, cy + 7)
            p.drawLine(cx + 7, cy - 7, cx - 7, cy + 7)
        # nhãn nhỏ cho các nút không rõ nghĩa
        p.setFont(ui_font(6))
        p.setPen(TEXT_FAINT)

    def _paint_canvas(self, p, g) -> None:
        cv = g["canvas"]
        # nền ca-rô báo vùng trong suốt
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        light = QColor(60, 72, 92)
        dark = QColor(48, 58, 76)
        cell = TS * 2
        for yy in range(0, cv.height(), cell):
            for xx in range(0, cv.width(), cell):
                p.fillRect(cv.left() + xx, cv.top() + yy, TS, TS, light)
                p.fillRect(cv.left() + xx + TS, cv.top() + yy, TS, TS, dark)
                p.fillRect(cv.left() + xx, cv.top() + yy + TS, TS, TS, dark)
                p.fillRect(cv.left() + xx + TS, cv.top() + yy + TS, TS, TS, light)
        # skin phóng to
        p.drawImage(cv, self.img, QRect(0, 0, GRID, GRID))
        # lưới
        if self.show_grid:
            p.setPen(QPen(QColor(255, 255, 255, 26), 1))
            for i in range(GRID + 1):
                x = cv.left() + i * TS
                y = cv.top() + i * TS
                step = 8 if i % 8 == 0 else 0
                p.setPen(QPen(QColor(255, 255, 255, 55 if step else 20), 1))
                p.drawLine(x, cv.top(), x, cv.bottom())
                p.drawLine(cv.left(), y, cv.right(), y)
        # khung hướng dẫn từng mặt
        if self.show_guide:
            for fx, fy, fw, fh, label in GUIDE_FACES:
                r = QRect(cv.left() + fx * TS, cv.top() + fy * TS, fw * TS, fh * TS)
                p.setPen(QPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 150), 1.4))
                p.setBrush(Qt.NoBrush)
                p.drawRect(r)
                p.setFont(ui_font(6, bold=True))
                p.setPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 220))
                p.drawText(QRect(r.left(), r.top() - 12, 60, 12),
                           Qt.AlignLeft | Qt.AlignBottom, label)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(cv)

    def _paint_right(self, p, g) -> None:
        pv = g["preview"]
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(QRectF(pv), 8, 8)
        if self.img.width() >= 64:
            from . import skin3d
            skin3d.render(p, self.img, pv.center().x(), pv.center().y() + 6,
                          8.0, self._yaw, self._pitch, self.variant == "slim")
        p.setFont(ui_font(7))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(pv.left(), pv.bottom() - 16, pv.width(), 14),
                   Qt.AlignCenter, "drag to rotate")

        x0 = g["right_x"]
        colw = g["right_w"]
        y = pv.bottom() + 16
        # hàng trên: ô màu hiện tại (trái) + toggle Classic/Slim (phải)
        sw = QRect(x0, y, 34, 34)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1))
        p.setBrush(self.color)
        p.drawRoundedRect(QRectF(sw), 5, 5)
        p.setFont(ui_font(9, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(x0 + 44, y, 110, 34), Qt.AlignLeft | Qt.AlignVCenter,
                   self.color.name().upper())
        tgw = 60
        for i, (label, var) in enumerate((("Classic", "classic"), ("Slim", "slim"))):
            r = QRect(x0 + colw - (2 - i) * (tgw + 4) + 4, y + 3, tgw, 28)
            self._chip(p, r, self.variant == var)
            p.setFont(ui_font(8, bold=self.variant == var))
            p.setPen(QColor(255, 255, 255) if self.variant == var else TEXT_DIM)
            p.drawText(r, Qt.AlignCenter, label)
            self._hit.append((r, "variant", var))

        # bảng màu 9×4
        y += 46
        cols = 9
        sz, gap = 26, 5
        for i, hx in enumerate(PALETTE):
            r = QRect(x0 + (i % cols) * (sz + gap), y + (i // cols) * (sz + gap), sz, sz)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(hx))
            p.drawRoundedRect(QRectF(r), 4, 4)
            if QColor(hx) == self.color:
                p.setPen(QPen(QColor(255, 255, 255), 2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(r).adjusted(1, 1, -1, -1), 4, 4)
            self._hit.append((r, "color", hx))
        rows = (len(PALETTE) + cols - 1) // cols
        y += rows * (sz + gap) + 6

        # nút chọn màu tuỳ ý
        cust = QRect(x0, y, cols * (sz + gap) - gap, 32)
        self._chip(p, cust, False)
        p.setFont(ui_font(9, bold=True))
        p.setPen(TEXT)
        p.drawText(cust, Qt.AlignCenter, "＋  Custom colour")
        self._hit.append((cust, "custom", None))
