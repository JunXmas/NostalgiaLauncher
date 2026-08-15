"""Hộp thoại dạng lớp phủ trong cửa sổ: đăng nhập, nhập tên, xác nhận."""

from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

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
                 hint: str = "", ok_text: str = "THÊM"):
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
        self.cancel = AeroButton("HUỶ", self, height=34, tone="neutral")
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

    def __init__(self, parent, title: str, message: str, *, ok_text: str = "XOÁ"):
        super().__init__(parent, title, width=440, height=206)
        self.message = message
        self.ok = AeroButton(ok_text, self, height=34, tone="danger")
        self.ok.clicked.connect(self._go)
        self.cancel = AeroButton("HUỶ", self, height=34, tone="neutral")
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


# ---------- đăng nhập Microsoft ----------

class LoginDialog(GlassDialog):
    """Hiện mã device code, tự sao chép, và chờ người dùng xác nhận trên web."""

    def __init__(self, parent):
        super().__init__(parent, "Đăng nhập tài khoản Microsoft", width=500, height=272)
        self.code = ""
        self.url = ""
        self.message = "Đang xin mã từ Microsoft…"
        self.state = "waiting"  # waiting | ready | error | done
        self.copy_btn = AeroButton("SAO CHÉP MÃ", self, height=32, tone="neutral")
        self.copy_btn.clicked.connect(self._copy)
        self.copy_btn.setVisible(False)
        self.close_btn = AeroButton("ĐÓNG", self, height=32, tone="neutral")
        self.close_btn.clicked.connect(self.dismiss)
        self.place()

    def place(self) -> None:
        c = self.card
        self.copy_btn.setGeometry(c.left() + 22, c.bottom() - 50, 150, 32)
        self.close_btn.setGeometry(c.right() - 122, c.bottom() - 50, 100, 32)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.code)
        self.message = "Đã chép mã. Dán vào trang vừa mở rồi xác nhận."
        self.update()

    def show_code(self, url: str, code: str) -> None:
        self.url, self.code, self.state = url, code, "ready"
        self.message = "Mở trang bên dưới, nhập mã, rồi quay lại đây."
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
            f.setLetterSpacing(f.AbsoluteSpacing, 5)
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

    def __init__(self, parent, title: str, body: str = "Đang chạy…"):
        super().__init__(parent, title, width=min(760, parent.width() - 80),
                         height=min(520, parent.height() - 90))
        self.view = QTextBrowser(self)
        self.view.setStyleSheet(REPORT_QSS)
        f = ui_font(9)
        f.setFamily("monospace")
        self.view.setFont(f)
        self.view.setPlainText(body)
        self.close_btn = AeroButton("ĐÓNG", self, height=32, tone="neutral")
        self.close_btn.clicked.connect(self.dismiss)
        self.place()

    def set_body(self, text: str) -> None:
        self.view.setPlainText(text)

    def place(self) -> None:
        c = self.card
        self.view.setGeometry(c.left() + 20, c.top() + 52, c.width() - 40, c.height() - 116)
        self.close_btn.setGeometry(c.right() - 122, c.bottom() - 48, 100, 32)
