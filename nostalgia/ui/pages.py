"""Các trang nội dung nằm giữa thanh trên và thanh dưới."""

from __future__ import annotations

import os

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

from ..settings import client_id as resolve_client_id, save_client_id
from .controls import AeroSlider, AeroToggle, ListView, Row
from .theme import ACCENT, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font
from .widgets import AeroButton

TEXT_QSS = """
QTextBrowser {
    background: transparent; border: none; color: #cbdbec;
    selection-background-color: rgba(108,196,128,140);
}
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(255,255,255,58); border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""

INPUT_QSS = """
QLineEdit {
    background: rgba(255,255,255,22); border: 1px solid rgba(255,255,255,62);
    border-radius: 3px; padding: 6px 9px; color: #eef4fa;
    selection-background-color: rgba(108,196,128,150);
}
QLineEdit:focus { border: 1px solid rgba(140,220,165,170); }
"""


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


class Page(QWidget):
    """Mặt kính cho nội dung. Trang Chơi tắt hẳn để ảnh hero hiện trọn."""

    scrim = True
    heading = ""

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl

    def refresh(self) -> None:
        """Gọi mỗi lần trang được hiện."""

    def paintEvent(self, event) -> None:
        if not self.scrim:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # Cùng công thức với GlassPanel: nền đã blur -> sắc kính -> vệt bóng.
        # Đặc hơn các tấm khác vì đây là chỗ đọc chữ dài.
        backdrop = getattr(self.window(), "blurred", None)
        if backdrop and not backdrop.isNull():
            origin = self.mapTo(self.window(), rect.topLeft())
            p.drawPixmap(rect, backdrop, QRect(origin, rect.size()))
        p.fillRect(rect, QColor(12, 21, 35, 226))
        p.fillRect(rect, gloss_gradient(96, 0.55))

        if self.heading:
            f = ui_font(12, bold=True)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
            p.setFont(f)
            p.setPen(TEXT)
            p.drawText(QRect(26, 18, self.width() - 52, 26),
                       Qt.AlignLeft | Qt.AlignVCenter, self.heading)
            p.setPen(QPen(QColor(255, 255, 255, 26), 1))
            p.drawLine(26, 48, self.width() - 26, 48)
        p.end()


class StubPage(Page):
    """Trang chưa có nội dung — Mods / Resource Packs / Servers."""

    def __init__(self, ctl, heading: str, note: str, parent=None):
        super().__init__(ctl, parent)
        self.heading = heading
        self._note = note

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setFont(ui_font(10))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(26, 70, self.width() - 52, 80),
                   Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self._note)
        p.end()


# ---------- bản cài đặt ----------

class InstallationsPage(Page):
    heading = "Installations"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="No versions downloaded yet. Click ADD VERSION.")
        self.list.activated.connect(self._select)
        self.list.action_clicked.connect(self.ctl.ask_delete_version)
        self.add_btn = AeroButton("ADD VERSION", self, height=32, tone="neutral")
        self.add_btn.clicked.connect(self.ctl.open_version_menu_for_install)
        self.fabric_btn = AeroButton("INSTALL FABRIC", self, height=32, tone="neutral")
        self.fabric_btn.clicked.connect(self.ctl.open_fabric_menu)

    def _select(self, version_id) -> None:
        self.ctl.set_version(version_id)
        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.list.setGeometry(16, 58, self.width() - 32, self.height() - 116)
        self.add_btn.setGeometry(self.width() - 196, self.height() - 46, 180, 32)
        self.fabric_btn.setGeometry(self.width() - 356, self.height() - 46, 150, 32)

    def refresh(self) -> None:
        current = self.ctl.settings.selected_version
        rows = []
        for v in self.ctl.installer.installed_versions():
            state = "ready" if v["complete"] else "metadata only"
            origin = f" · base {v['parent']}" if v.get("parent") else ""
            rows.append(Row(
                title=v["id"],
                subtitle=f"{v['type']}{origin} · Java {v['java']} · {state}",
                right=human_size(v["size"]),
                checked=v["id"] == current,
                action="delete",
                data=v["id"],
            ))
        self.list.set_rows(rows)


# ---------- skin ----------

class SkinsPage(Page):
    heading = "Skin"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.skin: QImage | None = None
        self.note = ""

    def refresh(self) -> None:
        account = self.ctl.current_account()
        self.skin, self.note = None, ""
        if account is None:
            self.note = "No accounts yet."
        elif account.kind != "msa" or not account.owns_game:
            self.note = ("Only Microsoft accounts that own the game have a server-side skin.\n"
                         "Offline profiles and demo accounts use the default Steve/Alex skin.")
        elif not account.skin_url:
            self.note = "This account has no cached skin — sign in again to fetch it."
        else:
            self.ctl.load_skin(account.skin_url, self._got)
            self.note = "Loading skin…"
        self.update()

    def _got(self, data: bytes | None) -> None:
        if data:
            img = QImage()
            if img.loadFromData(data):
                self.skin = img
                self.note = ""
        else:
            self.note = "Could not load skin."
        self.update()

    def _part(self, p: QPainter, sx: int, sy: int, sw: int, sh: int,
              dx: float, dy: float, scale: int) -> None:
        p.drawImage(QRectF(dx, dy, sw * scale, sh * scale), self.skin,
                    QRectF(sx, sy, sw, sh))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)

        if self.skin is not None and self.skin.width() >= 64:
            scale = 7
            ox, oy = 58, 96
            has_slim_arms = self.skin.height() >= 64
            # Ghép mặt trước: đầu, thân, hai tay, hai chân — toạ độ chuẩn của skin 64x64.
            self._part(p, 8, 8, 8, 8, ox + 4 * scale, oy, scale)                  # đầu
            self._part(p, 20, 20, 8, 12, ox + 4 * scale, oy + 8 * scale, scale)   # thân
            self._part(p, 44, 20, 4, 12, ox + 12 * scale, oy + 8 * scale, scale)  # tay phải
            if has_slim_arms:
                self._part(p, 36, 52, 4, 12, ox, oy + 8 * scale, scale)           # tay trái
                self._part(p, 20, 52, 4, 12, ox + 8 * scale, oy + 20 * scale, scale)
            else:
                self._part(p, 44, 20, 4, 12, ox, oy + 8 * scale, scale)
                self._part(p, 4, 20, 4, 12, ox + 8 * scale, oy + 20 * scale, scale)
            self._part(p, 4, 20, 4, 12, ox + 4 * scale, oy + 20 * scale, scale)   # chân phải
            self._part(p, 40, 8, 8, 8, ox + 4 * scale, oy, scale)                 # lớp mũ

            account = self.ctl.current_account()
            p.setFont(ui_font(13, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(ox + 150, oy + 6, 320, 24), Qt.AlignLeft | Qt.AlignVCenter,
                       account.username if account else "")
            p.setFont(ui_font(8))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(ox + 150, oy + 34, 420, 40),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                       "Change your skin at minecraft.net/msaprofile — the launcher only shows it,\n"
                       "uploading a new skin is not supported yet.")
        elif self.note:
            p.setFont(ui_font(10))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(26, 70, self.width() - 52, 120),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.note)
        p.end()


# ---------- ghi chú phiên bản ----------

class NotesPage(Page):
    heading = "Patch notes"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="Loading…")
        self.list.ROW_H = 44
        self.list.activated.connect(self._open)
        self.body = QTextBrowser(self)
        self.body.setStyleSheet(TEXT_QSS)
        self.body.setFont(ui_font(9))
        self.body.setOpenExternalLinks(True)
        self.body.setPlainText("Pick a version on the left to read its notes.")
        self._entries: list[dict] = []

    def resizeEvent(self, event) -> None:  # noqa: N802
        w = 344
        self.list.setGeometry(16, 58, w, self.height() - 74)
        self.body.setGeometry(w + 40, 58, self.width() - w - 66, self.height() - 74)

    def refresh(self) -> None:
        if self._entries:
            return
        self.ctl.load_patch_notes(self._got_list)

    def _got_list(self, entries: list[dict] | None) -> None:
        if not entries:
            self.list.empty_text = "Could not load patch notes (offline?)."
            self.list.set_rows([])
            return
        self._entries = entries
        self.list.set_rows([
            Row(title=e["title"], subtitle=f"{e['type']} · {e['version']}", data=e["path"])
            for e in entries
        ])

    def _open(self, path) -> None:
        self.body.setPlainText("Loading…")
        self.ctl.load_patch_body(path, self.body.setPlainText)


# ---------- tin tức ----------

class NewsPage(Page):
    heading = ""

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="Loading…")
        self.list.ROW_H = 62
        self.list.activated.connect(self.ctl.open_url)
        self._loaded = False

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.list.setGeometry(16, 22, self.width() - 32, self.height() - 38)

    def refresh(self) -> None:
        if self._loaded:
            return
        self.ctl.load_news(self._got)

    def _got(self, entries: list[dict] | None) -> None:
        if not entries:
            self.list.empty_text = "Could not load news (offline?)."
            self.list.set_rows([])
            return
        self._loaded = True
        self.list.set_rows([
            Row(title=e["title"],
                subtitle=(e["text"][:110] + "…") if len(e["text"]) > 110 else e["text"],
                right=e["date"], data=e["url"])
            for e in entries
        ])


# ---------- cài đặt ----------

class SettingsPage(Page):
    heading = ""

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        s = ctl.settings
        self.mem = AeroSlider(1024, self._max_memory(), s.memory_mb, 512, self)
        self.mem.changed.connect(self._set_memory)

        self.game_dir = QLineEdit(s.game_dir, self)
        self.game_dir.setStyleSheet(INPUT_QSS)
        self.game_dir.setFont(ui_font(9))
        self.game_dir.editingFinished.connect(self._set_dir)

        self.java = QLineEdit(s.java_path, self)
        self.java.setPlaceholderText("leave empty = auto-detect per version")
        self.java.setStyleSheet(INPUT_QSS)
        self.java.setFont(ui_font(9))
        self.java.editingFinished.connect(self._set_java)

        # Đăng nhập Microsoft đòi một Azure client ID, mà cho tới giờ chỉ đặt được
        # bằng biến môi trường hoặc sửa tay clients.json. Cách đó vô dụng với bản
        # cài đặt: người bấm vào installer không có terminal để export biến, và
        # càng không đi mò file JSON trong %APPDATA%. Nên nó phải nằm ở đây.
        self.client_id = QLineEdit(resolve_client_id("microsoft", "MC_CLIENT_ID"), self)
        self.client_id.setPlaceholderText("paste the Application (client) ID from Azure")
        self.client_id.setStyleSheet(INPUT_QSS)
        self.client_id.setFont(ui_font(9))
        self.client_id.editingFinished.connect(self._set_client_id)

        self.snapshots = AeroToggle(s.show_snapshots, self)
        self.snapshots.toggled.connect(self._set_snapshots)
        self.close_on_launch = AeroToggle(s.close_on_launch, self)
        self.close_on_launch.toggled.connect(self._set_close)

        self.open_dir = AeroButton("OPEN GAME FOLDER", self, height=32, tone="neutral")
        self.open_dir.clicked.connect(lambda: self.ctl.open_path(self.ctl.settings.game_path))
        self.doctor = AeroButton("CHECK INSTALL", self, height=32, tone="neutral")
        self.doctor.clicked.connect(self.ctl.run_doctor)
        self.bg_btn = AeroButton("CHANGE BACKGROUND", self, height=32, tone="neutral")
        self.bg_btn.clicked.connect(self.ctl.pick_background)

    @staticmethod
    def _total_memory_mb() -> int:
        """RAM thật của máy, tính bằng MB. Trả 0 nếu không hỏi được.

        Ba hệ điều hành ba cách hỏi. os.sysconf lo được cả Linux lẫn macOS, còn
        Windows không có sysconf nên phải gọi thẳng GlobalMemoryStatusEx qua
        ctypes. Trước đây chỗ này chỉ đọc /proc/meminfo, nên ngoài Linux thanh
        trượt luôn bị chốt ở mặc định 8 GB dù máy có bao nhiêu RAM đi nữa.
        """
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys) // (1024 * 1024)
            return 0

        try:
            return (os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")) // (1024 * 1024)
        except (OSError, ValueError, AttributeError):
            return 0

    @classmethod
    def _max_memory(cls) -> int:
        """Trần RAM = nửa RAM máy, làm tròn xuống bội 512, tối thiểu 4 GB."""
        total = cls._total_memory_mb()
        if not total:
            return 8192
        return max(4096, (total // 2) // 512 * 512)

    def _set_memory(self, value: int) -> None:
        self.ctl.settings.memory_mb = value
        self.ctl.settings.save()
        self.update()

    def _set_dir(self) -> None:
        self.ctl.set_game_dir(self.game_dir.text().strip())

    def _set_java(self) -> None:
        self.ctl.settings.java_path = self.java.text().strip()
        self.ctl.settings.save()

    def _set_client_id(self) -> None:
        # Client ID không phải bí mật (mọi launcher mã nguồn mở đều công khai của
        # mình), nhưng save_client_id vẫn ghi file với quyền 0600 cho đồng nhất
        # với chỗ đang giữ client secret của Google.
        save_client_id("microsoft", self.client_id.text().strip())

    def _set_snapshots(self, on: bool) -> None:
        self.ctl.settings.show_snapshots = on
        self.ctl.settings.save()

    def _set_close(self, on: bool) -> None:
        self.ctl.settings.close_on_launch = on
        self.ctl.settings.save()

    def resizeEvent(self, event) -> None:  # noqa: N802
        w = min(560, self.width() - 52)
        self.mem.setGeometry(26, 60, w, 26)
        self.game_dir.setGeometry(26, 142, w, 32)
        self.java.setGeometry(26, 218, w, 32)
        # Ô này có thêm một dòng gợi ý dưới nhãn nên tụt xuống 38px thay vì 28px
        # như các ô khác.
        self.client_id.setGeometry(26, 304, w, 32)
        self.snapshots.setGeometry(26, 368, 44, 22)
        self.close_on_launch.setGeometry(26, 408, 44, 22)
        self.open_dir.setGeometry(26, self.height() - 52, 190, 32)
        self.doctor.setGeometry(224, self.height() - 52, 170, 32)
        self.bg_btn.setGeometry(402, self.height() - 52, 210, 32)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        gb = self.ctl.settings.memory_mb / 1024

        def label(y: int, title: str, hint: str = "") -> None:
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(26, y, self.width() - 52, 18), Qt.AlignLeft | Qt.AlignVCenter, title)
            if hint:
                p.setFont(ui_font(8))
                p.setPen(TEXT_FAINT)
                p.drawText(QRect(26, y + 17, self.width() - 52, 16),
                           Qt.AlignLeft | Qt.AlignVCenter, hint)

        label(26, f"Max memory — {gb:.1f} GB", "")
        label(114, "Game folder")
        label(190, "Java path")
        label(266, "Microsoft Client ID",
              "Needed to sign in — portal.azure.com › App registrations › your app")
        p.setFont(ui_font(9))
        p.setPen(TEXT)
        p.drawText(QRect(84, 366, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Show snapshots")
        p.drawText(QRect(84, 406, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Close launcher when the game starts")

        warn = self.ctl.settings.memory_mb > self._max_memory() * 0.9
        if warn:
            p.setFont(ui_font(8))
            p.setPen(DEGRADED)
            p.drawText(QRect(26, 90, self.width() - 52, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       "Setting near all your RAM can freeze the system.")
        p.end()
