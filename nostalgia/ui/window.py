"""Cửa sổ chính: bố cục theo launcher chính thức, chất liệu theo Aero Glass."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QAbstractButton, QWidget

from .glass import GlassPanel, draw_glass_rect
from ..paths import APP_NAME
from .hero import render_hero
from .theme import (
    CONNECTED, DEGRADED, DISCONNECTED, TEXT, TEXT_DIM, blur_pixmap, ui_font,
)
from .widgets import AeroButton, AeroProgress, SidebarItem, TabBar, draw_cube_icon

SIDEBAR_W = 200
TOPBAR_H = 74
BOTTOMBAR_H = 92
CORNER = 8

# Vùng bấm được, toạ độ tương đối trong tấm kính chứa nó.
ACCOUNT_HIT = QRect(8, 10, SIDEBAR_W - 16, 50)
PILL = QRect(18, 20, 252, 30)

OVERLAY_CLASSES = ("GlassMenu", "TextPrompt", "ConfirmDialog", "LoginDialog")


def _chevron(p: QPainter, cx: float, cy: float, color: QColor) -> None:
    p.setPen(QPen(color, 1.4))
    p.drawLine(QPoint(int(cx - 4), int(cy - 2)), QPoint(int(cx), int(cy + 2)))
    p.drawLine(QPoint(int(cx), int(cy + 2)), QPoint(int(cx + 4), int(cy - 2)))


class CaptionButton(QAbstractButton):
    """Nút thu nhỏ / đóng ở góc phải, kiểu nút caption của Vista."""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(34, 24)
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
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._hover:
            tint = QColor(224, 84, 84, 190) if self.kind == "close" else QColor(255, 255, 255, 46)
            draw_glass_rect(p, r, radius=2, tint=tint, gloss=1.0)
        p.setPen(QPen(TEXT, 1.3))
        c = r.center()
        if self.kind == "close":
            p.drawLine(c.x() - 4, c.y() - 4, c.x() + 4, c.y() + 4)
            p.drawLine(c.x() + 4, c.y() - 4, c.x() - 4, c.y() + 4)
        else:
            p.drawLine(c.x() - 5, c.y() + 4, c.x() + 5, c.y() + 4)
        p.end()


class HotZoneMixin:
    """Một vùng bấm được bên trong tấm kính: đổi con trỏ và sáng lên khi rê vào."""

    hit_rect = QRect()

    def _init_hot(self) -> None:
        self._hot = False
        self.setMouseTracking(True)

    def mouseMoveEvent(self, e):  # noqa: N802
        hot = self.hit_rect.contains(e.position().toPoint())
        if hot != self._hot:
            self._hot = hot
            self.setCursor(Qt.PointingHandCursor if hot else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, e):  # noqa: N802
        if self._hot:
            self._hot = False
            self.update()


# ---------- ba tấm kính, mỗi tấm tự vẽ chữ của mình ----------
# Widget con luôn vẽ đè lên paintEvent của cha, nên chữ phải nằm trong chính
# tấm kính chứ không phải trong cửa sổ.


class SidebarPanel(HotZoneMixin, GlassPanel):
    account_clicked = Signal()
    hit_rect = ACCOUNT_HIT

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._init_hot()

    def mousePressEvent(self, e):  # noqa: N802
        if self.hit_rect.contains(e.position().toPoint()):
            self.account_clicked.emit()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        win = self.window()

        if self._hot:
            draw_glass_rect(p, QRectF(self.hit_rect), radius=3,
                            tint=QColor(255, 255, 255, 24), gloss=0.6)

        p.setFont(ui_font(10, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(16, 16, self.width() - 46, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   win.account_label)
        _chevron(p, self.width() - 22, 26, TEXT_DIM)

        p.setPen(Qt.NoPen)
        p.setBrush({"ok": CONNECTED, "warn": DEGRADED}.get(win.account_state, DISCONNECTED))
        p.drawEllipse(QRectF(17, 42, 7, 7))
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(31, 37, self.width() - 42, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   win.account_mode)

        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawLine(12, 76, self.width() - 12, 76)
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        p.drawLine(12, 77, self.width() - 12, 77)
        p.end()


class TopBarPanel(GlassPanel):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f = ui_font(9, bold=True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.3)
        p.setFont(f)
        p.setPen(TEXT)
        # Không có tab thì tiêu đề đứng giữa thanh, khỏi treo lơ lửng ở trên.
        y = 13 if self.window().tabs.isVisible() else (self.height() - 18) // 2
        p.drawText(QRect(18, y, 520, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   self.window().section_title)
        p.end()


class BottomBarPanel(HotZoneMixin, GlassPanel):
    version_clicked = Signal()
    hit_rect = PILL

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._init_hot()

    def mousePressEvent(self, e):  # noqa: N802
        if self.hit_rect.contains(e.position().toPoint()):
            self.version_clicked.emit()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        win = self.window()

        draw_glass_rect(p, QRectF(PILL), radius=3,
                        tint=QColor(255, 255, 255, 46 if self._hot else 30), gloss=0.85)
        draw_cube_icon(p, QRectF(PILL.left() + 8, PILL.center().y() - 9, 18, 18),
                       QColor(126, 190, 92), QColor(150, 112, 78))
        p.setFont(ui_font(9))
        p.setPen(TEXT)
        p.drawText(QRect(PILL.left() + 34, PILL.top(), 196, 30),
                   Qt.AlignLeft | Qt.AlignVCenter, win.version_label)
        _chevron(p, PILL.right() - 14, PILL.center().y() - 1, TEXT_DIM)

        # Chú thích tiến trình: luôn kèm số file, không để người dùng đoán.
        # Lúc rảnh không có thanh tiến trình nên kéo dòng chữ lên sát ô phiên bản.
        y = self.height() - 44 if win.progress.isVisible() else 56
        p.setFont(ui_font(8))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(20, y, self.width() - 300, 14), Qt.AlignLeft | Qt.AlignVCenter,
                   win.status_text)

        p.setFont(ui_font(9))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(self.width() - 190, 20, 172, 30), Qt.AlignRight | Qt.AlignVCenter,
                   win.account_label)
        p.end()


class LauncherWindow(QWidget):
    closing = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1060, 660)
        self.setMinimumSize(940, 600)

        self.hero = None
        self.blurred = None
        self._drag_from: QPoint | None = None
        self._centered = False

        self.account_label = "—"
        self.account_mode = "Chưa đăng nhập"
        self.account_state = "off"
        self.version_label = "Chưa chọn phiên bản"
        self.status_text = "Sẵn sàng"
        self.section_title = "MINECRAFT: JAVA EDITION"

        self.pages: dict[str, QWidget] = {}
        self.current_page: QWidget | None = None
        self._build()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closing.emit()
        super().closeEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Canh giữa sau khi cửa sổ đã hiện: gọi trong __init__ thì window manager
        # còn đặt lại vị trí sau đó, kết quả lệch hẳn ra mép màn hình.
        if not self._centered:
            self._centered = True
            self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def _build(self) -> None:
        self.sidebar = SidebarPanel(self, strong=True, edges="r", gloss=1.0, gloss_axis="h")
        self.topbar = TopBarPanel(self, edges="b", gloss=1.0)
        self.bottombar = BottomBarPanel(self, strong=True, edges="t", gloss=0.95)

        self.tabs = TabBar(["Chơi", "Bản cài đặt", "Skin", "Ghi chú"], self.topbar)

        self.nav_news = SidebarItem("Tin tức", "news", self.sidebar)
        self.nav_game = SidebarItem("MINECRAFT", "cube", self.sidebar, subtitle="Java Edition")
        self.nav_settings = SidebarItem("Cài đặt", "gear", self.sidebar)
        self.nav_game.setChecked(True)

        self.play = AeroButton("CHƠI", self.bottombar, height=48)
        self.progress = AeroProgress(self.bottombar)
        self.progress.setVisible(False)

        self.btn_min = CaptionButton("min", self)
        self.btn_close = CaptionButton("close", self)
        self.btn_close.clicked.connect(self.close)
        self.btn_min.clicked.connect(self.showMinimized)

    # ---------- trang ----------

    def register_pages(self, pages: dict[str, QWidget]) -> None:
        self.pages = pages
        for page in pages.values():
            page.setParent(self)
            page.hide()

    def show_page(self, key: str, *, title: str, tabs_visible: bool,
                  bottom_visible: bool) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        if self.current_page is not None and self.current_page is not page:
            self.current_page.hide()
        self.current_page = page
        self.section_title = title
        self.tabs.setVisible(tabs_visible)
        self.bottombar.setVisible(bottom_visible)
        self._layout_page()
        page.show()
        page.refresh()
        # Trang nằm dưới các tấm kính, không được che chúng.
        page.lower()
        self.topbar.raise_()
        self.sidebar.raise_()
        self.bottombar.raise_()
        self.btn_min.raise_()
        self.btn_close.raise_()
        self.topbar.update()

    def _layout_page(self) -> None:
        if self.current_page is None:
            return
        bottom = BOTTOMBAR_H if self.bottombar.isVisible() else 0
        self.current_page.setGeometry(
            SIDEBAR_W, TOPBAR_H, self.width() - SIDEBAR_W, self.height() - TOPBAR_H - bottom
        )

    # ---------- API cho Controller ----------

    def set_account(self, label: str, mode: str, state: str = "ok") -> None:
        self.account_label, self.account_mode, self.account_state = label, mode, state
        self.sidebar.update()
        self.bottombar.update()

    def set_version(self, label: str) -> None:
        self.version_label = label
        self.bottombar.update()

    def set_status(self, text: str) -> None:
        self.status_text = text
        self.bottombar.update()

    def set_progress(self, fraction: float | None) -> None:
        """None = không có việc gì đang chạy, ẩn hẳn thanh thay vì để nó ở 0%."""
        self.progress.setVisible(fraction is not None)
        if fraction is not None:
            self.progress.set_progress(fraction)
        self.bottombar.update()

    # ---------- bố cục ----------

    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        self.hero = render_hero(w, h)
        self.blurred = blur_pixmap(self.hero, factor=14, passes=2)

        self.sidebar.setGeometry(0, 0, SIDEBAR_W, h)
        self.topbar.setGeometry(SIDEBAR_W, 0, w - SIDEBAR_W, TOPBAR_H)
        self.bottombar.setGeometry(SIDEBAR_W, h - BOTTOMBAR_H, w - SIDEBAR_W, BOTTOMBAR_H)

        self.tabs.setGeometry(16, TOPBAR_H - 34, 480, 30)

        self.nav_news.setGeometry(0, 96, SIDEBAR_W, 38)
        self.nav_game.setGeometry(0, 140, SIDEBAR_W, 50)
        self.nav_settings.setGeometry(0, h - 52, SIDEBAR_W, 38)

        bw = self.bottombar.width()
        self.play.setGeometry(int(bw / 2 - 120), 22, 240, 48)
        self.progress.setGeometry(20, BOTTOMBAR_H - 26, 252, 11)

        self.btn_close.move(w - 42, 9)
        self.btn_min.move(w - 78, 9)

        self._layout_page()
        # Menu và hộp thoại phủ kín cửa sổ nên phải co giãn theo.
        for child in self.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if type(child).__name__ in OVERLAY_CLASSES:
                child.setGeometry(self.rect())
        super().resizeEvent(event)

    # ---------- kéo cửa sổ ----------

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == Qt.LeftButton and e.position().y() < TOPBAR_H:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._drag_from is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e):  # noqa: N802
        self._drag_from = None

    # ---------- nền ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Bo góc cửa sổ: Aero bo khoảng 8px, phần ngoài để trong suốt.
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), CORNER, CORNER)
        p.setClipPath(path)
        if self.hero:
            p.drawPixmap(self.rect(), self.hero)

        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 78), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), CORNER, CORNER)
        p.end()
