"""Trang Home — dashboard ba phần: hero card, lưới Instances, cột phải Account + News.

Nền để trong suốt cho ảnh hero của cửa sổ hiện xuyên qua; mọi thứ vẽ trên kính.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

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


class HomeDashboard(QWidget):
    scrim = False  # để hero hiện xuyên qua

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self._instances: list[dict] = []
        self._news: list[dict] = []
        self._card_rects: list[tuple[QRect, str]] = []
        self._news_rects: list[tuple[QRect, str]] = []
        self._hot_hero_links: list[tuple[QRect, str]] = []
        self.setMouseTracking(True)

        self.play_btn = AeroButton("PLAY", self, height=58, arrow=True)
        self.play_btn.clicked.connect(self.ctl.start_launch)
        self.new_btn = AeroButton("NEW INSTANCE", self, height=30, tone="neutral")
        self.new_btn.clicked.connect(self.ctl.begin_create_instance)
        self.manage_btn = AeroButton("Manage Account", self, height=28, tone="neutral")
        self.manage_btn.clicked.connect(self.ctl.open_account_menu_dashboard)

    def refresh(self) -> None:
        self._instances = self.ctl.instances.all()
        if not self._news:
            self.ctl.load_news(self._got_news)
        self._relayout()
        self.update()

    def _got_news(self, entries) -> None:
        self._news = entries or []
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
                self.ctl.set_active_instance(name)
                return
        for rect, url in self._news_rects:
            if rect.contains(pos):
                self.ctl.open_url(url)
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
                or any(r.contains(pos) for r, _ in self._news_rects)
                or any(r.contains(pos) for r, _ in self._hot_hero_links))

    def mouseMoveEvent(self, e):  # noqa: N802
        self.setCursor(Qt.PointingHandCursor if self._hot(e.position().toPoint())
                       else Qt.ArrowCursor)

    # ---------- vẽ ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._card_rects.clear()
        self._news_rects.clear()
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

    def _paint_hero(self, p, hero):
        self._card(p, hero, radius=9, strong=True)
        draw_cube_icon(p, QRectF(hero.left() + 24, hero.top() + 22, 34, 34),
                       QColor(126, 190, 92), QColor(150, 112, 78))
        p.setFont(ui_font(22, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(hero.left() + 68, hero.top() + 20, hero.width() - 90, 34),
                   Qt.AlignLeft | Qt.AlignVCenter, "Welcome back!")
        p.setFont(ui_font(10))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(hero.left() + 70, hero.top() + 54, hero.width() - 90, 20),
                   Qt.AlignLeft | Qt.AlignVCenter, "What will we build today?")

        # version pill cạnh PLAY
        pill = QRect(hero.left() + 250, hero.top() + 108, hero.width() - 250 - 26, 34)
        draw_glass_rect(p, QRectF(pill), radius=4, tint=QColor(255, 255, 255, 30), gloss=0.7)
        draw_cube_icon(p, QRectF(pill.left() + 8, pill.center().y() - 9, 18, 18),
                       QColor(126, 190, 92), QColor(150, 112, 78))
        p.setFont(ui_font(10, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(pill.left() + 34, pill.top(), pill.width() - 44, pill.height()),
                   Qt.AlignLeft | Qt.AlignVCenter, self.ctl.version_display())
        p.setPen(QPen(TEXT_DIM, 1.4))
        cy = pill.center().y()
        p.drawLine(pill.right() - 16, cy - 2, pill.right() - 12, cy + 2)
        p.drawLine(pill.right() - 12, cy + 2, pill.right() - 8, cy - 2)
        self._hot_hero_links.append((pill, "version"))

        # quick links
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.drawLine(hero.left() + 24, hero.bottom() - 34, hero.right() - 24, hero.bottom() - 34)
        links = [("Browse Mods", "mods"), ("Instances", "installations"),
                 ("Skin", "skins"), ("Settings", "settings")]
        lx = hero.left() + 26
        p.setFont(ui_font(9))
        for label, action in links:
            wdt = p.fontMetrics().horizontalAdvance(label) + 24
            rect = QRect(lx, hero.bottom() - 28, wdt, 20)
            p.setPen(ACCENT)
            p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, label)
            self._hot_hero_links.append((rect, "nav:" + action))
            lx += wdt + 16

    def _paint_instances(self, p, area):
        p.setFont(ui_font(12, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(area.left() + 2, area.top(), 300, 24),
                   Qt.AlignLeft | Qt.AlignVCenter, "My Instances")
        row_top = area.top() + 34
        current = self.ctl.instances.active

        if not self._instances:
            p.setFont(ui_font(9))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(area.left() + 2, row_top, area.width() - 4, 40),
                       Qt.AlignLeft | Qt.AlignTop,
                       "No instances yet. Click NEW INSTANCE to make one (name + version).")
            return

        ready = {v["id"] for v in self.ctl.installer.installed_versions() if v["complete"]}
        x = area.left()
        per_row = max(1, (area.width() + GAP) // (CARD_W + GAP))
        for inst in self._instances[:per_row]:
            rect = QRect(x, row_top, CARD_W, CARD_H)
            self._paint_instance_card(p, rect, inst, inst.name == current,
                                      inst.version in ready)
            self._card_rects.append((rect, inst.name))
            x += CARD_W + GAP

    def _paint_instance_card(self, p, rect, inst, selected, ready):
        self._card(p, rect, radius=7, strong=True)
        # thumbnail
        thumb = QRect(rect.left() + 8, rect.top() + 8, rect.width() - 16, 78)
        col = _hash_hue(inst.name)
        g = QLinearGradient(thumb.topLeft(), thumb.bottomRight())
        g.setColorAt(0, col.lighter(120))
        g.setColorAt(1, col.darker(130))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(thumb), 4, 4)
        p.setBrush(gloss_gradient(thumb.height(), 0.5))
        p.drawRoundedRect(QRectF(thumb), 4, 4)
        draw_cube_icon(p, QRectF(thumb.center().x() - 16, thumb.center().y() - 16, 32, 32),
                       QColor(230, 240, 250), col.darker(150))
        if selected:
            p.setPen(QPen(ACCENT, 2))
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
                   Qt.AlignLeft | Qt.AlignVCenter, "YOUR ACCOUNT")
        win = self.window()
        # avatar
        av = QRect(acc.left() + 14, acc.top() + 32, 40, 40)
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

        # --- News ---
        news = QRect(col.left(), acc.bottom() + 14, col.width(),
                     col.bottom() - acc.bottom() - 14)
        self._card(p, news, radius=8, strong=True)
        p.setFont(ui_font(8, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(news.left() + 14, news.top() + 10, news.width() - 28, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, "NEWS")
        y = news.top() + 32
        if not self._news:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(news.left() + 14, y, news.width() - 28, 20),
                       Qt.AlignLeft | Qt.AlignTop, "Loading…")
            return
        for e in self._news:
            if y + 52 > news.bottom() - 8:
                break
            item = QRect(news.left() + 10, y, news.width() - 20, 50)
            if any(r is item for r, _ in self._news_rects):
                pass
            # thumbnail nhỏ
            th = QRect(item.left(), item.top() + 4, 42, 42)
            col2 = _hash_hue(e["title"])
            p.setPen(Qt.NoPen)
            p.setBrush(col2)
            p.drawRoundedRect(QRectF(th), 3, 3)
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT)
            fm = p.fontMetrics()
            title = fm.elidedText(e["title"], Qt.ElideRight, item.width() - 54)
            p.drawText(QRect(th.right() + 8, item.top() + 4, item.width() - 54, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, title)
            p.setFont(ui_font(7))
            p.setPen(TEXT_FAINT)
            sub = fm.elidedText(e.get("date", ""), Qt.ElideRight, item.width() - 54)
            p.drawText(QRect(th.right() + 8, item.top() + 24, item.width() - 54, 22),
                       Qt.AlignLeft | Qt.AlignTop, sub)
            self._news_rects.append((item, e.get("url", "")))
            y += 54
