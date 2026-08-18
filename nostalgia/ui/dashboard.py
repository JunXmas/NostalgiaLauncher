"""Trang Home — dashboard ba phần: hero card, lưới Instances, cột phải Account + News.

Nền để trong suốt cho ảnh hero của cửa sổ hiện xuyên qua; mọi thứ vẽ trên kính.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QWidget

from ..i18n import tr

from .glass import draw_glass_rect
from .theme import (
    ACCENT, AERO_TINT, CONNECTED, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT,
    gloss_gradient, noise_tile, ui_font,
)
from .widgets import AeroButton, draw_cube_icon

PAD = 18
RIGHT_W = 258
RTOP = 40   # cột phải hạ xuống để không bị nút caption đè
HERO_H = 208
CARD_W = 176
CARD_H = 150
GAP = 14


def _hash_hue(name: str) -> QColor:
    """Màu thumbnail suy từ tên, để mỗi instance một sắc riêng ổn định."""
    h = sum(ord(c) * (i + 1) for i, c in enumerate(name)) % 360
    table = [QColor(90, 150, 210), QColor(120, 170, 90), QColor(170, 120, 190),
             QColor(200, 150, 80), QColor(90, 180, 160), QColor(190, 110, 110)]
    return table[h % len(table)]


def _fmt_playtime(seconds: int) -> str:
    """Tổng giờ chơi gọn: '3h 12m', '45m', '0m'."""
    m = max(0, int(seconds)) // 60
    h, m = divmod(m, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _reltime_ms(ms: int) -> str:
    """Khoảng thời gian từ mốc (ms epoch) tới giờ, dạng ngắn."""
    import time
    if not ms:
        return ""
    secs = max(0, time.time() - ms / 1000.0)
    if secs < 90:
        return tr("just now")
    mins = secs / 60
    if mins < 60:
        return tr("{n}m ago").format(n=int(mins))
    hours = mins / 60
    if hours < 24:
        return tr("{n}h ago").format(n=int(hours))
    days = hours / 24
    if days < 30:
        return tr("{n}d ago").format(n=int(days))
    return tr("{n}mo ago").format(n=int(days / 30))


def _continue_glyph(p: QPainter, r: QRect, kind: str) -> None:
    """Icon nhỏ cho mục Continue playing: quả địa cầu (world) / khối server."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    cx, cy = r.center().x(), r.center().y()
    if kind == "world":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(96, 168, 120))
        p.drawEllipse(QRectF(r.left() + 4, r.top() + 4, r.width() - 8, r.height() - 8))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 150), 1.3))
        rad = (r.width() - 8) / 2
        p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))
        p.drawArc(QRectF(cx - rad * 0.5, cy - rad, rad, rad * 2), 90 * 16, 180 * 16)
        p.drawArc(QRectF(cx - rad * 0.5, cy - rad, rad, rad * 2), -90 * 16, 180 * 16)
        p.drawLine(int(cx - rad), cy, int(cx + rad), cy)
    else:  # server
        p.setPen(Qt.NoPen)
        for i in range(2):
            bar = QRectF(r.left() + 4, r.top() + 6 + i * 12, r.width() - 8, 9)
            p.setBrush(QColor(120, 160, 210))
            p.drawRoundedRect(bar, 2, 2)
            p.setBrush(CONNECTED)                 # đèn báo
            p.drawEllipse(QRectF(bar.left() + 4, bar.center().y() - 2, 4, 4))
    p.restore()


_CUBE_IMG = None


def _cube_image():
    """Grass block dùng làm icon instance mặc định (assets/cube.png)."""
    global _CUBE_IMG
    if _CUBE_IMG is None:
        from pathlib import Path
        _CUBE_IMG = QImage(str(Path(__file__).parent / "assets" / "cube.png"))
    return _CUBE_IMG


class HomeDashboard(QWidget):
    scrim = False  # để hero hiện xuyên qua

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self._instances: list[dict] = []
        self._continue: dict | None = None
        self._card_rects: list[tuple[QRect, str]] = []
        self._continue_rects: list[tuple[QRect, str]] = []
        self._hot_hero_links: list[tuple[QRect, str]] = []
        self._hover_card: str | None = None
        self._hover_continue: int = -1
        self._icon_cache: dict = {}      # tên instance -> QImage icon modpack (hoặc None)
        self._avatar_img: QImage | None = None   # đầu skin tài khoản làm avatar
        self._avatar_url = ""
        self.setMouseTracking(True)

        self.play_btn = AeroButton(tr("PLAY"), self, height=58, arrow=True)
        self.play_btn.clicked.connect(self.ctl.toggle_play)
        self.new_btn = AeroButton(tr("NEW INSTANCE"), self, height=30, tone="neutral")
        self.new_btn.clicked.connect(self.ctl.begin_create_instance)
        self.manage_btn = AeroButton(tr("Manage Account"), self, height=28, tone="neutral")
        self.manage_btn.clicked.connect(self.ctl.open_account_menu_dashboard)

    def retranslate(self) -> None:
        self.play_btn.setText(tr("PLAY"))
        self.new_btn.setText(tr("NEW INSTANCE"))
        self.manage_btn.setText(tr("Manage Account"))
        self.update()

    def _got_avatar(self, data) -> None:
        if data:
            img = QImage()
            if img.loadFromData(data):
                self._avatar_img = img
        self.update()

    def _instance_icon(self, inst):
        if inst.name not in self._icon_cache:
            path = self.ctl.instance_dir(inst) / "icon.png"
            img = None
            if path.exists():
                im = QImage()
                if im.load(str(path)) and not im.isNull():
                    img = im
            self._icon_cache[inst.name] = img
        return self._icon_cache[inst.name]

    def refresh(self) -> None:
        self._instances = self.ctl.instances.all()
        self._icon_cache.clear()      # bắt icon modpack mới cài
        # avatar = đầu skin của tài khoản (Microsoft có skin_url)
        acct = self.ctl.current_account()
        url = getattr(acct, "skin_url", "") if acct else ""
        if url != self._avatar_url:
            self._avatar_url = url
            self._avatar_img = None
            if url:
                self.ctl.load_skin(url, self._got_avatar)
        self.ctl.load_continue(self._got_continue)
        self._relayout()
        self.update()

    def _got_continue(self, data) -> None:
        self._continue = data or {"items": [], "playtime": 0}
        for it in self._continue.get("items", []):
            if it["kind"] == "server":
                img = None
                if it.get("icon"):
                    qi = QImage()
                    if qi.loadFromData(it["icon"]):
                        img = qi
                it["_img"] = img
                motd = (it.get("motd") or "").strip()
                it["_title"] = motd or it.get("title") or it.get("ip") or "Server"
                if it.get("online") is not None:
                    it["_sub"] = f"{it['online']}/{it['max']} · {it['instance']}"
                else:
                    it["_sub"] = f"{tr('Server')} · {it['instance']}"
            else:  # world
                it["_img"] = None
                it["_title"] = it["title"]
                it["_sub"] = f"{tr('World')} · {it['instance']} · {_reltime_ms(it.get('last', 0))}"
        self.update()

    # ---------- layout ----------

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._relayout()

    def _center_w(self) -> int:
        return self.width() - RIGHT_W - PAD * 3

    def _relayout(self) -> None:
        cx = PAD
        hero = QRect(cx, PAD, self._center_w(), HERO_H)
        # PLAY to trong hero
        self.play_btn.setGeometry(hero.left() + 26, hero.top() + 96, 210, 58)
        # New Instance nằm ở dải "My Instances"
        inst_top = hero.bottom() + 20
        self.new_btn.setGeometry(hero.right() - 150, inst_top - 2, 150, 30)
        # Manage Account trong cột phải
        rx = self.width() - RIGHT_W - PAD
        self.manage_btn.setGeometry(rx + 14, RTOP + 92, RIGHT_W - 28, 28)

    # ---------- tương tác ----------

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        for rect, name in self._card_rects:
            if rect.contains(pos):
                if name == "\x00new":
                    self.ctl.begin_create_instance()
                else:
                    self.ctl.open_instance(name)
                return
        for rect, inst in self._continue_rects:
            if rect.contains(pos):
                self.ctl.open_instance(inst)
                return
        for rect, action in self._hot_hero_links:
            if rect.contains(pos):
                if action == "version":
                    origin = self.mapTo(self.window(), rect.topLeft())
                    self.ctl.open_instance_menu(QRect(origin, rect.size()))
                elif action.startswith("nav:"):
                    self.ctl.go(action[4:])
                return
        # Không trúng nút nào -> để sự kiện truyền lên cửa sổ để kéo cửa sổ.
        e.ignore()

    def _hot(self, pos) -> bool:
        return (any(r.contains(pos) for r, _ in self._card_rects)
                or any(r.contains(pos) for r, _ in self._continue_rects)
                or any(r.contains(pos) for r, _ in self._hot_hero_links))

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        self.setCursor(Qt.PointingHandCursor if self._hot(pos) else Qt.ArrowCursor)
        hovered = next((name for rect, name in self._card_rects if rect.contains(pos)), None)
        hc = next((i for i, (rect, _) in enumerate(self._continue_rects) if rect.contains(pos)), -1)
        if hovered != self._hover_card or hc != self._hover_continue:
            self._hover_card = hovered
            self._hover_continue = hc
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        if self._hover_card is not None:
            self._hover_card = None
            self.update()

    # ---------- vẽ ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._card_rects.clear()
        self._continue_rects.clear()
        self._hot_hero_links.clear()

        hero = QRect(PAD, PAD, self._center_w(), HERO_H)
        self._paint_hero(p, hero)
        self._paint_instances(p, QRect(PAD, hero.bottom() + 20, self._center_w(),
                                       self.height() - hero.bottom() - 20 - PAD))
        self._paint_right(p, QRect(self.width() - RIGHT_W - PAD, RTOP, RIGHT_W,
                                   self.height() - RTOP - PAD))
        p.end()

    def _card(self, p, rect, *, radius=8, strong=False):
        rf = QRectF(rect)
        win = self.window()
        # Đổ bóng mềm phía dưới để thẻ nổi lên (vẽ viền loe dần, không tô ruột).
        p.setBrush(Qt.NoBrush)
        for i, a in enumerate((30, 18, 9)):
            d = i * 2
            p.setPen(QPen(QColor(4, 10, 22, a), 2))
            p.drawRoundedRect(rf.adjusted(-d, 2 + d, d, 4 + d), radius + d, radius + d)

        # ---- Material Acrylic đầy đủ, cắt theo bo góc ----
        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(rf, radius, radius)
        p.setClipPath(clip)
        # 1. Nền mờ NGAY DƯỚI thẻ (per-element blur — điểm mấu chốt của acrylic thật,
        #    trước đây thiếu: thẻ chỉ phủ tint lên nền sắc nét).
        blurred = getattr(win, "blurred", None)
        if blurred and not blurred.isNull():
            origin = self.mapTo(win, rect.topLeft())
            p.drawPixmap(rect, blurred, QRect(origin, rect.size()))
        # 2. Lớp exclusion — tăng tương phản & độ trong trẻo (lớp Fluent hay thiếu).
        p.setCompositionMode(QPainter.CompositionMode_Exclusion)
        p.fillRect(rf, QColor(42, 56, 86, 40))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        # 3. Sắc kính Aero.
        p.fillRect(rf, QColor(AERO_TINT.red(), AERO_TINT.green(), AERO_TINT.blue(),
                              78 if strong else 54))
        # 4. Nhiễu hạt Acrylic.
        p.fillRect(rf, QBrush(noise_tile()))
        # 5. Vệt bóng gloss nửa trên.
        p.fillRect(rf, gloss_gradient(rf.height(), 0.85))
        p.restore()

        # Viền ngoài.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.drawRoundedRect(rf.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        # Gờ sáng đỉnh + vệt phản chiếu lam ở đáy.
        inner = rf.adjusted(1.5, 1.5, -1.5, -1.5)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1))
        p.drawLine(int(inner.left() + radius), int(inner.top() + 1),
                   int(inner.right() - radius), int(inner.top() + 1))
        p.setPen(QPen(QColor(150, 200, 245, 65), 1))
        p.drawLine(int(inner.left() + radius), int(inner.bottom() - 1),
                   int(inner.right() - radius), int(inner.bottom() - 1))

    def _draw_logo(self, p, rect):
        """Vẽ logo lá vào rect; nếu thiếu asset thì fallback về cube vẽ tay."""
        from .window import logo_pixmap
        logo = logo_pixmap()
        if logo is not None and not logo.isNull():
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.drawPixmap(rect, logo, QRectF(logo.rect()))
        else:
            draw_cube_icon(p, rect, QColor(126, 190, 92), QColor(150, 112, 78))

    def _paint_hero(self, p, hero):
        self._card(p, hero, radius=9, strong=True)
        self._draw_logo(p, QRectF(hero.left() + 22, hero.top() + 20, 38, 38))
        p.setFont(ui_font(22, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(hero.left() + 68, hero.top() + 20, hero.width() - 90, 34),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("Welcome back!"))
        p.setFont(ui_font(10))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(hero.left() + 70, hero.top() + 54, hero.width() - 90, 20),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("What will we build today?"))

        # version pill cạnh PLAY
        pill = QRect(hero.left() + 250, hero.top() + 108, hero.width() - 250 - 26, 34)
        draw_glass_rect(p, QRectF(pill), radius=4, tint=QColor(255, 255, 255, 30), gloss=0.7)
        self._draw_logo(p, QRectF(pill.left() + 7, pill.center().y() - 10, 20, 20))
        p.setFont(ui_font(10, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(pill.left() + 34, pill.top(), pill.width() - 44, pill.height()),
                   Qt.AlignLeft | Qt.AlignVCenter, self.ctl.version_display())
        p.setPen(QPen(TEXT_DIM, 1.4))
        cy = pill.center().y()
        p.drawLine(pill.right() - 16, cy - 2, pill.right() - 12, cy + 2)
        p.drawLine(pill.right() - 12, cy + 2, pill.right() - 8, cy - 2)
        self._hot_hero_links.append((pill, "version"))


    def _paint_instances(self, p, area):
        p.setFont(ui_font(12, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(area.left() + 2, area.top(), 300, 24),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("My Instances"))
        row_top = area.top() + 34
        current = self.ctl.instances.active

        ready = {v["id"] for v in self.ctl.installer.installed_versions() if v["complete"]}
        # Lưới nhiều hàng: lấp đầy chiều rộng LẪN chiều cao vùng còn lại.
        per_row = max(1, (area.width() + GAP) // (CARD_W + GAP))
        rows_fit = max(1, (area.height() - 34 + GAP) // (CARD_H + GAP))
        slots = per_row * rows_fit
        # Instance đang chọn (thứ PLAY sẽ chạy) hiện đầu tiên, khớp với ô version.
        # Chừa 1 ô cuối cho thẻ "+".
        shown = sorted(self._instances, key=lambda i: i.name != current)[:max(0, slots - 1)]

        def slot_rect(idx):
            row, col = divmod(idx, per_row)
            return QRect(area.left() + col * (CARD_W + GAP),
                         row_top + row * (CARD_H + GAP), CARD_W, CARD_H)

        for i, inst in enumerate(shown):
            rect = slot_rect(i)
            self._paint_instance_card(p, rect, inst, inst.name == current,
                                      inst.version in ready,
                                      hover=inst.name == self._hover_card)
            self._card_rects.append((rect, inst.name))
        add_rect = slot_rect(len(shown))
        self._paint_add_card(p, add_rect, empty=not self._instances,
                             hover=self._hover_card == "\x00new")
        self._card_rects.append((add_rect, "\x00new"))

    def _paint_add_card(self, p, rect, empty=False, hover=False):
        # Thẻ tạo instance: viền đứt + dấu cộng lớn. Rê chuột thì sáng lên.
        edge = 150 if hover else (90 if empty else 55)
        fill = 34 if hover else (20 if empty else 12)
        p.setPen(QPen(QColor(255, 255, 255, edge), 1.6, Qt.DashLine))
        p.setBrush(QColor(255, 255, 255, fill))
        p.drawRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 7, 7)
        cx, cy = rect.center().x(), rect.top() + 48
        r = 20
        p.setPen(QPen(ACCENT.lighter(120) if hover else ACCENT, 4))
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawLine(cx, cy - r, cx, cy + r)
        p.setFont(ui_font(10, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(rect.left(), rect.top() + 96, rect.width(), 20),
                   Qt.AlignHCenter | Qt.AlignVCenter, tr("New Instance"))

    def _paint_instance_card(self, p, rect, inst, selected, ready, hover=False):
        self._card(p, rect, radius=7, strong=True)
        # thumbnail
        thumb = QRect(rect.left() + 8, rect.top() + 8, rect.width() - 16, 78)
        col = _hash_hue(inst.name)
        icon = self._instance_icon(inst)
        if icon is not None and not icon.isNull():
            # icon modpack thật: cắt giữa cho vừa khung (aspect-fill), bo góc.
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(thumb), 4, 4)
            p.save()
            p.setClipPath(clip)
            iw, ih = icon.width(), icon.height()
            s = max(thumb.width() / iw, thumb.height() / ih)
            sw, sh = thumb.width() / s, thumb.height() / s
            p.drawImage(QRectF(thumb), icon,
                        QRectF((iw - sw) / 2, (ih - sh) / 2, sw, sh))
            p.restore()
            p.setPen(Qt.NoPen)
            p.setBrush(gloss_gradient(thumb.height(), 0.28))
            p.drawRoundedRect(QRectF(thumb), 4, 4)
        else:
            g = QLinearGradient(thumb.topLeft(), thumb.bottomRight())
            g.setColorAt(0, col.lighter(120))
            g.setColorAt(1, col.darker(130))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(QRectF(thumb), 4, 4)
            p.setBrush(gloss_gradient(thumb.height(), 0.5))
            p.drawRoundedRect(QRectF(thumb), 4, 4)
            cube = _cube_image()
            if cube is not None and not cube.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                d = 46
                p.drawImage(QRectF(thumb.center().x() - d / 2, thumb.center().y() - d / 2, d, d),
                            cube, QRectF(cube.rect()))
            else:
                draw_cube_icon(p, QRectF(thumb.center().x() - 16, thumb.center().y() - 16, 32, 32),
                               QColor(230, 240, 250), col.darker(150))
        if hover:
            # Rê chuột -> phủ nền tối + hiện ▶: dạy người dùng "bấm để mở/chơi".
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 95))
            p.drawRoundedRect(QRectF(thumb), 4, 4)
            c = thumb.center()
            tri = QPainterPath()
            tri.moveTo(c.x() - 9, c.y() - 12)
            tri.lineTo(c.x() + 13, c.y())
            tri.lineTo(c.x() - 9, c.y() + 12)
            tri.closeSubpath()
            p.setBrush(QColor(255, 255, 255, 235))
            p.drawPath(tri)
        if selected or hover:
            p.setPen(QPen(ACCENT if selected else ACCENT.lighter(135), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 7, 7)

        p.setFont(ui_font(10, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(rect.left() + 10, rect.top() + 92, rect.width() - 20, 16),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(inst.name, Qt.ElideRight, rect.width() - 20))
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(rect.left() + 10, rect.top() + 110, rect.width() - 20, 14),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   p.fontMetrics().elidedText(inst.version, Qt.ElideRight, rect.width() - 20))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(rect.left() + 10, rect.top() + 126, rect.width() - 20, 14),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "ready" if ready else "will download on play")

    def _paint_right(self, p, col):
        # --- Account ---
        acc = QRect(col.left(), col.top(), col.width(), 132)
        self._card(p, acc, radius=8, strong=True)
        p.setFont(ui_font(8, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(acc.left() + 14, acc.top() + 10, acc.width() - 28, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("YOUR ACCOUNT"))
        win = self.window()
        # avatar
        av = QRect(acc.left() + 14, acc.top() + 32, 40, 40)
        if self._avatar_img is not None and not self._avatar_img.isNull() \
                and self._avatar_img.width() >= 64:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(av), 4, 4)
            p.save()
            p.setClipPath(clip)
            p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            img = self._avatar_img
            p.drawImage(QRectF(av), img, QRectF(8, 8, 8, 8))    # mặt trước đầu
            p.drawImage(QRectF(av), img, QRectF(40, 8, 8, 8))   # lớp mũ
            p.restore()
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(av), 4, 4)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(150, 112, 78))
            p.drawRoundedRect(QRectF(av), 4, 4)
            draw_cube_icon(p, QRectF(av.center().x() - 12, av.center().y() - 12, 24, 24),
                           QColor(196, 150, 120), QColor(120, 86, 62))
        p.setFont(ui_font(11, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(av.right() + 12, acc.top() + 34, acc.width() - 70, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, win.account_label)
        dot = {"ok": CONNECTED, "warn": DEGRADED}.get(win.account_state, TEXT_FAINT)
        p.setPen(Qt.NoPen)
        p.setBrush(dot)
        p.drawEllipse(QRectF(av.right() + 12, acc.top() + 56, 7, 7))
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(av.right() + 24, acc.top() + 52, acc.width() - 90, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, win.account_mode)

        # --- Continue playing ---
        cont = QRect(col.left(), acc.bottom() + 14, col.width(),
                     col.bottom() - acc.bottom() - 14)
        self._card(p, cont, radius=8, strong=True)
        p.setFont(ui_font(8, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(cont.left() + 14, cont.top() + 10, cont.width() - 28, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("CONTINUE PLAYING"))
        # tổng giờ chơi ở góc phải tiêu đề
        total = (self._continue or {}).get("playtime", 0)
        p.setPen(TEXT_DIM)
        p.drawText(QRect(cont.left() + 14, cont.top() + 10, cont.width() - 28, 14),
                   Qt.AlignRight | Qt.AlignVCenter, _fmt_playtime(total))

        y = cont.top() + 34
        if self._continue is None:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(cont.left() + 14, y, cont.width() - 28, 20),
                       Qt.AlignLeft | Qt.AlignTop, tr("Loading…"))
            return
        items = self._continue.get("items", [])
        if not items:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(cont.left() + 14, y, cont.width() - 28, 40),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                       tr("No worlds or servers yet — play a bit and they'll show up here."))
            return
        fm = p.fontMetrics()
        for e in items:
            if y + 50 > cont.bottom() - 8:
                break
            item = QRect(cont.left() + 10, y, cont.width() - 20, 46)
            if self._hover_continue == len(self._continue_rects):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 20))
                p.drawRoundedRect(QRectF(item), 5, 5)
            icon = QRect(item.left() + 2, item.top() + 7, 32, 32)
            img = e.get("_img")
            if img is not None and not img.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                path = QPainterPath()
                path.addRoundedRect(QRectF(icon), 4, 4)
                p.save()
                p.setClipPath(path)
                p.drawImage(QRectF(icon), img, QRectF(img.rect()))
                p.restore()
            else:
                _continue_glyph(p, icon, e["kind"])
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT)
            title = fm.elidedText(e.get("_title", ""), Qt.ElideRight, item.width() - 48)
            p.drawText(QRect(icon.right() + 8, item.top() + 5, item.width() - 48, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, title)
            p.setFont(ui_font(7))
            p.setPen(TEXT_FAINT)
            sub = fm.elidedText(e.get("_sub", ""), Qt.ElideRight, item.width() - 48)
            p.drawText(QRect(icon.right() + 8, item.top() + 24, item.width() - 48, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, sub)
            self._continue_rects.append((item, e["instance"]))
            y += 50
