"""Cửa sổ chính — bố cục dashboard kiểu Blockcraft, chất liệu Aero Glass.

Khung: sidebar trái (logo + nav) · vùng nội dung · status bar dưới.
Trang Home tự dựng cột giữa + cột phải bên trong nó (xem dashboard.py).
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPoint, QRect, QRectF, Qt, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QAbstractButton, QWidget

from ..i18n import tr
from ..paths import APP_NAME
from .glass import GlassPanel, draw_glass_rect
from .hero import render_hero
from .theme import ACCENT, CONNECTED, TEXT, TEXT_DIM, TEXT_FAINT, blur_pixmap, ui_font
from .widgets import SidebarItem, draw_cube_icon

SIDEBAR_W = 224
STATUSBAR_H = 26
CORNER = 8
LOGO_H = 88

OVERLAY_CLASSES = ("GlassMenu", "TextPrompt", "ConfirmDialog", "LoginDialog", "ReportDialog")

# (route, nhãn, icon, helper). Helper = tooltip giải thích bằng lời thường —
# người mới rê chuột là hiểu ngay, không cần biết thuật ngữ trước.
# (route, nhãn, icon, helper). Helper = tooltip giải thích bằng lời thường —
# người mới rê chuột là hiểu ngay, không cần biết thuật ngữ trước.
#
# Mods / Resource Packs / Shaders có mặt Ở CẢ HAI nơi: mục top-level ở sidebar
# (duyệt & cài nhanh cho game đang chọn) VÀ trong tab của từng instance (quản lý
# nội dung của riêng game đó). Hai lối bổ trợ nhau, không loại nhau.
NAV = [
    ("home", "Home", "home", "Your dashboard — jump straight back into a game."),
    ("installations", "Games", "cube",
     "Your separate Minecraft setups. Each has its own version, mods and worlds."),
    ("mods", "Mods", "mods", "Add-ons that change or add features to the game."),
    ("resourcepacks", "Resource Packs", "packs",
     "Texture & sound packs that change how the game looks and sounds."),
    ("shaders", "Shaders", "shaders",
     "Fancy lighting and visual effects for a better-looking game."),
    ("skins", "Skin", "skin", "Change how your character looks in the game."),
    ("panorama", "Panorama", "packs",
     "Pick the animated background shown behind the in-game menu."),
    ("settings", "Settings", "gear", "Memory, folders, language and updates."),
    ("discord", "Discord", "discord", "Open our community Discord in your browser."),
]

DISCORD_INVITE = "https://discord.gg/DS6djZ6aN9"


class TitleDragBar(QWidget):
    """Dải trong suốt phủ hết mép trên để kéo cửa sổ — đáng tin hơn việc dựa vào
    truyền sự kiện qua các widget con. Nút caption được nâng lên trên dải này."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._from = None

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == Qt.LeftButton:
            self._from = e.globalPosition().toPoint() - self.win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._from is not None and e.buttons() & Qt.LeftButton:
            self.win.move(e.globalPosition().toPoint() - self._from)

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._from = None

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        if self.win.isMaximized():
            self.win.showNormal()
        else:
            self.win.showMaximized()


class CaptionButton(QAbstractButton):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(30, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
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
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        h = self._hover_amt
        if self.kind == "close":
            base = QColor(214, 96, 96, int(70 + (150 - 70) * h))
        else:
            base = QColor(255, 255, 255, int(26 + (60 - 26) * h))
        draw_glass_rect(p, r, radius=3, tint=base, gloss=1.0)
        glyph = TEXT if self.kind != "close" else QColor(
            int(TEXT.red() + (255 - TEXT.red()) * h),
            int(TEXT.green() + (255 - TEXT.green()) * h),
            int(TEXT.blue() + (255 - TEXT.blue()) * h))
        p.setPen(QPen(glyph, 1.3))
        c = r.center()
        if self.kind == "close":
            p.drawLine(c.x() - 4, c.y() - 4, c.x() + 4, c.y() + 4)
            p.drawLine(c.x() + 4, c.y() - 4, c.x() - 4, c.y() + 4)
        elif self.kind == "max":
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(c.x() - 4, c.y() - 4, 8, 8))
        else:
            p.drawLine(c.x() - 5, c.y() + 4, c.x() + 5, c.y() + 4)
        p.end()


_LOGO = None


def logo_pixmap():
    """Logo lá (assets/logo.png), nạp một lần. None nếu thiếu file."""
    global _LOGO
    if _LOGO is None:
        from pathlib import Path

        from PySide6.QtGui import QPixmap
        _LOGO = QPixmap(str(Path(__file__).parent / "assets" / "logo.png"))
    return _LOGO


class SidebarPanel(GlassPanel):
    """Sidebar: logo trên, nav phía dưới."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w = self.width()

        logo = logo_pixmap()
        if logo is not None and not logo.isNull():
            p.drawPixmap(QRectF(12, 18, 46, 46), logo, QRectF(logo.rect()))
        else:
            draw_cube_icon(p, QRectF(16, 22, 40, 40),
                           QColor(126, 190, 92), QColor(150, 112, 78))
        f = ui_font(13, bold=True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        p.setFont(f)
        p.setPen(TEXT)
        p.drawText(QRect(64, 26, w - 70, 20), Qt.AlignLeft | Qt.AlignVCenter, "NOSTALGIA")
        f2 = ui_font(8, bold=True)
        f2.setLetterSpacing(QFont.AbsoluteSpacing, 3.0)
        p.setFont(f2)
        p.setPen(ACCENT)
        p.drawText(QRect(64, 46, w - 70, 16), Qt.AlignLeft | Qt.AlignVCenter, "LAUNCHER")

        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawLine(14, LOGO_H, w - 14, LOGO_H)
        p.end()


class StatusBar(GlassPanel):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        win = self.window()
        p.setPen(Qt.NoPen)
        p.setBrush(CONNECTED)
        p.drawEllipse(QRectF(14, self.height() / 2 - 4, 8, 8))
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(30, 0, 500, self.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   win.status_left)
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(self.width() - 320, 0, 300, self.height()),
                   Qt.AlignRight | Qt.AlignVCenter, win.status_right)

        # Thanh tiến độ download (mảnh, chạy dọc mép trên của status bar).
        if win.progress is not None:
            frac = max(0.0, min(1.0, float(win.progress)))
            p.setBrush(QColor(255, 255, 255, 26))
            p.drawRect(QRectF(0, 0, self.width(), 3))
            p.setBrush(ACCENT)
            p.drawRect(QRectF(0, 0, self.width() * frac, 3))
        p.end()


class LauncherWindow(QWidget):
    closing = Signal()
    nav_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        _logo = logo_pixmap()
        if _logo is not None and not _logo.isNull():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(_logo))
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1180, 720)
        self.setMinimumSize(1040, 660)

        self.hero = None
        self.blurred = None
        self.background_path = ""
        self._drag_from: QPoint | None = None
        self._centered = False

        self.account_label = "—"
        self.account_mode = "Not signed in"
        self.account_state = "off"
        self.status_left = "Ready"
        self.status_right = ""
        self.progress = None      # None = ẩn; 0..1 = tiến độ thanh download

        self.pages: dict[str, QWidget] = {}
        self.current_page: QWidget | None = None
        self._build()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._centered:
            self._centered = True
            s = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
            if s:
                fr = self.frameGeometry()
                fr.moveCenter(s.availableGeometry().center())
                self.move(fr.topLeft())

    def _build(self) -> None:
        self.sidebar = SidebarPanel(self, strong=True, edges="r", gloss=1.0, gloss_axis="h")
        self.statusbar = StatusBar(self, strong=True, edges="t", gloss=0.6)

        self.nav: dict[str, SidebarItem] = {}
        for key, label, icon, help in NAV:
            item = SidebarItem(tr(label), icon, self.sidebar)
            item._i18n_key = label
            item._i18n_help = help
            item.setToolTip(tr(help))
            item.clicked.connect(lambda _=False, k=key: self.nav_clicked.emit(k))
            self.nav[key] = item
        self.nav["home"].setChecked(True)

        self.dragbar = TitleDragBar(self)

        self.btn_min = CaptionButton("min", self)
        self.btn_max = CaptionButton("max", self)
        self.btn_close = CaptionButton("close", self)
        self.btn_close.clicked.connect(self.close)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(
            lambda: self.showNormal() if self.isMaximized() else self.showMaximized())

    def retranslate(self) -> None:
        """Đổi ngôn ngữ: cập nhật chữ trên nav + nút, rồi vẽ lại toàn bộ."""
        for item in self.nav.values():
            key = getattr(item, "_i18n_key", None)
            if key:
                item.setText(tr(key))
            help = getattr(item, "_i18n_help", None)
            if help:
                item.setToolTip(tr(help))
            item.update()
        for page in getattr(self, "pages", {}).values():
            if hasattr(page, "retranslate"):
                page.retranslate()
            page.update()
        self.update()

    def rebuild_hero(self) -> None:
        """Dựng lại ảnh nền + bản blur (gọi khi đổi background_path)."""
        w, h = max(1, self.width()), max(1, self.height())
        self.hero = render_hero(w, h, self.background_path)
        self.blurred = blur_pixmap(self.hero, factor=15, passes=3)
        self.update()
        self.update_all()

    # ---------- pages ----------

    def register_pages(self, pages: dict[str, QWidget]) -> None:
        self.pages = pages
        for pg in pages.values():
            pg.setParent(self)
            pg.hide()

    def show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        if self.current_page is not None and self.current_page is not page:
            self.current_page.hide()
        self.current_page = page
        for k, item in self.nav.items():
            item.setChecked(k == key)
        self._layout_page()
        page.show()
        page.refresh()
        page.lower()
        self.sidebar.raise_()
        self.statusbar.raise_()
        self.dragbar.raise_()          # thanh kéo nằm trên trang
        self.btn_min.raise_()          # nút caption nằm trên thanh kéo
        self.btn_max.raise_()
        self.btn_close.raise_()

    def _layout_page(self) -> None:
        if self.current_page is None:
            return
        self.current_page.setGeometry(
            SIDEBAR_W, 0, self.width() - SIDEBAR_W, self.height() - STATUSBAR_H
        )

    # ---------- API cho Controller ----------

    def set_account(self, label: str, mode: str, state: str = "ok") -> None:
        self.account_label, self.account_mode, self.account_state = label, mode, state
        self.update_all()

    def set_status(self, text: str) -> None:
        self.status_left = text
        self.statusbar.update()

    def set_java(self, text: str) -> None:
        self.status_right = text
        self.statusbar.update()

    def set_progress(self, frac) -> None:
        """frac 0..1 để hiện thanh tiến độ; None để ẩn."""
        self.progress = frac
        self.statusbar.update()

    def update_all(self) -> None:
        self.sidebar.update()
        self.statusbar.update()
        if self.current_page is not None:
            self.current_page.update()

    # ---------- layout ----------

    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        self.hero = render_hero(w, h, self.background_path)
        self.blurred = blur_pixmap(self.hero, factor=15, passes=3)

        self.sidebar.setGeometry(0, 0, SIDEBAR_W, h - STATUSBAR_H)
        self.statusbar.setGeometry(0, h - STATUSBAR_H, w, STATUSBAR_H)

        y = LOGO_H + 14
        for item in self.nav.values():
            item.setGeometry(0, y, SIDEBAR_W, 46)
            y += 50

        # Thanh kéo phủ mép trên, chừa phần sidebar-logo (đã kéo được sẵn) không sao.
        self.dragbar.setGeometry(0, 0, w, 46)
        self.dragbar.raise_()

        self.btn_close.move(w - 38, 8)
        self.btn_max.move(w - 72, 8)
        self.btn_min.move(w - 106, 8)
        self.btn_min.raise_()
        self.btn_max.raise_()
        self.btn_close.raise_()

        self._layout_page()
        for child in self.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if type(child).__name__ in OVERLAY_CLASSES:
                child.setGeometry(self.rect())
        super().resizeEvent(event)

    # ---------- kéo cửa sổ ----------

    def mousePressEvent(self, e):  # noqa: N802
        # Kéo cửa sổ từ dải trên cùng (kể cả khi cú bấm được trang con truyền lên).
        if e.button() == Qt.LeftButton and e.position().y() < 54:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._drag_from is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._drag_from = None

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closing.emit()
        super().closeEvent(event)

    # ---------- nền ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), CORNER, CORNER)
        p.setClipPath(path)
        if self.hero:
            p.drawPixmap(self.rect(), self.hero)

        r = QRectF(self.rect())
        for i, a in enumerate((20, 12, 6)):
            p.setPen(QPen(QColor(150, 200, 255, a), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(1.5 + i, 1.5 + i, -1.5 - i, -1.5 - i), CORNER, CORNER)
        p.setPen(QPen(QColor(255, 255, 255, 150), 1))
        p.drawLine(int(r.left() + CORNER), int(r.top() + 1),
                   int(r.right() - CORNER), int(r.top() + 1))

        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 82), 1))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), CORNER, CORNER)
        p.end()
