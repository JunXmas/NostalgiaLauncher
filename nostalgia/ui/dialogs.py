"""Hộp thoại dạng lớp phủ trong cửa sổ: đăng nhập, nhập tên, xác nhận."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QGuiApplication, QPainter, QPen, QPixmap, QTextCursor,
)
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

from .. import modrinth
from .controls import AeroSlider, AeroToggle, ListView, Row
from .theme import ACCENT, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font
from .widgets import AeroButton

INPUT_QSS = """
QLineEdit {
    background: rgba(255,255,255,26);
    border: 1px solid rgba(255,255,255,70);
    border-radius: 3px;
    padding: 6px 9px;
    color: #eef4fa;
    selection-background-color: rgba(108,196,128,150);
}
QLineEdit:focus { border: 1px solid rgba(140,220,165,170); }
"""


class GlassDialog(QWidget):
    """Nền mờ phủ kín cửa sổ + một thẻ kính ở giữa."""

    closed = Signal()

    def __init__(self, parent: QWidget, title: str, *, width: int = 460, height: int = 240):
        super().__init__(parent)
        self.title = title
        self.card_size = (width, height)
        self.setGeometry(parent.rect())
        self.setFocusPolicy(Qt.StrongFocus)
        self.raise_()

    @property
    def card(self) -> QRect:
        w, h = self.card_size
        return QRect((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def place(self) -> None:
        """Con lớp gọi sau khi tạo widget con, để đặt chúng theo khung thẻ."""

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.place()

    def mousePressEvent(self, e):  # noqa: N802
        if not self.card.contains(e.position().toPoint()):
            self.dismiss()

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key_Escape:
            self.dismiss()

    def dismiss(self) -> None:
        self.closed.emit()
        self.hide()
        self.deleteLater()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 96))

        card = QRectF(self.card)
        backdrop = getattr(self.window(), "blurred", None)
        p.save()
        p.setClipRect(card)
        if backdrop and not backdrop.isNull():
            p.drawPixmap(self.card, backdrop, self.card)
        p.fillRect(card, QColor(18, 28, 44, 224))
        p.fillRect(card, gloss_gradient(96, 0.95))
        p.restore()

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 104), 1))
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)

        p.setFont(ui_font(11, bold=True))
        p.setPen(TEXT)
        p.drawText(QRect(self.card.left() + 22, self.card.top() + 18,
                         self.card.width() - 44, 24), Qt.AlignLeft | Qt.AlignVCenter, self.title)
        self.paint_body(p)
        p.end()

    def paint_body(self, p: QPainter) -> None:
        """Con lớp vẽ nội dung thân thẻ."""


# ---------- nhập một dòng ----------

class TextPrompt(GlassDialog):
    accepted = Signal(str)

    def __init__(self, parent, title: str, prompt: str, *, placeholder: str = "",
                 hint: str = "", ok_text: str = "ADD"):
        super().__init__(parent, title, width=440, height=232)
        self.prompt = prompt
        self.hint = hint
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setStyleSheet(INPUT_QSS)
        self.edit.setFont(ui_font(10))
        self.edit.returnPressed.connect(self._accept)
        self.ok = AeroButton(ok_text, self, height=34)
        self.ok.clicked.connect(self._accept)
        self.cancel = AeroButton("CANCEL", self, height=34, tone="neutral")
        self.cancel.clicked.connect(self.dismiss)
        self.place()
        self.edit.setFocus()

    def place(self) -> None:
        c = self.card
        self.edit.setGeometry(c.left() + 22, c.top() + 78, c.width() - 44, 34)
        self.ok.setGeometry(c.right() - 132, c.bottom() - 52, 110, 34)
        self.cancel.setGeometry(c.right() - 250, c.bottom() - 52, 108, 34)

    def _accept(self) -> None:
        text = self.edit.text().strip()
        if text:
            self.accepted.emit(text)
            self.dismiss()

    def paint_body(self, p: QPainter) -> None:
        c = self.card
        p.setFont(ui_font(9))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(c.left() + 22, c.top() + 50, c.width() - 44, 20),
                   Qt.AlignLeft | Qt.AlignVCenter, self.prompt)
        if self.hint:
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(c.left() + 22, c.top() + 120, c.width() - 44, 40),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.hint)


# ---------- xác nhận ----------

class ConfirmDialog(GlassDialog):
    confirmed = Signal()

    def __init__(self, parent, title: str, message: str, *, ok_text: str = "DELETE",
                 tone: str = "danger"):
        super().__init__(parent, title, width=440, height=206)
        self.message = message
        self.ok = AeroButton(ok_text, self, height=34, tone=tone)
        self.ok.clicked.connect(self._go)
        self.cancel = AeroButton("CANCEL", self, height=34, tone="neutral")
        self.cancel.clicked.connect(self.dismiss)
        self.place()

    def place(self) -> None:
        c = self.card
        self.ok.setGeometry(c.right() - 132, c.bottom() - 52, 110, 34)
        self.cancel.setGeometry(c.right() - 250, c.bottom() - 52, 108, 34)

    def _go(self) -> None:
        self.confirmed.emit()
        self.dismiss()

    def paint_body(self, p: QPainter) -> None:
        c = self.card
        p.setFont(ui_font(9))
        p.setPen(TEXT_DIM)
        p.drawText(QRect(c.left() + 22, c.top() + 54, c.width() - 44, 66),
                   Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.message)


# ---------- chọn loader ----------

class LoaderDialog(GlassDialog):
    """Chọn loader trong một thẻ gọn ở giữa: mỗi loader là một hàng bấm được."""

    picked = Signal(str)  # phát ra khoá loader: vanilla/fabric/forge/neoforge

    ROWS = [
        ("Optimized", "optimized",
         "Fabulously Optimized preinstalled — best FPS, zero setup", QColor(120, 200, 120)),
        ("Vanilla", "vanilla", "Plain Minecraft, no mods", QColor(120, 170, 90)),
        ("Fabric", "fabric", "Light and fast — most modern mods", QColor(150, 128, 104)),
        ("Forge", "forge", "The classic loader for big mods", QColor(90, 150, 210)),
        ("NeoForge", "neoforge", "A modern fork of Forge", QColor(170, 120, 190)),
    ]
    ROW_STEP = 58
    TOP = 54

    def __init__(self, parent):
        h = self.TOP + self.ROW_STEP * len(self.ROWS) + 16
        super().__init__(parent, "Choose a loader", width=430, height=h)
        self._hover = -1
        self.setMouseTracking(True)
        self.place()

    def _row_rects(self) -> list[QRect]:
        c = self.card
        out, y = [], c.top() + self.TOP
        for _ in self.ROWS:
            out.append(QRect(c.left() + 16, y, c.width() - 32, self.ROW_STEP - 8))
            y += self.ROW_STEP
        return out

    def _index_at(self, pos) -> int:
        for i, r in enumerate(self._row_rects()):
            if r.contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):  # noqa: N802
        i = self._index_at(e.position().toPoint())
        if i != self._hover:
            self._hover = i
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        i = self._index_at(e.position().toPoint())
        if i >= 0:
            self.picked.emit(self.ROWS[i][1])
            self.dismiss()
            return
        super().mousePressEvent(e)  # bấm ngoài thẻ -> đóng

    def paint_body(self, p: QPainter) -> None:
        for i, r in enumerate(self._row_rects()):
            name, _key, sub, col = self.ROWS[i]
            hovered = i == self._hover
            if hovered:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 30))
                p.drawRoundedRect(QRectF(r), 6, 6)
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(ACCENT.lighter(130), 1.4))
                p.drawRoundedRect(QRectF(r).adjusted(0.7, 0.7, -0.7, -0.7), 6, 6)
            # ô màu nhận diện loader
            sw = QRect(r.left() + 10, r.center().y() - 17, 34, 34)
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(sw), 7, 7)
            p.setBrush(gloss_gradient(sw.height(), 0.5))
            p.drawRoundedRect(QRectF(sw), 7, 7)
            p.setFont(ui_font(13, bold=True))
            p.setPen(QColor(255, 255, 255, 235))
            p.drawText(sw, Qt.AlignCenter, name[0])
            # tên + mô tả ngắn
            tx = r.left() + 56
            p.setFont(ui_font(11, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(tx, r.top() + 7, r.width() - 92, 18),
                       Qt.AlignLeft | Qt.AlignVCenter, name)
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(tx, r.top() + 26, r.width() - 92, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, sub)
            # mũi tên ›
            p.setPen(QPen(TEXT_DIM if hovered else TEXT_FAINT, 2))
            cx, cy = r.right() - 18, r.center().y()
            p.drawLine(cx - 4, cy - 6, cx + 2, cy)
            p.drawLine(cx + 2, cy, cx - 4, cy + 6)


# ---------- đăng nhập Microsoft ----------

class LoginDialog(GlassDialog):
    """Hiện mã device code, tự sao chép, và chờ người dùng xác nhận trên web."""

    def __init__(self, parent):
        super().__init__(parent, "Sign in with Microsoft", width=500, height=272)
        self.code = ""
        self.url = ""
        self.message = "Requesting a code from Microsoft…"
        self.state = "waiting"  # waiting | ready | error | done
        self.copy_btn = AeroButton("COPY CODE", self, height=32, tone="neutral")
        self.copy_btn.clicked.connect(self._copy)
        self.copy_btn.setVisible(False)
        self.close_btn = AeroButton("CLOSE", self, height=32, tone="neutral")
        self.close_btn.clicked.connect(self.dismiss)
        self.place()

    def place(self) -> None:
        c = self.card
        self.copy_btn.setGeometry(c.left() + 22, c.bottom() - 50, 150, 32)
        self.close_btn.setGeometry(c.right() - 122, c.bottom() - 50, 100, 32)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.code)
        self.message = "Code copied. Paste it on the page that opened, then confirm."
        self.update()

    def show_code(self, url: str, code: str) -> None:
        self.url, self.code, self.state = url, code, "ready"
        self.message = "Open the page below, enter the code, then come back here."
        self.copy_btn.setVisible(True)
        self.update()

    def show_result(self, ok: bool, text: str) -> None:
        self.state = "done" if ok else "error"
        self.message = text
        self.copy_btn.setVisible(False)
        # Chữ lỗi thường dài 3-4 dòng: nới thẻ ra thay vì để nó bị cắt cụt.
        lines = text.count("\n") + 1 + len(text) // 58
        self.card_size = (500, max(196, 118 + lines * 19))
        self.place()
        self.update()

    def paint_body(self, p: QPainter) -> None:
        c = self.card
        # Ở trạng thái lỗi, thông báo được vẽ ở khối bên dưới với xuống dòng —
        # vẽ thêm ở đây nữa thì thành hai lớp chữ chồng nhau.
        if self.state != "error":
            p.setFont(ui_font(9))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(c.left() + 22, c.top() + 50, c.width() - 44, 20),
                       Qt.AlignLeft | Qt.AlignVCenter, self.message)

        if self.state == "ready":
            box = QRectF(c.left() + 22, c.top() + 82, c.width() - 44, 62)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 22))
            p.drawRoundedRect(box, 4, 4)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 60), 1))
            p.drawRoundedRect(box, 4, 4)

            f = ui_font(17, bold=True)
            # Phải là QFont.AbsoluteSpacing chứ không phải f.AbsoluteSpacing:
            # PySide6 chỉ gắn hằng số enum lên class, không lên đối tượng. Viết
            # qua đối tượng thì AttributeError nổ ngay giữa paintEvent — và vì
            # nổ trước p.end(), painter bị bỏ treo, kéo theo hàng nghìn cảnh báo
            # "paint device can only be painted by one painter at a time" ở mọi
            # lượt vẽ sau đó. Năm chỗ dùng letter spacing khác trong dự án đều
            # viết qua class, chỉ riêng đây lọt lưới.
            f.setLetterSpacing(QFont.AbsoluteSpacing, 5)
            p.setFont(f)
            p.setPen(ACCENT)
            p.drawText(box, Qt.AlignCenter, self.code)

            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(c.left() + 22, c.top() + 152, c.width() - 44, 18),
                       Qt.AlignLeft | Qt.AlignVCenter, self.url)
        elif self.state == "error":
            p.setFont(ui_font(9))
            p.setPen(DEGRADED)
            p.drawText(QRect(c.left() + 22, c.top() + 52, c.width() - 44,
                             c.height() - 118),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.message)


# ---------- báo cáo dài, có cuộn ----------

REPORT_QSS = """
QTextBrowser {
    background: rgba(0,0,0,60); border: 1px solid rgba(255,255,255,40);
    border-radius: 3px; color: #cbdbec; padding: 8px;
    selection-background-color: rgba(108,196,128,140);
}
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(255,255,255,58); border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


class ReportDialog(GlassDialog):
    """Thẻ kính lớn chứa một báo cáo văn bản dài."""

    def __init__(self, parent, title: str, body: str = "Running…"):
        super().__init__(parent, title, width=min(760, parent.width() - 80),
                         height=min(520, parent.height() - 90))
        self.view = QTextBrowser(self)
        self.view.setStyleSheet(REPORT_QSS)
        f = ui_font(9)
        f.setFamily("monospace")
        self.view.setFont(f)
        self.view.setPlainText(body)
        self.close_btn = AeroButton("CLOSE", self, height=32, tone="neutral")
        self.close_btn.clicked.connect(self.dismiss)
        self.place()

    def set_body(self, text: str) -> None:
        self.view.setPlainText(text)

    def append_line(self, line: str) -> None:
        self.view.moveCursor(QTextCursor.End)
        self.view.insertPlainText(line)
        self.view.moveCursor(QTextCursor.End)

    def place(self) -> None:
        c = self.card
        self.view.setGeometry(c.left() + 20, c.top() + 52, c.width() - 40, c.height() - 116)
        self.close_btn.setGeometry(c.right() - 122, c.bottom() - 48, 100, 32)


# ---------- duyệt & cài modpack Modrinth ----------

def _compact(n: int) -> str:
    for div, suf in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if n >= div:
            return f"{n / div:.1f}{suf}"
    return str(n)


class ModpackDialog(GlassDialog):
    """Tìm modpack trên Modrinth và cài thẳng thành một instance mới."""

    def __init__(self, parent, ctl):
        super().__init__(parent, "Add a modpack from Modrinth",
                         width=min(660, parent.width() - 60),
                         height=min(480, parent.height() - 80))
        self.ctl = ctl
        self._hits: list = []
        self._icons: dict = {}
        self._icon_wanted: set = set()

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search modpacks…")
        self.search.setStyleSheet(INPUT_QSS)
        self.search.setFont(ui_font(10))
        self.search.returnPressed.connect(self._load)
        self.search_btn = AeroButton("SEARCH", self, height=30)
        self.search_btn.clicked.connect(self._load)
        self.results = ListView(self, empty_text="Loading popular modpacks…")
        self.results.activated.connect(self._install)
        self.results.badge_clicked.connect(self._install)
        self.close_btn = AeroButton("CLOSE", self, height=30, tone="neutral")
        self.close_btn.clicked.connect(self.dismiss)
        self.place()
        self.search.setFocus()
        self._load()

    def place(self) -> None:
        c = self.card
        self.search.setGeometry(c.left() + 20, c.top() + 50, c.width() - 150, 30)
        self.search_btn.setGeometry(c.right() - 118, c.top() + 50, 98, 30)
        self.results.setGeometry(c.left() + 20, c.top() + 92, c.width() - 40, c.height() - 156)
        self.close_btn.setGeometry(c.right() - 118, c.bottom() - 46, 98, 30)

    def _load(self) -> None:
        q = self.search.text().strip()
        self.results.empty_text = "Loading from Modrinth…"
        self.results.set_rows([])
        self.ctl._run(
            lambda: modrinth.search(q, "modpack", index="downloads", limit=30),
            self._show, lambda m: self._fail(m))

    def _fail(self, msg: str) -> None:
        self.results.empty_text = f"Couldn't reach Modrinth: {msg}"
        self.results.set_rows([])

    def _show(self, hits) -> None:
        self._hits = hits
        self.results.empty_text = "No modpacks matched."
        self._render()
        for h in hits:
            url = h.get("icon_url")
            if url and url not in self._icons and url not in self._icon_wanted:
                self._icon_wanted.add(url)
                self.ctl._run(lambda u=url: modrinth.fetch_icon(u),
                              lambda data, u=url: self._icon(u, data),
                              lambda _m, u=url: self._icon_wanted.discard(u))

    def _icon(self, url, data) -> None:
        self._icon_wanted.discard(url)
        pm = QPixmap()
        if pm.loadFromData(data):
            self._icons[url] = pm
            self._render()

    def _render(self) -> None:
        rows = []
        for h in self._hits:
            rows.append(Row(
                title=h.get("title", "?"),
                subtitle=f"{h.get('author', '?')} · {_compact(h.get('downloads', 0))} downloads",
                badge="ADD", badge_on=True,
                icon=self._icons.get(h.get("icon_url") or ""),
                data=h))
        self.results.set_rows(rows)

    def _install(self, hit) -> None:
        self.ctl.install_modpack(hit)
        self.dismiss()


# ---------- chọn phiên bản Minecraft ----------

class VersionPickerDialog(GlassDialog):
    """Danh sách phiên bản có ô lọc, đánh dấu bản đã tải, tuỳ chọn snapshot."""

    picked = Signal(str)

    def __init__(self, parent, versions, *, installed=None,
                 title="Choose a Minecraft version", on_snapshots=None):
        super().__init__(parent, title, width=460, height=456)
        self._installed = set(installed or [])
        self._all: list = []

        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText("Type to filter — e.g. 1.20")
        self.filter.setStyleSheet(INPUT_QSS)
        self.filter.setFont(ui_font(10))
        self.filter.textChanged.connect(self._apply)

        self.snapshots = None
        if on_snapshots is not None:
            self.snapshots = AeroToggle(False, self)
            self.snapshots.toggled.connect(on_snapshots)

        self.list = ListView(self, empty_text="No matching versions.")
        self.list.activated.connect(self._choose)
        self.cancel = AeroButton("CANCEL", self, height=32, tone="neutral")
        self.cancel.clicked.connect(self.dismiss)

        self.set_versions(versions)
        self.place()
        self.filter.setFocus()

    def set_versions(self, versions) -> None:
        self._all = list(versions or [])
        self._apply()

    def _apply(self) -> None:
        q = self.filter.text().strip().lower()
        rows = [Row(title=v, right="✓ downloaded" if v in self._installed else "", data=v)
                for v in self._all if q in v.lower()]
        self.list.set_rows(rows)

    def _choose(self, v) -> None:
        if v:
            self.picked.emit(v)
            self.dismiss()

    def place(self) -> None:
        c = self.card
        self.filter.setGeometry(c.left() + 22, c.top() + 50, c.width() - 44, 32)
        top = c.top() + 94
        if self.snapshots:
            self.snapshots.setGeometry(c.left() + 22, c.top() + 94, 44, 22)
            top = c.top() + 126
        self.list.setGeometry(c.left() + 18, top, c.width() - 36, c.bottom() - top - 56)
        self.cancel.setGeometry(c.right() - 120, c.bottom() - 46, 98, 32)

    def paint_body(self, p: QPainter) -> None:
        if self.snapshots:
            p.setFont(ui_font(9))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(self.card.left() + 74, self.card.top() + 94, 300, 22),
                       Qt.AlignLeft | Qt.AlignVCenter, "Include snapshots")


# ---------- cấu hình riêng của một instance ----------

class InstanceSettingsDialog(GlassDialog):
    """Đổi tên instance và ghi đè RAM / đường dẫn Java cho riêng nó."""

    saved = Signal(str, int, str)   # tên mới, RAM (MB), java path
    duplicate = Signal()
    repair = Signal()
    set_icon = Signal()
    reset_icon = Signal()
    aero_toggled = Signal(bool)     # bật/tắt Aero UI cho instance này

    def __init__(self, parent, inst, *, default_memory: int, max_memory: int,
                 aero_on: bool = False):
        super().__init__(parent, f"Instance settings", width=480, height=392)
        self.old_name = inst.name
        self.name = QLineEdit(inst.name, self)
        self.name.setStyleSheet(INPUT_QSS)
        self.name.setFont(ui_font(10))
        self.mem = AeroSlider(1024, max_memory, inst.memory_mb or default_memory, 512, self)
        self.mem.changed.connect(lambda _v: self.update())
        self.java = QLineEdit(inst.java_path, self)
        self.java.setPlaceholderText("leave empty = auto / global default")
        self.java.setStyleSheet(INPUT_QSS)
        self.java.setFont(ui_font(9))
        self.ok = AeroButton("SAVE", self, height=32, tone="green")
        self.ok.clicked.connect(self._save)
        self.cancel = AeroButton("CANCEL", self, height=32, tone="neutral")
        self.cancel.clicked.connect(self.dismiss)
        self.dup = AeroButton("DUPLICATE", self, height=32, tone="neutral")
        self.dup.clicked.connect(lambda: (self.duplicate.emit(), self.dismiss()))
        self.rep = AeroButton("REPAIR", self, height=32, tone="neutral")
        self.rep.clicked.connect(lambda: (self.repair.emit(), self.dismiss()))
        self.icon_btn = AeroButton("SET ICON", self, height=30, tone="neutral")
        self.icon_btn.clicked.connect(self.set_icon.emit)
        self.icon_reset = AeroButton("RESET", self, height=30, tone="neutral")
        self.icon_reset.clicked.connect(self.reset_icon.emit)
        self.aero_on = aero_on
        self.aero_btn = AeroButton(self._aero_label(), self, height=30,
                                   tone="green" if aero_on else "neutral")
        self.aero_btn.clicked.connect(self._toggle_aero)
        self.place()

    def _aero_label(self) -> str:
        return "AERO UI: ON" if self.aero_on else "AERO UI: OFF"

    def _toggle_aero(self) -> None:
        self.aero_on = not self.aero_on
        self.aero_btn.setText(self._aero_label())
        self.aero_btn.tone = "green" if self.aero_on else "neutral"
        self.aero_btn.update()
        self.aero_toggled.emit(self.aero_on)

    def _save(self) -> None:
        self.saved.emit(self.name.text().strip() or self.old_name,
                        self.mem.value, self.java.text().strip())
        self.dismiss()

    def place(self) -> None:
        c = self.card
        self.name.setGeometry(c.left() + 22, c.top() + 76, c.width() - 44, 32)
        self.mem.setGeometry(c.left() + 22, c.top() + 150, c.width() - 44, 26)
        self.java.setGeometry(c.left() + 22, c.top() + 222, c.width() - 44, 32)
        self.icon_btn.setGeometry(c.left() + 22, c.top() + 292, 120, 30)
        self.icon_reset.setGeometry(c.left() + 150, c.top() + 292, 84, 30)
        self.aero_btn.setGeometry(c.left() + 244, c.top() + 292, 194, 30)
        self.dup.setGeometry(c.left() + 22, c.bottom() - 46, 108, 30)
        self.rep.setGeometry(c.left() + 138, c.bottom() - 46, 92, 30)
        self.ok.setGeometry(c.right() - 128, c.bottom() - 46, 106, 30)
        self.cancel.setGeometry(c.right() - 244, c.bottom() - 46, 104, 30)

    def paint_body(self, p: QPainter) -> None:
        c = self.card

        def label(y, text):
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(c.left() + 22, y, c.width() - 44, 18),
                       Qt.AlignLeft | Qt.AlignVCenter, text)

        label(c.top() + 52, "Name")
        label(c.top() + 122, f"Max memory — {self.mem.value / 1024:.1f} GB")
        label(c.top() + 198, "Java path (this instance)")
        label(c.top() + 270, "Icon (shown on the Home card)")
