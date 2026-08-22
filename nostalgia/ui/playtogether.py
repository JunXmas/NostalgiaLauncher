"""Trang "Play Together" — chơi cùng bạn bè KHÔNG cần host server, không mod, mọi
phiên bản. Chia sẻ một mã phòng; dữ liệu đi qua relay Cloudflare nên 2 người khác
mạng vẫn thấy nhau trong tab LAN của Minecraft. Người chơi không cài/cấu hình gì.
"""
from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLineEdit

from ..i18n import tr
from .multiplayer_worker import MultiplayerService, make_code
from .pages import INPUT_QSS, Page
from .theme import ACCENT, CONNECTED, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font
from .widgets import AeroButton

_GAP = 20
_PANEL_TOP = 116        # chừa chỗ trên cùng cho hàng chọn instance


class PlayTogetherPage(Page):
    heading = "Play Together"
    subheading = "Play with friends — no server needed, just share a room code."

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self._host_state = "idle"     # idle | waiting | live
        self._join_state = "idle"     # idle | connecting | ready
        self._code = ""
        self._join_port = 0
        self._error = ""
        self._instance_name = ""      # game sẽ launch (rỗng = dùng instance đang chọn)

        # Chọn game để launch cho CẢ host lẫn join, ngay trên trang này.
        self.inst_btn = AeroButton("", self, height=34, tone="neutral")
        self.inst_btn.clicked.connect(self._open_instance_picker)

        self.svc = MultiplayerService(parent=self)
        self.svc.waiting_world.connect(self._on_waiting)
        self.svc.hosting_live.connect(self._on_live)
        self.svc.joined.connect(self._on_joined)
        self.svc.failed.connect(self._on_failed)
        self.svc.ended.connect(self._on_ended)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.svc.shutdown)

        # HOST
        self.host_btn = AeroButton(tr("HOST MY WORLD"), self, height=40, tone="green")
        self.host_btn.clicked.connect(self._on_host)
        self.launch_host = AeroButton(tr("LAUNCH & HOST"), self, height=40, tone="green")
        self.launch_host.clicked.connect(self._on_launch_host)
        self.launch_host.hide()
        self.host_stop = AeroButton(tr("STOP HOSTING"), self, height=32, tone="danger")
        self.host_stop.clicked.connect(self._reset)
        self.host_stop.hide()

        # JOIN
        self.code_in = QLineEdit(self)
        self.code_in.setStyleSheet(INPUT_QSS)
        self.code_in.setPlaceholderText(tr("Enter your friend's room code"))
        self.code_in.setMaxLength(12)
        self.code_in.returnPressed.connect(self._on_join)
        self.join_btn = AeroButton(tr("JOIN"), self, height=40, tone="neutral")
        self.join_btn.clicked.connect(self._on_join)
        self.launch_join = AeroButton(tr("LAUNCH & JOIN"), self, height=40, tone="green")
        self.launch_join.clicked.connect(self._on_launch_join)
        self.launch_join.hide()
        self.join_stop = AeroButton(tr("LEAVE"), self, height=32, tone="danger")
        self.join_stop.clicked.connect(self._reset)
        self.join_stop.hide()

        self._refresh_instance_label()

    # ── hình học ─────────────────────────────────────────────────────────────
    def _panels(self):
        pw = (self.width() - 52 - _GAP) // 2
        ph = self.height() - _PANEL_TOP - 20
        return QRect(26, _PANEL_TOP, pw, ph), QRect(26 + pw + _GAP, _PANEL_TOP, pw, ph)

    def resizeEvent(self, event) -> None:  # noqa: N802
        # Hàng chọn game ở trên cùng (dùng cho cả host lẫn join).
        self.inst_btn.setGeometry(26, 74, min(380, self.width() - 52), 34)

        host, join = self._panels()
        self.host_btn.setGeometry(host.x() + 20, host.bottom() - 56, host.width() - 40, 40)
        self.launch_host.setGeometry(host.x() + 20, host.bottom() - 104, host.width() - 40, 40)
        self.host_stop.setGeometry(host.x() + 20, host.bottom() - 56, host.width() - 40, 32)

        self.code_in.setGeometry(join.x() + 20, join.y() + 116, join.width() - 40, 34)
        self.join_btn.setGeometry(join.x() + 20, join.bottom() - 56, join.width() - 40, 40)
        self.launch_join.setGeometry(join.x() + 20, join.bottom() - 56, join.width() - 40, 40)
        self.join_stop.setGeometry(join.x() + 20, join.bottom() - 104, join.width() - 40, 32)

    # ── sự kiện host ─────────────────────────────────────────────────────────
    def _on_host(self) -> None:
        if self.svc.role:
            self.svc.stop_session()
        self._error = ""
        self._code = make_code()
        self._host_state = "waiting"
        self.svc.host(self._code)
        self._sync()

    def _on_waiting(self) -> None:
        self._host_state = "waiting"
        self._sync()

    def _on_live(self, code: str) -> None:
        self._host_state = "live"
        self._code = code
        self._sync()

    # ── sự kiện join ─────────────────────────────────────────────────────────
    def _on_join(self) -> None:
        code = self.code_in.text().strip().upper()
        if len(code) < 4:
            self._error = "That room code doesn't look right."
            self._sync()
            return
        if self.svc.role:
            self.svc.stop_session()
        self._error = ""
        self._join_state = "connecting"
        self.svc.join(code)
        self._sync()

    def _on_joined(self, port: int) -> None:
        self._join_state = "ready"
        self._join_port = port
        self._sync()

    def _on_launch_join(self) -> None:
        if self._join_port:
            self.ctl.start_launch({"type": "multiplayer",
                                   "target": f"127.0.0.1:{self._join_port}"},
                                  instance=self._instance())

    def _on_launch_host(self) -> None:
        # Host chạy game bình thường (không quick_play) rồi Esc → Open to LAN.
        self.ctl.start_launch(instance=self._instance())

    # ── chọn game để launch ────────────────────────────────────────────────────
    def _instance(self):
        """Instance sẽ launch: cái người dùng chọn ở trang này, nếu không thì cái
        đang active trong launcher."""
        inst = self.ctl.instances.get(self._instance_name) if self._instance_name else None
        return inst or self.ctl.active_instance()

    def _open_instance_picker(self) -> None:
        r = self.inst_btn.geometry()
        origin = self.mapTo(self.window(), r.topLeft())
        self.ctl.pick_instance_menu(QRect(origin, r.size()), self._pick_instance,
                                    current=self._instance_name)

    def _pick_instance(self, name: str) -> None:
        self._instance_name = name
        self._refresh_instance_label()

    def _refresh_instance_label(self) -> None:
        inst = self._instance()
        self.inst_btn.setText((inst.name if inst else tr("No game — create one first")) + "   ▾")
        self.inst_btn.update()

    # ── chung ────────────────────────────────────────────────────────────────
    def _on_failed(self, msg: str) -> None:
        self._error = msg or "Connection error."
        self._host_state = self._join_state = "idle"
        self._sync()

    def _on_ended(self) -> None:
        self._sync()

    def _reset(self) -> None:
        self.svc.stop_session()
        self._host_state = self._join_state = "idle"
        self._code = ""
        self._join_port = 0
        self._sync()

    def _sync(self) -> None:
        hosting = self._host_state != "idle"
        joining = self._join_state != "idle"
        self.host_btn.setVisible(not hosting)
        self.launch_host.setVisible(hosting)
        self.host_stop.setVisible(hosting)
        self.join_btn.setVisible(not joining)
        self.launch_join.setVisible(self._join_state == "ready")
        self.join_stop.setVisible(joining)
        self.code_in.setEnabled(not joining)
        self.update()

    def refresh(self) -> None:
        self._refresh_instance_label()
        self._sync()

    # ── vẽ ───────────────────────────────────────────────────────────────────
    def _panel(self, p: QPainter, r: QRect, title: str, accent: QColor) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 16))
        p.drawRoundedRect(r, 6, 6)
        # vệt bóng trên (gloss) + bevel
        gloss = gloss_gradient(r.height(), 0.5)
        p.save(); p.translate(r.topLeft()); p.fillRect(QRect(0, 0, r.width(), r.height()), gloss); p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawLine(r.x() + 1, r.y() + 1, r.right() - 1, r.y() + 1)
        p.setPen(QPen(QColor(0, 0, 0, 60), 1))
        p.drawLine(r.x() + 1, r.bottom(), r.right() - 1, r.bottom())
        # tiêu đề panel
        f = ui_font(11, bold=True); f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        p.setFont(f); p.setPen(accent)
        p.drawText(QRect(r.x() + 20, r.y() + 16, r.width() - 40, 22),
                   Qt.AlignLeft | Qt.AlignVCenter, title)

    def _status_dot(self, p: QPainter, x: int, y: int, color: QColor, text: str) -> None:
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawEllipse(x, y + 4, 8, 8)
        p.setFont(ui_font(9)); p.setPen(TEXT_DIM)
        p.drawText(QRect(x + 16, y - 2, 300, 18), Qt.AlignLeft | Qt.AlignVCenter, tr(text))

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        host, join = self._panels()

        # ── hàng chọn game để launch ──
        f = ui_font(9, bold=True); f.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        p.setFont(f); p.setPen(TEXT_FAINT)
        p.drawText(QRect(26, 52, self.width() - 52, 16),
                   Qt.AlignLeft | Qt.AlignVCenter, tr("GAME TO LAUNCH"))

        # ── HOST ──
        self._panel(p, host, tr("HOST — OPEN A ROOM"), ACCENT)
        hx = host.x() + 20
        if self._host_state == "idle":
            p.setFont(ui_font(9)); p.setPen(TEXT_FAINT)
            p.drawText(QRect(hx, host.y() + 48, host.width() - 40, 120),
                       Qt.TextWordWrap,
                       tr("You're the host: open your world to friends. Click the button, "
                          "then in Minecraft open your world and choose Esc → Open to LAN. "
                          "The launcher gives you a room code to send to your friends."))
        else:
            # mã phòng lớn để chia sẻ
            p.setFont(ui_font(9)); p.setPen(TEXT_FAINT)
            p.drawText(QRect(hx, host.y() + 48, host.width() - 40, 18),
                       Qt.AlignLeft, tr("ROOM CODE — send to friends"))
            cf = ui_font(26, bold=True); cf.setLetterSpacing(QFont.AbsoluteSpacing, 6.0)
            p.setFont(cf); p.setPen(TEXT)
            p.drawText(QRect(hx, host.y() + 66, host.width() - 40, 44),
                       Qt.AlignLeft | Qt.AlignVCenter, self._code)
            if self._host_state == "waiting":
                self._status_dot(p, hx, host.y() + 120, DEGRADED,
                                 "Waiting… in Minecraft: Esc → Open to LAN")
            else:
                self._status_dot(p, hx, host.y() + 120, CONNECTED,
                                 "Live — friends can join now")

        # ── JOIN ──
        self._panel(p, join, tr("JOIN — ENTER A ROOM"), QColor(120, 180, 235))
        jx = join.x() + 20
        p.setFont(ui_font(9)); p.setPen(TEXT_FAINT)
        p.drawText(QRect(jx, join.y() + 48, join.width() - 40, 60), Qt.TextWordWrap,
                   tr("Paste a friend's room code and click JOIN. Their world shows up in "
                      "Minecraft's LAN tab, or click Launch & Join to jump straight in."))
        if self._join_state == "connecting":
            self._status_dot(p, jx, join.y() + 160, DEGRADED, "Connecting to the room…")
        elif self._join_state == "ready":
            self._status_dot(p, jx, join.y() + 160, CONNECTED,
                             "Ready — open the LAN tab, or Launch & Join")

        if self._error:
            p.setFont(ui_font(9)); p.setPen(QColor(228, 130, 130))
            p.drawText(QRect(26, self.height() - 18, self.width() - 52, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, tr(self._error))
        p.end()
