"""Trang duyệt modpack kiểu Modrinth: cột lọc trái + thẻ kết quả giàu thông tin.

Thay cho hộp thoại nhỏ trước đây. Bố cục: header (BACK + số kết quả) · cột lọc
(Category, Game version) · thanh search + Sort · danh sách thẻ modpack cuộn được.
Bấm một thẻ để cài modpack thành instance mới.
"""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import (
    QEasingCurve, QRect, QRectF, Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QLineEdit, QWidget

from .. import modrinth
from .dialogs import INPUT_QSS, _compact
from .menus import MenuItem, popup
from .pages import Page
from .theme import ACCENT, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font
from .widgets import AeroButton

CATEGORIES = [
    ("Adventure", "adventure"), ("Challenging", "challenging"),
    ("Combat", "combat"), ("Kitchen Sink", "kitchen-sink"),
    ("Lightweight", "lightweight"), ("Magic", "magic"),
    ("Multiplayer", "multiplayer"), ("Optimization", "optimization"),
    ("Quests", "quests"), ("Technology", "technology"),
]
SORTS = [("Relevance", "relevance"), ("Downloads", "downloads"),
         ("Follows", "follows"), ("Newest", "newest"), ("Updated", "updated")]

SIDEBAR_W = 196
CARD_H = 104
PANEL_TOP = 90      # dưới dải kéo cửa sổ (46px) để nút BACK bấm được
CAT_TOP = 128       # hàng category đầu tiên


def _ago(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    for div, unit in ((31536000, "year"), (2592000, "month"), (86400, "day"),
                      (3600, "hour"), (60, "minute")):
        n = int(secs // div)
        if n >= 1:
            return f"{n} {unit}{'s' if n > 1 else ''} ago"
    return "just now"


class ModpackCards(QWidget):
    """Danh sách thẻ modpack cuộn được, tự vẽ — icon, tên, mô tả, số liệu, tag."""

    activated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hits: list = []
        self.icons: dict = {}
        self.empty_text = "Loading modpacks…"
        self.scroll = 0
        self._hover = -1
        self._hover_amt = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.valueChanged.connect(self._on_anim)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def _on_anim(self, v):
        self._hover_amt = float(v)
        self.update()

    def set_hits(self, hits) -> None:
        self.hits = hits
        self.scroll = 0
        self.update()

    def _content_h(self) -> int:
        return len(self.hits) * CARD_H

    def _rect_of(self, i: int) -> QRect:
        return QRect(0, i * CARD_H - self.scroll, self.width(), CARD_H)

    def _index_at(self, y: int) -> int:
        i = (y + self.scroll) // CARD_H
        return i if 0 <= i < len(self.hits) else -1

    def mouseMoveEvent(self, e):  # noqa: N802
        i = self._index_at(int(e.position().y()))
        if i != self._hover:
            self._hover = i
            self._anim.stop()
            self._anim.setDuration(120)
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0 if i >= 0 else 0.0)
            self._anim.start()
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        i = self._index_at(int(e.position().y()))
        if i >= 0:
            self.activated.emit(self.hits[i])

    def wheelEvent(self, e):  # noqa: N802
        overflow = self._content_h() - self.height()
        if overflow > 0:
            self.scroll = max(0, min(overflow, self.scroll - e.angleDelta().y()))
            self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.hits:
            p.setFont(ui_font(9))
            p.setPen(TEXT_FAINT)
            p.drawText(self.rect(), Qt.AlignCenter, self.empty_text)
            p.end()
            return
        for i, hit in enumerate(self.hits):
            r = self._rect_of(i)
            if r.bottom() < 0 or r.top() > self.height():
                continue
            self._paint_card(p, hit, r, i == self._hover)
        # thanh cuộn mảnh
        overflow = self._content_h() - self.height()
        if overflow > 0:
            frac = self.height() / self._content_h()
            bar_h = max(28, int(self.height() * frac))
            y = int((self.height() - bar_h) * (self.scroll / overflow))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 55))
            p.drawRoundedRect(QRectF(self.width() - 5, y, 3, bar_h), 1.5, 1.5)
        p.end()

    def _paint_card(self, p: QPainter, hit: dict, r: QRect, hovered: bool) -> None:
        body = QRectF(r.adjusted(2, 4, -8, -4))
        amt = self._hover_amt if hovered else 0.0
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, int(12 + 16 * amt)))
        p.drawRoundedRect(body, 7, 7)
        if hovered:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(),
                                 int(150 * amt)), 1.3))
            p.drawRoundedRect(body.adjusted(0.6, 0.6, -0.6, -0.6), 7, 7)

        # icon
        d = 64
        ir = QRectF(body.left() + 12, body.center().y() - d / 2, d, d)
        path = QPainterPath()
        path.addRoundedRect(ir, 10, 10)
        p.save()
        p.setClipPath(path)
        pm = self.icons.get(hit.get("icon_url") or "")
        if pm and not pm.isNull():
            p.drawPixmap(ir.toRect(), pm)
        else:
            p.fillRect(ir, QColor(255, 255, 255, 18))
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(ir, 10, 10)

        left = int(ir.right() + 14)
        stat_w = 150
        text_w = int(body.right() - left - stat_w - 14)

        # tiêu đề + tác giả
        title = hit.get("title", "?")
        p.setFont(ui_font(12, bold=True))
        fm = p.fontMetrics()
        tw = min(fm.horizontalAdvance(title), text_w)
        p.setPen(TEXT)
        p.drawText(QRect(left, int(body.top()) + 12, tw + 2, 20),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   fm.elidedText(title, Qt.ElideRight, text_w))
        author = hit.get("author", "")
        if author and tw + 60 < text_w:
            p.setFont(ui_font(9))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(left + tw + 8, int(body.top()) + 12, text_w - tw - 8, 20),
                       Qt.AlignLeft | Qt.AlignVCenter, f"by {author}")

        # mô tả (2 dòng, tự xuống dòng, cắt gọn trong khung)
        p.setFont(ui_font(9))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(left, int(body.top()) + 34, text_w, 32),
                   Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                   hit.get("description", ""))

        # tag ở đáy
        self._paint_tags(p, hit, left, int(body.bottom()) - 24, text_w)

        # cột số liệu bên phải
        rx = int(body.right() - stat_w)
        rw = stat_w - 6
        p.setFont(ui_font(9, bold=True))
        p.setPen(TEXT)
        dl = _compact(hit.get("downloads", 0))
        fol = _compact(hit.get("follows", 0))
        p.drawText(QRect(rx, int(body.top()) + 14, rw, 16),
                   Qt.AlignRight | Qt.AlignVCenter, f"⬇ {dl}    ♡ {fol}")
        ago = _ago(hit.get("date_modified", ""))
        if ago:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(rx, int(body.top()) + 34, rw, 14),
                       Qt.AlignRight | Qt.AlignVCenter, f"updated {ago}")

        # gợi ý cài: chip xanh "INSTALL" hiện khi hover
        if hovered:
            chip = QRectF(body.right() - 92, body.bottom() - 30, 82, 22)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), int(220 * amt)))
            p.drawRoundedRect(chip, 4, 4)
            p.setFont(ui_font(8, bold=True))
            p.setPen(QColor(255, 255, 255, int(255 * amt)))
            p.drawText(chip, Qt.AlignCenter, "INSTALL")

    def _paint_tags(self, p: QPainter, hit: dict, x: int, y: int, max_w: int) -> None:
        cats = [c for c in hit.get("categories", []) if c not in ("fabric", "forge",
                "neoforge", "quilt")][:4]
        p.setFont(ui_font(7, bold=True))
        fm = p.fontMetrics()
        cx = x
        for c in cats:
            label = c.replace("-", " ").title()
            w = fm.horizontalAdvance(label) + 16
            if cx + w - x > max_w:
                break
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 24))
            p.drawRoundedRect(QRectF(cx, y, w, 17), 8, 8)
            p.setPen(TEXT_DIM)
            p.drawText(QRect(cx, y, w, 17), Qt.AlignCenter, label)
            cx += w + 6


class ModpackBrowsePage(Page):
    """Trang duyệt & cài modpack, bố cục kiểu Modrinth."""

    heading = ""

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self._selected_cats: set[str] = set()
        self._sort = "relevance"
        self._count = 0
        self._cat_rects: list[tuple[QRect, str]] = []
        self._icon_wanted: set = set()

        self.back_btn = AeroButton("‹  BACK", self, height=30, tone="neutral")
        self.back_btn.clicked.connect(lambda: self.ctl.go("installations"))

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search modpacks…")
        self.search.setStyleSheet(INPUT_QSS)
        self.search.setFont(ui_font(10))
        self.search.returnPressed.connect(self._load)

        self.sort_btn = AeroButton("Sort: Relevance", self, height=30, tone="neutral")
        self.sort_btn.clicked.connect(self._open_sort)

        self.version = QLineEdit(self)
        self.version.setPlaceholderText("e.g. 1.20.1")
        self.version.setStyleSheet(INPUT_QSS)
        self.version.setFont(ui_font(9))
        self.version.returnPressed.connect(self._load)

        self.cards = ModpackCards(self)
        self.cards.activated.connect(self._install)

    # ---------- vòng đời ----------

    def refresh(self) -> None:
        if not self.cards.hits:
            self._load()

    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        self.back_btn.setGeometry(24, 52, 92, 30)
        content_x = 24 + SIDEBAR_W + 20
        content_w = w - content_x - 24
        self.search.setGeometry(content_x, PANEL_TOP, content_w - 200, 32)
        self.sort_btn.setGeometry(content_x + content_w - 190, PANEL_TOP, 190, 32)
        self._place_filters()
        self.cards.setGeometry(content_x, PANEL_TOP + 42, content_w,
                               h - (PANEL_TOP + 42) - 16)

    def _place_filters(self) -> None:
        # ô nhập game version nằm dưới tiêu đề "GAME VERSION" ở cột trái
        gv_y = CAT_TOP + len(CATEGORIES) * 30 + 30
        self.version.setGeometry(38, gv_y, SIDEBAR_W - 28, 30)

    # ---------- tải dữ liệu ----------

    def _load(self) -> None:
        q = self.search.text().strip()
        gv = self.version.text().strip()
        cats = sorted(self._selected_cats)
        self.cards.empty_text = "Loading from Modrinth…"
        self.cards.set_hits([])
        self.ctl._run(
            lambda: modrinth.search(
                q, "modpack",
                loaders=cats or None,
                game_versions=[gv] if gv else None,
                index=self._sort, limit=40),
            self._show,
            lambda m: self._fail(m))

    def _fail(self, msg: str) -> None:
        self.cards.empty_text = f"Couldn't reach Modrinth: {msg}"
        self.cards.set_hits([])
        self.update()

    def _show(self, hits) -> None:
        self.cards.empty_text = "No modpacks matched these filters."
        self.cards.set_hits(hits)
        self._count = len(hits)
        self.update()
        for hgt in hits:
            url = hgt.get("icon_url")
            if url and url not in self.cards.icons and url not in self._icon_wanted:
                self._icon_wanted.add(url)
                self.ctl._run(lambda u=url: modrinth.fetch_icon(u),
                              lambda data, u=url: self._icon(u, data),
                              lambda _m, u=url: self._icon_wanted.discard(u))

    def _icon(self, url, data) -> None:
        self._icon_wanted.discard(url)
        pm = QPixmap()
        if pm.loadFromData(data):
            self.cards.icons[url] = pm
            self.cards.update()

    def _install(self, hit) -> None:
        self.ctl.install_modpack(hit)
        self.ctl.go("installations")

    # ---------- sort + lọc ----------

    def _open_sort(self) -> None:
        items = [MenuItem(kind="header", label="Sort by")]
        for label, key in SORTS:
            items.append(MenuItem(label=label, checked=key == self._sort, data=key))
        g = self.sort_btn.geometry()
        origin = self.sort_btn.mapTo(self.window(), g.topLeft())
        popup(self.window(), items, QRect(origin, g.size()), self._pick_sort, width=190)

    def _pick_sort(self, key) -> None:
        if not key:
            return
        self._sort = key
        label = next(lbl for lbl, k in SORTS if k == key)
        self.sort_btn.setText(f"Sort: {label}")
        self._load()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        for rect, slug in self._cat_rects:
            if rect.contains(pos):
                if slug in self._selected_cats:
                    self._selected_cats.discard(slug)
                else:
                    self._selected_cats.add(slug)
                self.update()
                self._load()
                return

    # ---------- vẽ ----------

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # tiêu đề trang + số kết quả
        p.setFont(ui_font(13, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(128, 52, 300, 28), Qt.AlignLeft | Qt.AlignVCenter, "Modpacks")
        if self._count:
            p.setFont(ui_font(9))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(230, 54, 300, 24), Qt.AlignLeft | Qt.AlignVCenter,
                       f"{self._count} results")

        # nền cột lọc
        panel = QRectF(24, PANEL_TOP, SIDEBAR_W, self.height() - PANEL_TOP - 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(panel, 8, 8)
        p.setBrush(gloss_gradient(80, 0.4))
        p.drawRoundedRect(panel, 8, 8)

        self._cat_rects = []
        p.setFont(ui_font(8, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(38, PANEL_TOP + 16, SIDEBAR_W - 20, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, "CATEGORY")
        y = CAT_TOP
        for label, slug in CATEGORIES:
            row = QRect(34, y, SIDEBAR_W - 20, 28)
            on = slug in self._selected_cats
            if on:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 60))
                p.drawRoundedRect(QRectF(row.adjusted(0, 1, 0, -1)), 5, 5)
            # ô tick
            box = QRect(row.left() + 6, row.center().y() - 7, 14, 14)
            p.setPen(QPen(QColor(255, 255, 255, 120), 1.2))
            p.setBrush(ACCENT if on else Qt.NoBrush)
            p.drawRoundedRect(QRectF(box), 3, 3)
            if on:
                p.setPen(QPen(QColor(255, 255, 255), 1.6))
                c = box.center()
                p.drawLine(c.x() - 3, c.y(), c.x() - 1, c.y() + 3)
                p.drawLine(c.x() - 1, c.y() + 3, c.x() + 3, c.y() - 3)
            p.setFont(ui_font(9, bold=on))
            p.setPen(TEXT if on else TEXT_DIM)
            p.drawText(QRect(box.right() + 10, row.top(), row.width() - 40, row.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, label)
            self._cat_rects.append((row, slug))
            y += 30

        p.setFont(ui_font(8, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(38, y + 12, SIDEBAR_W - 20, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, "GAME VERSION")
        p.end()
