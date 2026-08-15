"""Các trang nội dung nằm giữa thanh trên và thanh dưới."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

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


class PlayPage(Page):
    """Không che gì — để ảnh hero hiện trọn vẹn."""

    scrim = False


# ---------- bản cài đặt ----------

class InstallationsPage(Page):
    heading = "Bản cài đặt"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="Chưa tải phiên bản nào. Bấm THÊM PHIÊN BẢN.")
        self.list.activated.connect(self._select)
        self.list.action_clicked.connect(self.ctl.ask_delete_version)
        self.add_btn = AeroButton("THÊM PHIÊN BẢN", self, height=32, tone="neutral")
        self.add_btn.clicked.connect(self.ctl.open_version_menu_for_install)
        self.fabric_btn = AeroButton("CÀI FABRIC", self, height=32, tone="neutral")
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
            state = "sẵn sàng" if v["complete"] else "mới có metadata"
            origin = f" · nền {v['parent']}" if v.get("parent") else ""
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
            self.note = "Chưa có tài khoản nào."
        elif account.kind != "msa" or not account.owns_game:
            self.note = ("Chỉ tài khoản Microsoft đã mua game mới có skin trên máy chủ.\n"
                         "Hồ sơ offline và tài khoản demo dùng skin mặc định Steve/Alex.")
        elif not account.skin_url:
            self.note = "Tài khoản này chưa lưu skin — đăng nhập lại để lấy về."
        else:
            self.ctl.load_skin(account.skin_url, self._got)
            self.note = "Đang tải skin…"
        self.update()

    def _got(self, data: bytes | None) -> None:
        if data:
            img = QImage()
            if img.loadFromData(data):
                self.skin = img
                self.note = ""
        else:
            self.note = "Không tải được skin."
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
                       "Đổi skin ở minecraft.net/msaprofile — launcher chỉ hiển thị,\n"
                       "chưa hỗ trợ tải skin mới lên.")
        elif self.note:
            p.setFont(ui_font(10))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(26, 70, self.width() - 52, 120),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.note)
        p.end()


# ---------- ghi chú phiên bản ----------

class NotesPage(Page):
    heading = "Ghi chú phiên bản"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="Đang tải…")
        self.list.ROW_H = 44
        self.list.activated.connect(self._open)
        self.body = QTextBrowser(self)
        self.body.setStyleSheet(TEXT_QSS)
        self.body.setFont(ui_font(9))
        self.body.setOpenExternalLinks(True)
        self.body.setPlainText("Chọn một phiên bản bên trái để xem ghi chú.")
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
            self.list.empty_text = "Không tải được ghi chú (mất mạng?)."
            self.list.set_rows([])
            return
        self._entries = entries
        self.list.set_rows([
            Row(title=e["title"], subtitle=f"{e['type']} · {e['version']}", data=e["path"])
            for e in entries
        ])

    def _open(self, path) -> None:
        self.body.setPlainText("Đang tải…")
        self.ctl.load_patch_body(path, self.body.setPlainText)


# ---------- tin tức ----------

class NewsPage(Page):
    heading = ""

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="Đang tải…")
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
            self.list.empty_text = "Không tải được tin tức (mất mạng?)."
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
        self.java.setPlaceholderText("để trống = tự dò theo phiên bản")
        self.java.setStyleSheet(INPUT_QSS)
        self.java.setFont(ui_font(9))
        self.java.editingFinished.connect(self._set_java)

        self.snapshots = AeroToggle(s.show_snapshots, self)
        self.snapshots.toggled.connect(self._set_snapshots)
        self.close_on_launch = AeroToggle(s.close_on_launch, self)
        self.close_on_launch.toggled.connect(self._set_close)

        self.open_dir = AeroButton("MỞ THƯ MỤC GAME", self, height=32, tone="neutral")
        self.open_dir.clicked.connect(lambda: self.ctl.open_path(self.ctl.settings.game_path))
        self.doctor = AeroButton("KIỂM TRA CÀI ĐẶT", self, height=32, tone="neutral")
        self.doctor.clicked.connect(self.ctl.run_doctor)

    @staticmethod
    def _max_memory() -> int:
        """Trần RAM = nửa RAM máy, làm tròn xuống bội 512, tối thiểu 4 GB."""
        try:
            total = 0
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) // 1024
                    break
            return max(4096, (total // 2) // 512 * 512)
        except OSError:
            return 8192

    def _set_memory(self, value: int) -> None:
        self.ctl.settings.memory_mb = value
        self.ctl.settings.save()
        self.update()

    def _set_dir(self) -> None:
        self.ctl.set_game_dir(self.game_dir.text().strip())

    def _set_java(self) -> None:
        self.ctl.settings.java_path = self.java.text().strip()
        self.ctl.settings.save()

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
        self.snapshots.setGeometry(26, 282, 44, 22)
        self.close_on_launch.setGeometry(26, 322, 44, 22)
        self.open_dir.setGeometry(26, self.height() - 52, 200, 32)
        self.doctor.setGeometry(238, self.height() - 52, 200, 32)

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

        label(26, f"Bộ nhớ tối đa — {gb:.1f} GB", "")
        label(114, "Thư mục game")
        label(190, "Đường dẫn Java")
        p.setFont(ui_font(9))
        p.setPen(TEXT)
        p.drawText(QRect(84, 280, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Hiện cả bản snapshot")
        p.drawText(QRect(84, 320, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Đóng launcher khi game chạy")

        warn = self.ctl.settings.memory_mb > self._max_memory() * 0.9
        if warn:
            p.setFont(ui_font(8))
            p.setPen(DEGRADED)
            p.drawText(QRect(26, 90, self.width() - 52, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       "Đặt gần hết RAM máy dễ làm treo hệ thống.")
        p.end()
