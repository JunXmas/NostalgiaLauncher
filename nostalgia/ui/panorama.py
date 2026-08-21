"""Trang "Theme Panorama" — lưới thẻ chọn ảnh nền panorama cho menu game, phong
cách Modrinth/CurseForge nhưng vẽ tay theo chất liệu Aero Glass của launcher.

Chọn một thẻ -> lưu vào settings (ctl.set_panorama_theme) -> launcher dựng lại
pack/jar Aero với 6 mặt panorama của theme đó cho mọi instance. Theme lấy từ
aero.panorama_themes() (2 bộ dựng sẵn day/night + theme người dùng nhập).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor, QImage, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QWidget

from .. import aero
from ..i18n import tr
from .theme import (
    ACCENT, AERO_TINT, CONNECTED, TEXT, TEXT_DIM, TEXT_FAINT,
    gloss_gradient, noise_tile, ui_font,
)

# Thẻ + lưới.
CARD_W = 300
CARD_H = 256
PREVIEW_H = 128           # nửa trên = ảnh xem trước
GAP = 18
PAD = 26
RADIUS = 10

# Mô tả/tags gợi ý theo id theme (mock data; theme người dùng nhập dùng mặc định).
_META = {
    "day":   ("by Nostalgia", "Bầu trời Aero ban ngày — trong trẻo, xanh mát.",
              ["360° Panorama", "Animated", "Aero Theme"]),
    "night": ("by Nostalgia", "Nền menu ban đêm — trầm, hợp chơi khuya.",
              ["360° Panorama", "Animated", "Dark"]),
}
_DEFAULT_TAGS = ["360° Panorama", "Animated", "Custom"]


class PanoramaPage(QWidget):
    """Lưới thẻ chọn theme panorama. Tự cuộn bằng con lăn."""

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.setMouseTracking(True)
        self._themes: list[dict] = []
        self._preview_cache: dict[str, QPixmap] = {}
        self._card_rects: list[tuple[QRect, str]] = []
        self._hover: str | None = None
        self._scroll = 0
        self._content_h = 0
        self.refresh()

    # ---------- dữ liệu ----------

    def refresh(self) -> None:
        """Nạp lại danh sách theme + theme đang chọn, rồi vẽ lại."""
        self._themes = aero.panorama_themes()
        self._preview_cache.clear()
        self._relayout()
        self.update()

    @property
    def _active_id(self) -> str:
        return getattr(self.ctl.settings, "panorama_theme", "") or ""

    def _preview(self, theme: dict) -> QPixmap | None:
        """Ảnh xem trước (panorama_0) đã scale-to-cover, có cache."""
        tid = theme["id"]
        if tid in self._preview_cache:
            return self._preview_cache[tid]
        img = QImage(str(theme["preview"]))
        if img.isNull():
            return None
        pm = QPixmap.fromImage(img)
        self._preview_cache[tid] = pm
        return pm

    # ---------- bố cục ----------

    def resizeEvent(self, event):  # noqa: N802
        self._relayout()

    def _columns(self) -> int:
        avail = self.width() - 2 * PAD
        return max(1, (avail + GAP) // (CARD_W + GAP))

    def _relayout(self) -> None:
        cols = self._columns()
        rows = (len(self._themes) + cols - 1) // max(1, cols)
        # Căn giữa khối lưới theo bề ngang.
        grid_w = cols * CARD_W + (cols - 1) * GAP
        x0 = max(PAD, (self.width() - grid_w) // 2)
        self._card_rects.clear()
        for i, t in enumerate(self._themes):
            r, c = divmod(i, cols)
            x = x0 + c * (CARD_W + GAP)
            y = PAD + 40 + r * (CARD_H + GAP) - self._scroll
            self._card_rects.append((QRect(x, y, CARD_W, CARD_H), t["id"]))
        self._content_h = PAD + 40 + rows * (CARD_H + GAP) + PAD

    def wheelEvent(self, e):  # noqa: N802
        vh = self.height()
        maxs = max(0, self._content_h - vh)
        self._scroll = min(maxs, max(0, self._scroll - e.angleDelta().y()))
        self._relayout()
        self.update()

    # ---------- tương tác ----------

    def _at(self, pos) -> str | None:
        for rect, tid in self._card_rects:
            if rect.contains(pos):
                return tid
        return None

    def mouseMoveEvent(self, e):  # noqa: N802
        hit = self._at(e.position().toPoint())
        self.setCursor(Qt.PointingHandCursor if hit else Qt.ArrowCursor)
        if hit != self._hover:
            self._hover = hit
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        if self._hover is not None:
            self._hover = None
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() != Qt.LeftButton:
            return
        tid = self._at(e.position().toPoint())
        if tid and tid != self._active_id:
            # >>> Gửi lựa chọn xuống backend launcher: lưu settings + dựng lại pack/jar
            #     Aero cho mọi instance (xem app.set_panorama_theme -> aero.apply...).
            self.ctl.set_panorama_theme(tid)
            self.update()

    def retranslate(self) -> None:
        self.update()

    # ---------- vẽ ----------

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Tiêu đề mục.
        p.setFont(ui_font(15, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(PAD, PAD - self._scroll, self.width() - 2 * PAD, 30),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("Theme Panorama"))
        for rect, tid in self._card_rects:
            if rect.bottom() < 0 or rect.top() > self.height():
                continue  # ngoài khung nhìn -> khỏi vẽ
            theme = next((t for t in self._themes if t["id"] == tid), None)
            if theme:
                self._paint_card(p, rect, theme)

    def _paint_card(self, p: QPainter, rect: QRect, theme: dict) -> None:
        tid = theme["id"]
        active = tid == self._active_id
        hovered = tid == self._hover
        rf = QRectF(rect)
        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(rf, RADIUS, RADIUS)
        p.setClipPath(clip)

        # --- nền kính acrylic (blur nền dưới thẻ nếu có) ---
        win = self.window()
        blurred = getattr(win, "blurred", None)
        if blurred and not blurred.isNull():
            origin = self.mapTo(win, rect.topLeft())
            p.drawPixmap(rect, blurred, QRect(origin, rect.size()))
        p.fillRect(rf, QColor(30, 30, 36, 205))          # dark glass #1e1e24
        p.fillRect(rf, QColor(AERO_TINT.red(), AERO_TINT.green(), AERO_TINT.blue(), 40))
        p.fillRect(rf, QBrushNoise())

        # --- ảnh xem trước (nửa trên) ---
        prev = self._preview(theme)
        pv = QRect(rect.left(), rect.top(), rect.width(), PREVIEW_H)
        if prev and not prev.isNull():
            scaled = prev.scaled(pv.size(), Qt.KeepAspectRatioByExpanding,
                                 Qt.SmoothTransformation)
            sx = (scaled.width() - pv.width()) // 2
            sy = (scaled.height() - pv.height()) // 2
            p.drawPixmap(pv, scaled, QRect(sx, sy, pv.width(), pv.height()))
        else:
            p.fillRect(pv, QColor(24, 40, 64, 220))
        # Vệt tối chân ảnh cho chữ dễ đọc.
        p.fillRect(QRect(pv.left(), pv.bottom() - 26, pv.width(), 26),
                   QColor(20, 22, 28, 150))
        p.fillRect(rf, gloss_gradient(rf.height(), 0.5))
        p.restore()

        # --- phần thông tin (nửa dưới) ---
        info_top = rect.top() + PREVIEW_H
        ix = rect.left() + 14
        # Icon vuông 48x48 bo góc (dùng chính ảnh preview thu nhỏ).
        icon_r = QRect(ix, info_top + 12, 48, 48)
        p.save()
        ic = QPainterPath()
        ic.addRoundedRect(QRectF(icon_r), 8, 8)
        p.setClipPath(ic)
        if prev and not prev.isNull():
            sq = prev.scaled(icon_r.size(), Qt.KeepAspectRatioByExpanding,
                             Qt.SmoothTransformation)
            p.drawPixmap(icon_r, sq, QRect(0, 0, min(sq.width(), 48), min(sq.height(), 48)))
        else:
            p.fillRect(icon_r, QColor(60, 90, 130))
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 45), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(icon_r), 8, 8)

        tx = icon_r.right() + 12
        tw = rect.right() - tx - 14
        source, desc, tags = _META.get(
            tid, (f"by {'Nostalgia' if theme['builtin'] else 'You'}",
                  tr("Custom panorama background you imported."), _DEFAULT_TAGS))
        # Tiêu đề + nguồn.
        p.setFont(ui_font(11, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(tx, info_top + 12, tw, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, theme["name"])
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(tx, info_top + 32, tw, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, source)
        # Mô tả 2 dòng.
        p.setFont(ui_font(8))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(ix, info_top + 66, rect.width() - 28, 30),
                   Qt.AlignLeft | Qt.TextWordWrap, desc)
        # Tags (chừa lề phải cho badge trạng thái ở cùng hàng, khỏi đè lên nhau).
        self._paint_tags(p, QRect(ix, info_top + 98, rect.width() - 28 - 96, 18), tags)

        # Thanh trạng thái dưới: badge Active hoặc gợi ý Select.
        badge = QRect(rect.right() - 92, rect.bottom() - 30, 78, 20)
        if active:
            p.setBrush(QColor(CONNECTED.red(), CONNECTED.green(), CONNECTED.blue(), 210))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(badge), 10, 10)
            p.setFont(ui_font(8, bold=True))
            p.setPen(QColor(10, 24, 14))
            p.drawText(badge, Qt.AlignCenter, tr("Active"))
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1))
            p.drawRoundedRect(QRectF(badge), 10, 10)
            p.setFont(ui_font(8, bold=True))
            p.setPen(TEXT_DIM)
            p.drawText(badge, Qt.AlignCenter, tr("Select"))

        # --- viền: active (cyan/xanh Aero) + check, hoặc hover glow, hoặc thường ---
        p.setBrush(Qt.NoBrush)
        if active:
            glow = QColor(96, 208, 200)
            p.setPen(QPen(glow, 2))
            p.drawRoundedRect(rf.adjusted(1, 1, -1, -1), RADIUS, RADIUS)
            # Check góc trên-phải.
            ck = QRect(rect.right() - 34, rect.top() + 10, 22, 22)
            p.setBrush(glow)
            p.setPen(Qt.NoPen)
            p.drawEllipse(ck)
            p.setPen(QPen(QColor(12, 30, 30), 2))
            p.drawLine(ck.left() + 6, ck.center().y() + 1,
                       ck.center().x() - 1, ck.bottom() - 6)
            p.drawLine(ck.center().x() - 1, ck.bottom() - 6,
                       ck.right() - 5, ck.top() + 6)
        elif hovered:
            p.setPen(QPen(QColor(150, 210, 255, 190), 2))
            p.drawRoundedRect(rf.adjusted(1, 1, -1, -1), RADIUS, RADIUS)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 55), 1))
            p.drawRoundedRect(rf.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)

    def _paint_tags(self, p: QPainter, area: QRect, tags: list[str]) -> None:
        p.setFont(ui_font(7))
        x = area.left()
        fm = p.fontMetrics()
        for tag in tags:
            w = fm.horizontalAdvance(tag) + 16
            if x + w > area.right():
                break
            pill = QRect(x, area.top(), w, 16)
            p.setBrush(QColor(70, 116, 170, 70))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(pill), 8, 8)
            p.setPen(QColor(198, 220, 240))
            p.drawText(pill, Qt.AlignCenter, tag)
            x += w + 6


def QBrushNoise():
    """Brush hạt nhiễu acrylic (bọc noise_tile của theme)."""
    from PySide6.QtGui import QBrush
    return QBrush(noise_tile())
