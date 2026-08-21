"""Modal chọn Instance khi cài một mod — thay cho ô dropdown cố định ở góc.

Luồng:
  Card Mod → nút "Install" (results.activated) → InstallTargetDialog:
    • liệt kê mọi Instance kèm [MC version] + [loader],
    • tự kiểm tra tương thích (mc + loader của instance so với mod),
      instance không hợp bị làm mờ + nhãn "Không tương thích",
    • hàng cuối "＋ Tạo Instance mới cho mod này",
  → chọn instance hợp + Xác nhận → tải mod vào <instance>/mods/.

Chia thành component rõ ràng: `instance_target`/`check_compat` (thuần logic),
`InstanceRow` (một hàng chọn được), `InstallTargetDialog` (QDialog kính Aero).
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .. import optifine
from ..i18n import tr
from .dialogs import GlassDialog
from .theme import AERO_TINT, CONNECTED, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT, ui_font
from .widgets import AeroButton


# ─────────────────────────── Logic tương thích (thuần) ───────────────────────────

def instance_target(instance) -> tuple[str, str]:
    """Suy (mc_version, loader) từ id phiên bản của một Instance.

    vd 'fabric-loader-0.19.3-1.21.11' → ('1.21.11', 'fabric');
       '1.12.2-forge-14.23.5.2859'   → ('1.12.2', 'forge');
       '1.20.6'                        → ('1.20.6', 'vanilla').
    """
    v = (instance.version or "").lower()
    if "fabric-loader" in v or "quilt-loader" in v:
        mc = (instance.version or "").rsplit("-", 1)[-1]
        loader = "quilt" if "quilt" in v else "fabric"
    elif "neoforge" in v:
        mc, loader = optifine.mc_from_version_id(instance.version) or "", "neoforge"
    elif "forge" in v:
        mc, loader = optifine.mc_from_version_id(instance.version) or "", "forge"
    else:
        mc = optifine.mc_from_version_id(instance.version) or (instance.version or "")
        loader = "vanilla"
    return mc, loader


def check_compat(instance, mc_versions: list[str], loaders: list[str]) -> tuple[bool, str]:
    """Instance có chạy được mod không → (ok, lý do khi không).

    mc_versions/loaders là tập MC + loader mà MOD hỗ trợ (từ Modrinth). Rỗng =
    không rõ → coi như hợp về mặt đó (để không chặn nhầm).
    """
    mc, loader = instance_target(instance)
    if loaders and loader not in loaders:
        return False, tr("Needs {loaders}").format(loaders=", ".join(sorted(loaders)).title())
    if mc_versions and mc not in mc_versions:
        return False, tr("Not for MC {mc}").format(mc=mc)
    return True, ""


# ─────────────────────────────── Một hàng Instance ───────────────────────────────

class InstanceRow(QWidget):
    """Một dòng chọn được: tên + (MC · loader), có trạng thái disable/selected."""

    clicked = Signal(str)          # phát tên instance ("" = hàng "tạo mới")
    ROW_H = 52

    def __init__(self, parent, *, name: str, subtitle: str,
                 enabled: bool = True, reason: str = "", create: bool = False):
        super().__init__(parent)
        self._name = name
        self._subtitle = subtitle
        self._enabled = enabled
        self._reason = reason
        self._create = create
        self._hover = False
        self._selected = False
        self.setFixedHeight(self.ROW_H)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)

    def set_selected(self, on: bool) -> None:
        if on != self._selected:
            self._selected = on
            self.update()

    def enterEvent(self, e):  # noqa: N802
        if self._enabled and not self._hover:
            self._hover = True; self.update()

    def leaveEvent(self, e):  # noqa: N802
        if self._hover:
            self._hover = False; self.update()

    def mousePressEvent(self, e):  # noqa: N802
        if self._enabled and e.button() == Qt.LeftButton:
            self.clicked.emit(self._name)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect().adjusted(0, 2, -1, -2))

        # ---- Mặt kính Aero: tint + gloss + sheen, cắt theo bo góc ----
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.save()
        p.setClipPath(clip)
        # 1) sắc kính lam (mờ hẳn khi disable, sáng khi hover/selected)
        tint = 14 if not self._enabled else 66 if self._selected else 50 if self._hover else 32
        p.fillRect(r, QColor(AERO_TINT.red(), AERO_TINT.green(), AERO_TINT.blue(), tint))
        # 2) gloss: sáng nửa trên, "kệ" ở giữa, tối nhẹ đáy (bóng nút Aero)
        top_a = 40 if self._enabled else 14
        g = QLinearGradient(r.left(), r.top(), r.left(), r.bottom())
        g.setColorAt(0.0, QColor(255, 255, 255, top_a))
        g.setColorAt(0.48, QColor(255, 255, 255, top_a // 5))
        g.setColorAt(0.52, QColor(255, 255, 255, 0))
        g.setColorAt(1.0, QColor(10, 20, 35, 46))
        p.fillRect(r, g)
        # 3) sheen chéo khi hover/selected
        if self._enabled and (self._hover or self._selected):
            s = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
            s.setColorAt(0.0, QColor(255, 255, 255, 34))
            s.setColorAt(0.35, QColor(255, 255, 255, 8))
            s.setColorAt(0.6, QColor(255, 255, 255, 0))
            p.fillRect(r, s)
        p.restore()

        # ---- Bevel: gờ sáng đỉnh + phản chiếu lam đáy ----
        inner = r.adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(255, 255, 255, 120 if self._enabled else 36), 1))
        p.drawLine(int(inner.left()) + 8, int(inner.top()),
                   int(inner.right()) - 8, int(inner.top()))
        p.setPen(QPen(QColor(120, 190, 240, 70 if self._enabled else 22), 1))
        p.drawLine(int(inner.left()) + 8, int(inner.bottom()),
                   int(inner.right()) - 8, int(inner.bottom()))

        # ---- Viền ngoài / glow cyan khi selected ----
        p.setBrush(Qt.NoBrush)
        if self._selected:
            p.setPen(QPen(QColor(111, 208, 239, 70), 3))
            p.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), 8, 8)
            p.setPen(QPen(QColor(150, 224, 245), 1.4))
            p.drawRoundedRect(r.adjusted(0.7, 0.7, -0.7, -0.7), 8, 8)
        else:
            p.setPen(QPen(QColor(255, 255, 255, 44 if self._enabled else 18), 1))
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        left = int(r.left()) + 14
        # Hàng "tạo mới": dấu ＋ + nhãn, tông accent.
        if self._create:
            p.setFont(ui_font(13, bold=True))
            p.setPen(QColor(150, 210, 255) if self._hover else TEXT_DIM)
            p.drawText(QRect(left, int(r.top()), 20, int(r.height())),
                       Qt.AlignVCenter | Qt.AlignLeft, "＋")
            p.setFont(ui_font(10, bold=True))
            p.setPen(TEXT if self._hover else TEXT_DIM)
            p.drawText(QRect(left + 22, int(r.top()), int(r.width()) - 40, int(r.height())),
                       Qt.AlignVCenter | Qt.AlignLeft, self._name or tr("Create a new instance"))
            return

        col = TEXT if self._enabled else QColor(TEXT.red(), TEXT.green(), TEXT.blue(), 120)
        # Tên instance.
        p.setFont(ui_font(10.5, bold=True))
        p.setPen(col)
        p.drawText(QRect(left, int(r.top()) + 7, int(r.width()) - 130, 18),
                   Qt.AlignLeft | Qt.AlignVCenter, self._name)
        # Phụ đề: MC · loader.
        p.setFont(ui_font(8.5))
        p.setPen(TEXT_FAINT if self._enabled else QColor(TEXT_FAINT.red(), TEXT_FAINT.green(),
                                                         TEXT_FAINT.blue(), 110))
        p.drawText(QRect(left, int(r.top()) + 26, int(r.width()) - 130, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, self._subtitle)

        # Nhãn phải: "Không tương thích" (disable) hoặc dấu check (selected).
        rr = QRect(int(r.right()) - 122, int(r.top()), 110, int(r.height()))
        if not self._enabled:
            p.setFont(ui_font(8.5, bold=True))
            p.setPen(DEGRADED)
            p.drawText(rr, Qt.AlignRight | Qt.AlignVCenter, self._reason or tr("Incompatible"))
        elif self._selected:
            p.setFont(ui_font(9, bold=True))
            p.setPen(QColor(111, 208, 239))
            p.drawText(rr, Qt.AlignRight | Qt.AlignVCenter, tr("Selected ✓"))


# ─────────────────────────────── Modal chọn đích ───────────────────────────────

class InstallTargetDialog(GlassDialog):
    """QDialog kính Aero: chọn Instance đích để cài mod (kèm kiểm tra tương thích)."""

    confirmed = Signal(str)        # tên instance đã chọn
    create_new = Signal()          # người dùng muốn tạo instance mới

    _PAD = 22
    _TOP = 56                       # chừa cho tiêu đề
    _FOOT = 58                      # chừa cho nút

    def __init__(self, parent, *, mod_name: str, instances: list,
                 mc_versions: list[str], loaders: list[str]):
        n = len(instances) + 1                      # + hàng "tạo mới"
        body = n * (InstanceRow.ROW_H + 6)
        height = min(self._TOP + body + self._FOOT, 560)
        super().__init__(parent, tr("Install {mod}").format(mod=mod_name),
                         width=460, height=height)
        self._selected: str | None = None
        self._scroll_note = body > (height - self._TOP - self._FOOT)  # dư -> nên cuộn

        # Hàng cho từng instance (đã tính tương thích).
        self.rows: list[InstanceRow] = []
        for inst in instances:
            ok, reason = check_compat(inst, mc_versions, loaders)
            mc, loader = instance_target(inst)
            row = InstanceRow(self, name=inst.name,
                              subtitle=f"{mc or '?'} · {loader.title()}",
                              enabled=ok, reason=reason)
            row.clicked.connect(self._pick)
            self.rows.append(row)

        # Hàng "tạo instance mới".
        self.create_row = InstanceRow(self, name=tr("Create a new instance"),
                                      subtitle="", create=True)
        self.create_row.clicked.connect(self._on_create)

        # Nút xác nhận / huỷ.
        self.ok = AeroButton(tr("CONFIRM"), self, height=34)
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self._confirm)
        self.cancel = AeroButton(tr("CANCEL"), self, height=34, tone="neutral")
        self.cancel.clicked.connect(self.dismiss)

        self.place()

    # --- chọn / xác nhận ---
    def _pick(self, name: str) -> None:
        self._selected = name
        for row in self.rows:
            row.set_selected(row._name == name)
        self.create_row.set_selected(False)
        self.ok.setEnabled(True)

    def _on_create(self, _name: str) -> None:
        self.create_new.emit()
        self.dismiss()

    def _confirm(self) -> None:
        if self._selected:
            self.confirmed.emit(self._selected)
            self.dismiss()

    # --- bố cục widget con trong khung thẻ ---
    def place(self) -> None:
        c = self.card
        x = c.left() + self._PAD
        w = c.width() - self._PAD * 2
        y = c.top() + self._TOP
        for row in self.rows + [self.create_row]:
            row.setGeometry(x, y, w, InstanceRow.ROW_H)
            y += InstanceRow.ROW_H + 6
        self.ok.setGeometry(c.right() - 132, c.bottom() - 46, 110, 34)
        self.cancel.setGeometry(c.right() - 250, c.bottom() - 46, 108, 34)

    def paint_body(self, p: QPainter) -> None:
        """Thêm chất kính Aero cho thẻ: sheen chéo lớn + gờ sáng đỉnh + gạch dưới tiêu đề."""
        c = self.card
        cf = QRectF(c)
        clip = QPainterPath()
        clip.addRoundedRect(cf, 5, 5)
        p.save()
        p.setClipPath(clip)
        # Sheen chéo phủ nửa trên thẻ.
        s = QLinearGradient(cf.left(), cf.top(), cf.right(), cf.center().y())
        s.setColorAt(0.0, QColor(255, 255, 255, 24))
        s.setColorAt(0.4, QColor(255, 255, 255, 6))
        s.setColorAt(0.72, QColor(255, 255, 255, 0))
        p.fillRect(cf, s)
        p.restore()
        # Gờ sáng đỉnh + gạch mờ dưới tiêu đề.
        p.setPen(QPen(QColor(255, 255, 255, 80), 1))
        p.drawLine(c.left() + 6, c.top() + 1, c.right() - 6, c.top() + 1)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.drawLine(c.left() + 22, c.top() + 45, c.right() - 22, c.top() + 45)
