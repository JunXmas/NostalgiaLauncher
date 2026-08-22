"""Các thành phần giao diện vẽ tay theo phong cách Aero."""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPointF, QRect, QRectF, Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
    QPolygonF, QRadialGradient,
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


def draw_home_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    p.save()
    p.setPen(QPen(color, 1.5))
    p.setBrush(Qt.NoBrush)
    c = rect.center()
    w = rect.width() * 0.36
    # mái nhà
    p.drawPolygon(QPolygonF([QPointF(c.x() - w, c.y() - 1), QPointF(c.x(), c.y() - w - 2),
                             QPointF(c.x() + w, c.y() - 1)]))
    # thân nhà
    p.drawRect(QRectF(c.x() - w * 0.72, c.y() - 1, w * 1.44, w + 2))
    p.restore()


def draw_mods_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    # cờ-lê đơn giản
    p.save()
    p.setPen(QPen(color, 1.5))
    p.setBrush(Qt.NoBrush)
    c = rect.center()
    r = rect.width() * 0.16
    p.drawEllipse(QPointF(c.x() - rect.width() * 0.18, c.y() - rect.height() * 0.18), r, r)
    p.drawLine(QPointF(c.x() - rect.width() * 0.08, c.y() - rect.height() * 0.08),
               QPointF(c.x() + rect.width() * 0.28, c.y() + rect.height() * 0.28))
    p.restore()


def draw_packs_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    # chồng tài nguyên
    p.save()
    p.setPen(QPen(color, 1.4))
    p.setBrush(Qt.NoBrush)
    x = rect.left() + rect.width() * 0.2
    w = rect.width() * 0.6
    for i in range(3):
        y = rect.top() + rect.height() * (0.24 + i * 0.24)
        p.drawRect(QRectF(x, y, w, rect.height() * 0.16))
    p.restore()


def draw_servers_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    # quả cầu
    p.save()
    p.setPen(QPen(color, 1.4))
    p.setBrush(Qt.NoBrush)
    c = rect.center()
    rr = rect.width() * 0.34
    p.drawEllipse(c, rr, rr)
    p.drawEllipse(c, rr * 0.45, rr)
    p.drawLine(QPointF(c.x() - rr, c.y()), QPointF(c.x() + rr, c.y()))
    p.restore()


def draw_skin_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    # đầu + vai nhân vật
    p.save()
    p.setPen(QPen(color, 1.4))
    p.setBrush(Qt.NoBrush)
    c = rect.center()
    hr = rect.width() * 0.2
    p.drawEllipse(QPointF(c.x(), c.y() - rect.height() * 0.16), hr, hr)
    p.drawArc(QRectF(c.x() - rect.width() * 0.32, c.y() + rect.height() * 0.02,
                     rect.width() * 0.64, rect.height() * 0.5), 0, 180 * 16)
    p.restore()


def draw_shaders_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    # mặt trời: lõi tròn + tia sáng
    import math
    p.save()
    p.setPen(QPen(color, 1.4))
    p.setBrush(Qt.NoBrush)
    c = rect.center()
    rr = rect.width() * 0.18
    p.drawEllipse(c, rr, rr)
    for i in range(8):
        a = math.pi / 4 * i
        d1, d2 = rr * 1.5, rr * 2.15
        p.drawLine(QPointF(c.x() + math.cos(a) * d1, c.y() + math.sin(a) * d1),
                   QPointF(c.x() + math.cos(a) * d2, c.y() + math.sin(a) * d2))
    p.restore()


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    """Nội suy tuyến tính giữa hai màu — dùng cho chuyển màu mượt khi hover."""
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t),
                  int(a.alpha() + (b.alpha() - a.alpha()) * t))


_NAV_PM: dict = {}


def _nav_pixmap(kind: str):
    """Icon Aero (Windows 7) dạng ảnh cho thanh điều hướng; None nếu không có asset."""
    if kind not in _NAV_PM:
        from pathlib import Path

        from PySide6.QtGui import QPixmap
        f = Path(__file__).parent / "assets" / "icons" / f"{kind}.png"
        pm = QPixmap(str(f)) if f.exists() else QPixmap()
        _NAV_PM[kind] = pm if not pm.isNull() else None
    return _NAV_PM[kind]


def _draw_nav_icon(p: QPainter, kind: str, rect: QRectF, color: QColor) -> None:
    pm = _nav_pixmap(kind)
    if pm is not None:
        # Icon bóng nhiều màu: vẽ nguyên màu, hơi to hơn khung; độ mờ theo trạng thái
        # (mục đang chọn/hover sáng rõ, mục thường dịu lại) để vẫn "sống" theo tương tác.
        op = max(0.72, min(1.0, color.lightnessF() + 0.06))
        # Vẽ vào Ô VUÔNG căn giữa (giữ tỉ lệ) để icon không bao giờ bị kéo méo,
        # kể cả khi khung truyền vào không vuông.
        box = rect.adjusted(-2.5, -2.5, 2.5, 2.5)
        side = min(box.width(), box.height())
        sq = QRectF(box.center().x() - side / 2, box.center().y() - side / 2, side, side)
        p.save()
        p.setOpacity(op)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawPixmap(sq, pm, QRectF(pm.rect()))
        p.restore()
        return
    if kind == "cube":
        draw_cube_icon(p, rect, QColor(126, 190, 92), QColor(150, 112, 78))
    elif kind == "gear":
        draw_gear_icon(p, rect, color)
    elif kind == "news":
        draw_news_icon(p, rect, color)
    elif kind == "home":
        draw_home_icon(p, rect, color)
    elif kind == "mods":
        draw_mods_icon(p, rect, color)
    elif kind == "packs":
        draw_packs_icon(p, rect, color)
    elif kind == "servers":
        draw_servers_icon(p, rect, color)
    elif kind == "skin":
        draw_skin_icon(p, rect, color)
    elif kind == "shaders":
        draw_shaders_icon(p, rect, color)
    elif kind == "discord":
        draw_discord_icon(p, rect, color)


_DISCORD_PM = None


def _discord_pixmap():
    global _DISCORD_PM
    if _DISCORD_PM is None:
        from pathlib import Path

        from PySide6.QtGui import QPixmap
        _DISCORD_PM = QPixmap(str(Path(__file__).parent / "assets" / "discord.png"))
    return _DISCORD_PM


def draw_discord_icon(p: QPainter, rect: QRectF, color: QColor) -> None:
    """Logo Discord thật (blurple)."""
    pm = _discord_pixmap()
    if pm is not None and not pm.isNull():
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawPixmap(rect, pm, QRectF(pm.rect()))
        p.restore()
        return
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(rect.adjusted(1, 3, -1, -2), 5, 5)


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

    def __init__(self, text: str, parent=None, *, height: int = 46, tone: str = "green",
                 arrow: bool = False):
        super().__init__(parent)
        self.setText(text)
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.tone = tone
        self.arrow = arrow  # vẽ mũi tên ▶ sau chữ (nút PLAY)
        self._hover = False

        # Trạng thái nhấn có "trọng lượng": _press chạy 0->1 khi bấm (nhanh, nặng),
        # về 0 khi thả với OutBack -> nảy nhẹ lên. Đúng tinh thần cubic-bezier(.25,.8,.25,1).
        self._press = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_anim)
        self.pressed.connect(self._press_down)
        self.released.connect(self._press_up)

        # Trạng thái hover chạy mượt 0<->1 để nút "nhấc lên" chứ không bật tắt phựt:
        # đây là thứ tạo cảm giác nút nổi về phía người dùng khi lia chuột qua.
        self._hover_amt = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.valueChanged.connect(self._on_hover_anim)

    def _on_anim(self, v):
        self._press = float(v)
        self.update()

    def _on_hover_anim(self, v):
        self._hover_amt = float(v)
        self.update()

    def _animate_hover(self, target: float, ms: int):
        self._hover_anim.stop()
        self._hover_anim.setDuration(ms)
        # OutCubic: bung nhanh lúc đầu rồi giảm tốc -> phản hồi tức thì mà vẫn mượt.
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.setStartValue(self._hover_amt)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def _press_down(self):
        self._anim.stop()
        self._anim.setDuration(90)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self._press)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _press_up(self):
        self._anim.stop()
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QEasingCurve.OutBack)  # nảy nhẹ vượt 0 rồi về
        self._anim.setStartValue(self._press)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def enterEvent(self, e):  # noqa: N802
        self._hover = True
        self._animate_hover(1.0, 120)   # nổi lên nhanh
        self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = False
        self._animate_hover(0.0, 170)   # hạ xuống hơi chậm hơn -> tự nhiên
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        press = self._press
        pressPos = max(0.0, press)
        enabled = self.isEnabled()
        hov = self._hover_amt if enabled else 0.0
        top, mid, low, bot, edge, glow_c = TONES.get(self.tone, TONES["green"])
        if not enabled:
            top, mid, low, bot = (c.darker(135) for c in (top, mid, low, bot))

        # Chừa lề cố định để mặt nút có chỗ "nhấc lên" và đổ bóng mà không bị cắt.
        M = 4.0
        # Hover -> phồng nhẹ (grow) và nhấc lên (rise). Nhấn -> xẹp hai thứ đó lại.
        grow = hov * 1.7 * (1.0 - pressPos)
        rise = hov * 3.2 * (1.0 - pressPos)
        # Lún: thu nhỏ khung theo mức nhấn (OutBack cho press<0 -> phồng nhẹ).
        inset = press * min(self.width(), self.height()) * 0.02
        r = QRectF(self.rect()).adjusted(M, M, -M, -M)
        r = r.adjusted(-grow + inset, -grow + inset - rise, grow - inset, grow - inset - rise)

        # Bóng đổ phía dưới: nghỉ thì mờ, hover thì sâu & tối hơn -> tách khỏi nền kính.
        shadow_a = int(30 + 60 * hov - 45 * pressPos)
        if shadow_a > 0 and enabled:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, shadow_a))
            p.drawRoundedRect(r.translated(0, 2.0 + rise * 0.8), 4, 4)

        # Đặc lại khi nhấn: tối đi (density) — trừ vào lift. Lift chạy mượt theo hover.
        lift = int(16 * hov) - int(pressPos * 16)

        # Quầng sáng toả ra ngoài khi rê chuột — Win7 gọi là hot-tracking glow.
        # Tăng dần theo hover, xẹp dần khi nhấn.
        glow_a = int(70 * hov * (1.0 - pressPos))
        if glow_a > 0 and enabled:
            glow = QRadialGradient(r.center(), r.width() * 0.6)
            glow.setColorAt(0.0, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), glow_a))
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

        # Vệt phản chiếu kính LUÔN hiện ở nửa trên — làm mặt nút bóng "ướt" hơn (đặc
        # trưng Aero); sáng thêm khi hover, mờ đi khi nhấn (như mặt kính lún vào).
        sheen_a = int((44 + 22 * hov) * (1.0 - pressPos))
        if sheen_a > 0:
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(r, 3, 3)
            p.setClipPath(clip)
            sheen = QLinearGradient(r.topLeft(), QPointF(r.left(), r.top() + r.height() * 0.5))
            sheen.setColorAt(0.0, QColor(255, 255, 255, sheen_a))
            sheen.setColorAt(0.6, QColor(255, 255, 255, int(sheen_a * 0.16)))
            sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(r.left(), r.top(), r.width(), r.height() * 0.5), sheen)
            p.restore()

        # Bóng đổ nội viền khi nhấn: bề mặt kính lún vào trong (dark inset ở đỉnh).
        if press > 0.01:
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(r, 3, 3)
            p.setClipPath(clip)
            sh = QLinearGradient(r.topLeft(), QPointF(r.left(), r.top() + r.height() * 0.5))
            a = int(press * 90)
            sh.setColorAt(0.0, QColor(0, 20, 8, a))
            sh.setColorAt(1.0, QColor(0, 20, 8, 0))
            p.fillRect(r, sh)
            p.restore()

        big = self.height() >= 44
        # Chữ theo mặt nút: lún xuống khi nhấn, nhấc lên khi hover.
        sink = press * 1.5 - rise
        f = ui_font(13 if big else 9, bold=True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.6 if big else 1.0)
        p.setFont(f)
        # Có mũi tên thì dịch chữ sang trái chút để chừa chỗ.
        shift = -14 if self.arrow else 0
        text_rect = self.rect().translated(shift, int(round(sink)))
        p.setPen(QColor(0, 20, 8, 120))
        p.drawText(text_rect.translated(0, 2), Qt.AlignCenter, self.text())
        p.setPen(QColor(255, 255, 255, 255 if enabled else 150))
        p.drawText(text_rect, Qt.AlignCenter, self.text())

        if self.arrow:
            tw = p.fontMetrics().horizontalAdvance(self.text())
            ax = self.width() / 2 + shift + tw / 2 + 16
            ay = self.height() / 2 + sink  # mũi tên đi theo mặt nút
            s = 7 if big else 5
            tri = QPolygonF([QPointF(ax - s, ay - s), QPointF(ax + s, ay),
                             QPointF(ax - s, ay + s)])
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 30, 12, 120))
            p.drawPolygon(tri.translated(0, 2))
            p.setBrush(QColor(255, 255, 255, 240))
            p.drawPolygon(tri)
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

        # Hover chạy mượt 0<->1: highlight sáng dần và nội dung trượt nhẹ sang phải,
        # thay vì bật tắt phựt — hợp idiom của thanh điều hướng.
        self._hover_amt = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.valueChanged.connect(self._on_hover_anim)

    def _on_hover_anim(self, v):
        self._hover_amt = float(v)
        self.update()

    def _animate_hover(self, target: float, ms: int):
        self._hover_anim.stop()
        self._hover_anim.setDuration(ms)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.setStartValue(self._hover_amt)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, e):  # noqa: N802
        self._hover = True
        self._animate_hover(1.0, 110)
        self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = False
        self._animate_hover(0.0, 150)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        hov = self._hover_amt
        checked = self.isChecked()

        pill = r.adjusted(4, 2, -4, -2)
        if checked:
            # Pill nền accent + viền sáng + hào quang: mục đang chọn phải nổi bật rõ.
            glow = QColor(ACCENT)
            glow.setAlpha(60)
            gr = QRadialGradient(pill.center(), pill.width() * 0.62)
            gr.setColorAt(0.0, glow)
            gr.setColorAt(1.0, QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 0))
            p.setPen(Qt.NoPen)
            p.setBrush(gr)
            p.drawRoundedRect(pill.adjusted(-2, -2, 2, 2), 12, 12)

            grad = QLinearGradient(pill.topLeft(), pill.bottomLeft())
            grad.setColorAt(0.0, QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 92))
            grad.setColorAt(1.0, QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 52))
            p.setBrush(grad)
            p.drawRoundedRect(pill, 9, 9)
            draw_glass_rect(p, pill, tint=QColor(255, 255, 255, 30), gloss=1.0)
            p.setPen(QPen(QColor(255, 255, 255, 46), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(pill.adjusted(0.5, 0.5, -0.5, -0.5), 9, 9)
            # Thanh accent bên trái: cao và sáng hơn trước.
            p.setPen(Qt.NoPen)
            p.setBrush(GREEN_GLOW)
            p.drawRoundedRect(QRectF(r.left() + 4, r.top() + 5, 4, r.height() - 10), 2, 2)
        elif hov > 0.01:
            draw_glass_rect(p, pill,
                            tint=QColor(255, 255, 255, int(34 * hov)), gloss=0.7 * hov)
            # Gợi ý thanh accent mờ khi rê chuột — mời gọi bấm vào.
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), int(150 * hov)))
            p.drawRoundedRect(QRectF(r.left() + 4, r.top() + 9, 3, r.height() - 18), 1.5, 1.5)

        # Trượt nội dung sang phải theo hover (mục đang chọn thì đứng yên).
        dx = 0.0 if checked else hov * 4.0
        # Màu icon/chữ chuyển mượt từ mờ -> rõ theo hover.
        base = TEXT if checked else _mix(TEXT_DIM, TEXT, hov)
        icon_rect = QRectF(r.left() + 16 + dx, r.center().y() - 10, 20, 20)
        # Mục đang chọn: icon nhuốm xanh accent cho nổi bật.
        color = _mix(TEXT, GREEN_GLOW, 0.55) if checked else base
        _draw_nav_icon(p, self.icon_kind, icon_rect, color)

        text_left = int(r.left() + 46 + dx)
        if self.subtitle:
            f = ui_font(7)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
            p.setFont(f)
            p.setPen(TEXT_DIM if checked else _mix(TEXT_FAINT, TEXT_DIM, hov))
            p.drawText(QRect(text_left, int(r.top() + 8), self.width() - 50, 11),
                       Qt.AlignLeft | Qt.AlignTop, self.text())
            p.setFont(ui_font(10, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(text_left, int(r.top() + 24), self.width() - 50, 18),
                       Qt.AlignLeft | Qt.AlignTop, self.subtitle)
        else:
            p.setFont(ui_font(11, bold=checked))
            p.setPen(TEXT if checked else color)
            p.drawText(QRect(text_left, int(r.top()), self.width() - 52, int(r.height())),
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
        self._compute_widths()

        # Gạch chân accent trượt mượt từ tab cũ sang tab mới khi đổi.
        self._ul_current = -1
        self._ul_x = 0.0
        self._ul_w = 0.0
        self._ul_from = (0.0, 0.0)
        self._ul_to = (0.0, 0.0)
        self._ul_anim = QVariantAnimation(self)
        self._ul_anim.valueChanged.connect(self._on_ul)
        # Fade màu chữ của tab đang rê chuột.
        self._hover_amt = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.valueChanged.connect(self._on_hover_anim)

    def _compute_widths(self) -> None:
        fm = QFontMetrics(ui_font(9))
        self._widths = [fm.horizontalAdvance(t) + 28 for t in self.labels]

    def _index_at(self, x: int) -> int:
        acc = 0
        for i, w in enumerate(self._widths):
            if acc <= x < acc + w:
                return i
            acc += w
        return -1

    def _underline_target(self, i: int) -> tuple[float, float]:
        x = sum(self._widths[:i])
        return x + 10, self._widths[i] - 20

    def _on_ul(self, t):
        t = float(t)
        fx, fw = self._ul_from
        tx, tw = self._ul_to
        self._ul_x = fx + (tx - fx) * t
        self._ul_w = fw + (tw - fw) * t
        self.update()

    def _on_hover_anim(self, v):
        self._hover_amt = float(v)
        self.update()

    def _sync_underline(self) -> None:
        """Bắt kịp mọi thay đổi current (kể cả gán từ bên ngoài) để trượt gạch chân."""
        if self.current == self._ul_current or not self.labels:
            return
        first = self._ul_current < 0
        self._ul_current = self.current
        tx, tw = self._underline_target(self.current)
        if first:  # lần đầu: đặt thẳng, không trượt
            self._ul_x, self._ul_w = tx, tw
            return
        self._ul_from = (self._ul_x, self._ul_w)
        self._ul_to = (tx, tw)
        self._ul_anim.stop()
        self._ul_anim.setDuration(240)
        self._ul_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._ul_anim.setStartValue(0.0)
        self._ul_anim.setEndValue(1.0)
        self._ul_anim.start()

    def mouseMoveEvent(self, e):  # noqa: N802
        idx = self._index_at(e.position().x())
        if idx != self._hover:
            self._hover = idx
            self._hover_anim.stop()
            self._hover_anim.setDuration(120)
            self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._hover_anim.setStartValue(0.0 if idx >= 0 else self._hover_amt)
            self._hover_anim.setEndValue(1.0 if idx >= 0 else 0.0)
            self._hover_anim.start()
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = -1
        self._hover_anim.stop()
        self._hover_anim.setDuration(140)
        self._hover_anim.setStartValue(self._hover_amt)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
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
        self._compute_widths()
        self._sync_underline()
        x = 0
        for i, label in enumerate(self.labels):
            w = self._widths[i]
            active = i == self.current
            p.setFont(ui_font(9, bold=active))
            if active:
                col = TEXT
            elif i == self._hover:
                col = _mix(TEXT_FAINT, TEXT_DIM, self._hover_amt)
            else:
                col = TEXT_FAINT
            p.setPen(col)
            p.drawText(QRect(x, 0, w, self.height() - 4), Qt.AlignCenter, label)
            x += w
        # gạch chân trượt (một dải duy nhất, vị trí do animation quyết định)
        if self._ul_w > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(QRectF(self._ul_x, self.height() - 3, self._ul_w, 3), 1.5, 1.5)
        p.end()
