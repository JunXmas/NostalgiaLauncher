"""Các trang nội dung nằm giữa thanh trên và thanh dưới."""

from __future__ import annotations

import os

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

from .. import mods as mods_mgr
from .. import modrinth
from ..i18n import language, language_name, tr
from .controls import AeroSlider, AeroToggle, ListView, Row
from .dialogs import ConfirmDialog
from .menus import MenuItem, popup
from .theme import ACCENT, DEGRADED, TEXT, TEXT_DIM, TEXT_FAINT, gloss_gradient, ui_font
from .widgets import AeroButton, TabBar

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


def human_count(n: int) -> str:
    """Số lượt tải gọn: 1234 -> 1.2K, 5_600_000 -> 5.6M."""
    for div, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if n >= div:
            return f"{n / div:.1f}{suffix}"
    return str(n)


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
    heading = "Instances"

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.list = ListView(self, empty_text="No instances yet. Click NEW INSTANCE (name + version).")
        self.list.activated.connect(self._select)
        self.list.action_clicked.connect(self._delete)
        self.list.badge_clicked.connect(self.ctl.edit_instance)
        self.add_btn = AeroButton("NEW INSTANCE", self, height=32, tone="neutral")
        self.add_btn.clicked.connect(self.ctl.begin_create_instance)
        self.fabric_btn = AeroButton("GET MODPACK", self, height=32, tone="neutral")
        self.fabric_btn.clicked.connect(self.ctl.begin_browse_modpacks)
        self.logs_btn = AeroButton("LOGS", self, height=32, tone="neutral")
        self.logs_btn.clicked.connect(self.ctl.show_logs)

    def _select(self, name) -> None:
        self.ctl.open_instance(name)

    def _delete(self, name) -> None:
        self.ctl.ask_delete_instance(name)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.list.setGeometry(16, 58, self.width() - 32, self.height() - 116)
        self.add_btn.setGeometry(self.width() - 196, self.height() - 46, 180, 32)
        self.fabric_btn.setGeometry(self.width() - 356, self.height() - 46, 150, 32)
        self.logs_btn.setGeometry(self.width() - 458, self.height() - 46, 92, 32)

    def refresh(self) -> None:
        current = self.ctl.instances.active
        ready = {v["id"] for v in self.ctl.installer.installed_versions() if v["complete"]}
        rows = []
        for inst in self.ctl.instances.all():
            state = "ready" if inst.version in ready else "will download on play"
            extra = f" · {inst.memory_mb // 1024} GB" if inst.memory_mb else ""
            if inst.playtime_sec:
                h, m = inst.playtime_sec // 3600, (inst.playtime_sec % 3600) // 60
                extra += f" · played {h}h {m}m" if h else f" · played {m}m"
            rows.append(Row(
                title=inst.name,
                subtitle=f"{inst.version} · {state}{extra}",
                checked=inst.name == current,
                badge="EDIT",
                action="delete",
                data=inst.name,
            ))
        self.list.set_rows(rows)


# ---------- thư viện nội dung: Mods / Resource Packs ----------

_LOADER_COLORS = {
    "fabric": QColor(222, 210, 168), "quilt": QColor(178, 132, 226),
    "forge": QColor(120, 142, 190), "neoforge": QColor(232, 152, 92),
}
_LOADERS = {"fabric", "forge", "neoforge", "quilt", "liteloader", "rift",
            "modloader", "optifine", "iris", "canvas", "vanilla", "datapack",
            "folia", "paper", "spigot", "bukkit", "purpur", "sponge",
            "velocity", "waterfall", "bungeecord"}


def _reltime_iso(iso: str) -> str:
    import datetime
    if not iso:
        return ""
    try:
        d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        s = (now - d).total_seconds()
    except (ValueError, TypeError):
        return ""
    for unit, sec in (("y", 31536000), ("mo", 2592000), ("d", 86400),
                      ("h", 3600), ("m", 60)):
        if s >= sec:
            n = int(s // sec)
            return f"{n}{unit} ago"
    return "just now"


class ModrinthResultsView(QWidget):
    """Danh sách kết quả Modrinth kiểu thẻ: icon, tên · tác giả, mô tả, lượt tải/
    thích/cập nhật, pill danh mục + loader, và thanh phân trang ở đáy."""

    activated = Signal(object)     # bấm thẻ -> cài hit
    page_changed = Signal(int)     # bấm số trang -> nạp trang

    CARD_H = 96
    PAGER_H = 44

    def __init__(self, parent=None, *, empty_text: str = ""):
        super().__init__(parent)
        self.empty_text = empty_text
        self._hits: list = []
        self._icons: dict = {}
        self._badges: dict = {}
        self._page = self._pages = 1
        self._scroll = 0
        self._hover = -1
        self._card_rects: list = []
        self._page_rects: list = []
        self.setMouseTracking(True)

    def set_page(self, hits, page, pages, badges) -> None:
        self._hits, self._page, self._pages = hits, page, max(1, pages)
        self._badges = badges
        self._scroll = 0
        self._hover = -1
        self.update()

    def set_state(self, icons, badges) -> None:      # icon/badge cập nhật -> vẽ lại
        self._icons, self._badges = icons, badges
        self.update()

    def _content_h(self) -> int:
        return self.height() - self.PAGER_H

    def wheelEvent(self, e):  # noqa: N802
        maxs = max(0, len(self._hits) * self.CARD_H + 8 - self._content_h())
        self._scroll = min(maxs, max(0, self._scroll - e.angleDelta().y()))
        self.update()

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        h = next((i for i, (r, _) in enumerate(self._card_rects) if r.contains(pos)), -1)
        if h != self._hover:
            self._hover = h
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        for r, page in self._page_rects:
            if r.contains(pos) and page != self._page:
                self.page_changed.emit(page)
                return
        for r, hit in self._card_rects:
            if r.contains(pos):
                self.activated.emit(hit)
                return

    def _pills(self, hit) -> list[tuple]:
        """(nhãn, màu|None) cho môi trường + danh mục + loader."""
        out = []
        cs, ss = hit.get("client_side"), hit.get("server_side")
        env = ("Client or server" if cs != "unsupported" and ss != "unsupported"
               else "Server" if ss != "unsupported" else "Client")
        out.append((env, None))
        cats = hit.get("display_categories") or hit.get("categories") or []
        for c in cats:
            if c not in _LOADERS:
                out.append((c.replace("-", " ").title(), None))
        for c in hit.get("categories", []):
            if c in _LOADERS:
                out.append((c.title(), _LOADER_COLORS.get(c, QColor(150, 160, 180))))
        return out

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._card_rects = []
        self._page_rects = []
        w = self.width()
        ch = self._content_h()
        p.setClipRect(0, 0, w, ch)
        if not self._hits:
            p.setPen(TEXT_DIM); p.setFont(ui_font(11))
            p.drawText(QRect(0, 0, w, ch), Qt.AlignCenter, self.empty_text)
            p.setClipping(False)
            self._paint_pager(p)
            p.end()
            return
        for i, hit in enumerate(self._hits):
            y = 4 - self._scroll + i * self.CARD_H
            if y + self.CARD_H < 0 or y > ch:
                continue
            card = QRect(6, y, w - 12, self.CARD_H - 8)
            self._card_rects.append((card, hit))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 24 if i == self._hover else 12))
            p.drawRoundedRect(card, 8, 8)
            self._paint_card(p, card, hit)
        p.setClipping(False)
        self._paint_pager(p)
        p.end()

    def _paint_card(self, p, card, hit):
        # icon
        ic = QRect(card.left() + 12, card.top() + 12, 60, 60)
        pm = self._icons.get(hit.get("icon_url") or "")
        p.save(); p.setClipRect(ic)
        if pm is not None and not pm.isNull():
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            scaled = pm.scaled(ic.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ox = ic.left() + (ic.width() - scaled.width()) // 2
            oy = ic.top() + (ic.height() - scaled.height()) // 2
            p.fillRect(ic, QColor(28, 40, 60, 120))
            p.drawPixmap(ox, oy, scaled)
        else:
            p.fillRect(ic, QColor(40, 60, 90, 160))
        p.restore()
        p.setPen(QColor(255, 255, 255, 40)); p.setBrush(Qt.NoBrush); p.drawRect(ic)

        tx = ic.right() + 14
        # thống kê bên phải
        p.setFont(ui_font(9)); p.setPen(TEXT_DIM)
        dls = f"⬇ {human_count(hit.get('downloads', 0))}"
        fol = f"♥ {human_count(hit.get('follows', 0))}"
        upd = _reltime_iso(hit.get("date_modified", ""))
        rx = card.right() - 12
        fm = p.fontMetrics()
        stat = f"{dls}    {fol}"
        p.drawText(QRect(rx - 220, card.top() + 8, 220, 16),
                   Qt.AlignRight | Qt.AlignVCenter, stat)
        if upd:
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(rx - 220, card.top() + 26, 220, 16),
                       Qt.AlignRight | Qt.AlignVCenter, f"🕒 {upd}")
        right_edge = rx - 230
        # tên + tác giả
        p.setFont(ui_font(12, bold=True)); p.setPen(TEXT)
        title = hit.get("title", "?")
        tw = p.fontMetrics().horizontalAdvance(title)
        p.drawText(tx, card.top() + 24, title)
        p.setFont(ui_font(9)); p.setPen(TEXT_DIM)
        p.drawText(tx + tw + 8, card.top() + 24, f"by {hit.get('author', '?')}")
        # trạng thái cài
        slug = hit.get("slug") or hit.get("project_id")
        st = self._badges.get(slug)
        if st:
            p.setPen(ACCENT if st == "ADDED" else TEXT_DIM)
            p.drawText(QRect(right_edge, card.top() + 44, 160, 16),
                       Qt.AlignRight | Qt.AlignVCenter, st)
        # mô tả
        p.setFont(ui_font(9)); p.setPen(TEXT_DIM)
        desc = (hit.get("description") or "").strip()
        p.drawText(tx, card.top() + 42,
                   p.fontMetrics().elidedText(desc, Qt.ElideRight, right_edge - tx))
        # pills
        self._paint_pills(p, tx, card.top() + 54, right_edge, self._pills(hit))

    def _paint_pills(self, p, x, y, right, pills):
        p.setFont(ui_font(8))
        fm = p.fontMetrics()
        for label, color in pills:
            tw = fm.horizontalAdvance(label)
            dot = 12 if color is not None else 0
            pw = tw + 16 + dot
            if x + pw > right - 24:
                p.setPen(TEXT_FAINT); p.setBrush(Qt.NoBrush)
                p.drawText(x + 2, y + 15, "…")
                break
            pill = QRect(x, y, pw, 20)
            p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(pill, 10, 10)
            lx = x + 8
            if color is not None:
                p.setBrush(color); p.drawEllipse(QRect(lx, y + 7, 6, 6)); lx += 12
            p.setPen(TEXT_DIM)
            p.drawText(QRect(lx, y, tw + 8, 20), Qt.AlignLeft | Qt.AlignVCenter, label)
            x += pw + 6

    def _paint_pager(self, p):
        if self._pages <= 1:
            return
        y = self.height() - self.PAGER_H
        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.drawLine(6, y, self.width() - 6, y)
        cur, last = self._page, self._pages
        nums = sorted({1, cur - 1, cur, cur + 1, last})
        nums = [n for n in nums if 1 <= n <= last]
        seq, prev = [], 0
        for n in nums:
            if prev and n - prev > 1:
                seq.append(None)      # dấu …
            seq.append(n); prev = n
        p.setFont(ui_font(10, bold=True))
        x = self.width() - 12
        for item in reversed(seq):    # xếp từ phải sang
            if item is None:
                x -= 24
                p.setPen(TEXT_FAINT)
                p.drawText(QRect(x, y, 24, self.PAGER_H), Qt.AlignCenter, "…")
                continue
            box = QRect(x - 34, y + 7, 30, 30)
            self._page_rects.append((box, item))
            if item == cur:
                p.setPen(Qt.NoPen); p.setBrush(ACCENT)
                p.drawEllipse(box); p.setPen(QColor(10, 20, 14))
            else:
                p.setPen(TEXT_DIM); p.setBrush(Qt.NoBrush)
            p.drawText(box, Qt.AlignCenter, str(item))
            x -= 40


class ContentLibraryPage(Page):
    """Hai tab: 'Installed' (bật/tắt/xoá/mở thư mục) và 'Browse' (tìm & cài từ Modrinth)."""

    kind = "mods"                 # "mods" | "resourcepacks"
    is_mod = True
    project_type = "mod"

    # nhãn tab sort -> tham số index của Modrinth
    SORTS = [("Relevance", "relevance"), ("Popular", "downloads"), ("Newest", "newest")]
    LOADERS = ["fabric", "forge", "neoforge", "quilt"]

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.embedded = False             # True = nhúng trong trang instance
        self._fixed_instance = None       # instance cố định khi nhúng
        self._top = 58                    # mốc y đầu nội dung (nhúng thì kéo lên)
        self._hits: list[dict] = []
        self._done: set[str] = set()      # slug đã cài trong phiên này
        self._busy: set[str] = set()      # slug đang tải
        self._icons: dict[str, object] = {}   # url -> QPixmap đã tải
        self._icon_wanted: set[str] = set()
        self._index = "downloads"         # sort đang chọn; mặc định Popular cho discover
        self._loader = "fabric"           # loader đang chọn (mods)
        self._discovered = False          # đã tự nạp mod hot lần đầu chưa
        self._instance = ctl.active_instance()   # cài/xem mod cho instance nào

        # Nút chọn instance (góc phải): quyết định cài mod vào modpack nào.
        self.inst_btn = AeroButton("Instance ▾", self, height=28, tone="neutral")
        self.inst_btn.clicked.connect(self._open_instance_menu)

        self.tabs = TabBar(["Installed", "Browse Modrinth"], self)
        self.tabs.changed.connect(self._show_tab)

        # --- Installed ---
        self._items: list = []
        self._updates: dict = {}          # tên hiển thị -> file bản mới (Modrinth)
        self._mod_icons: dict = {}        # (path, size) -> QPixmap icon rút từ jar
        self.inst_search = QLineEdit(self)
        self.inst_search.setPlaceholderText("Filter installed…")
        self.inst_search.setStyleSheet(INPUT_QSS)
        self.inst_search.setFont(ui_font(10))
        self.inst_search.textChanged.connect(lambda _t: self._apply_installed_filter())
        self.installed = ListView(self, empty_text=self._empty_installed)
        self.installed.badge_clicked.connect(self._toggle)
        self.installed.action_clicked.connect(self._ask_delete)
        self.installed.activated.connect(self._on_installed_click)
        self.open_btn = AeroButton("OPEN FOLDER", self, height=32, tone="neutral")
        self.open_btn.clicked.connect(
            lambda: self.ctl.open_path(mods_mgr.folder(self._game_dir(), self.kind)))
        self.update_btn = AeroButton("UPDATE ALL", self, height=32)   # xanh
        self.update_btn.clicked.connect(self._update_all)
        self.update_btn.setVisible(False)

        # --- Browse ---
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self._search_hint)
        self.search.setStyleSheet(INPUT_QSS)
        self.search.setFont(ui_font(10))
        self.search.returnPressed.connect(self._load)
        self.search_btn = AeroButton("SEARCH", self, height=32)
        self.search_btn.clicked.connect(self._load)

        # Thanh discover: sort + loader
        self.sort_tabs = TabBar([s[0] for s in self.SORTS], self)
        self.sort_tabs.current = 1        # Popular sáng sẵn, khớp discover
        self.sort_tabs.changed.connect(self._sort_changed)
        self.loader_tabs = TabBar([lo.capitalize() for lo in self.LOADERS], self)
        self.loader_tabs.changed.connect(self._loader_changed)

        self._page = 1
        self._total = 0
        self.results = ModrinthResultsView(self, empty_text="Loading popular picks from Modrinth…")
        self.results.activated.connect(self._install)
        self.results.page_changed.connect(self._go_page)

        self._show_tab(0)

    # tiện lấy theo lớp con
    @property
    def _empty_installed(self) -> str:
        return f"No {self.kind} yet. Open the Browse tab to add some from Modrinth."

    @property
    def _search_hint(self) -> str:
        return "Search mods on Modrinth…" if self.is_mod else "Search resource packs on Modrinth…"

    # ---- chế độ nhúng trong trang instance ----

    def enter_embedded(self, instance) -> None:
        """Nhúng vào trang instance: khoá vào 1 instance, ẩn bộ chọn, kéo layout lên."""
        self.embedded = True
        self.scrim = False           # trang instance tự vẽ nền/tiêu đề
        self._top = 6
        self._fixed_instance = instance
        self.inst_btn.hide()

    def set_instance(self, instance) -> None:
        self._fixed_instance = instance
        self._discovered = False
        self._updates = {}
        self.refresh()

    def configure(self, kind: str, project_type: str, is_mod: bool) -> None:
        """Đổi loại nội dung (mods/resourcepacks/shaderpacks) mà không đổi instance."""
        self.kind, self.project_type, self.is_mod = kind, project_type, is_mod
        self.search.setPlaceholderText(self._search_hint)
        self.installed.empty_text = self._empty_installed
        self._discovered = False
        self._updates = {}
        self._hits = []
        self._page, self._total = 1, 0
        self.results.set_page([], 1, 1, {})
        self._show_tab(0)

    # ---- instance đang thao tác ----

    def _game_dir(self):
        if self.embedded:
            inst = self._fixed_instance
        else:
            inst = self._instance or self.ctl.active_instance()
        return self.ctl.instance_dir(inst) if inst else self.ctl.store_root

    def _sync_instance(self) -> None:
        if self.embedded:
            self._instance = self._fixed_instance
            return
        # Instance có thể bị xoá/đổi ở nơi khác; đồng bộ lại và cập nhật nhãn nút.
        if not (self._instance and self.ctl.instances.get(self._instance.name)):
            self._instance = self.ctl.active_instance()
        self.inst_btn.setText((self._instance.name if self._instance else "No instance") + " ▾")

    def _open_instance_menu(self) -> None:
        items = [MenuItem(kind="header", label="Install into")]
        for inst in self.ctl.instances.all():
            items.append(MenuItem(
                label=inst.name, sublabel=inst.version,
                checked=bool(self._instance) and inst.name == self._instance.name,
                data=inst.name))
        if not self.ctl.instances.all():
            items.append(MenuItem(label="(no instances — create one first)", enabled=False))
        origin = self.inst_btn.mapTo(self.window(), self.inst_btn.rect().topLeft())
        popup(self.window(), items, QRect(origin, self.inst_btn.size()),
              self._pick_instance, width=224)

    def _pick_instance(self, name) -> None:
        inst = self.ctl.instances.get(name) if name else None
        if inst:
            self._instance = inst
            self._done.clear()          # trạng thái "ADDED" tính theo từng instance
            self._sync_instance()
            self.refresh()
            self._render_results()

    def _show_tab(self, i: int) -> None:
        self.tabs.current = i
        self.tabs.update()
        browse = i == 1
        for w in (self.installed, self.open_btn, self.inst_search):
            w.setVisible(not browse)
        self.update_btn.setVisible((not browse) and bool(self._updates))
        for w in (self.search, self.search_btn, self.results, self.sort_tabs):
            w.setVisible(browse)
        self.loader_tabs.setVisible(browse and self.is_mod)   # resource pack không có loader
        if browse:
            self.search.setFocus()
            if not self._discovered:
                self._discovered = True
                self._load()               # tự khám phá mod hot lần đầu
        else:
            self.refresh()

    def _sort_changed(self, i: int) -> None:
        self._index = self.SORTS[i][1]
        self._load()

    def _loader_changed(self, i: int) -> None:
        self._loader = self.LOADERS[i]
        self._load()

    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        t = self._top
        # Nút chọn instance ở hàng tab (phải); ẩn khi nhúng (instance đã cố định).
        if self.embedded:
            self.tabs.setGeometry(24, t, w - 48, 30)
        else:
            self.inst_btn.setGeometry(w - 232, t - 2, 210, 30)
            self.tabs.setGeometry(24, t, w - 260, 30)
        # Installed: ô lọc trên, danh sách dưới.
        self.inst_search.setGeometry(16, t + 40, w - 32, 32)
        self.installed.setGeometry(16, t + 80, w - 32, h - (t + 80) - 58)
        self.open_btn.setGeometry(w - 190, h - 46, 174, 32)
        self.update_btn.setGeometry(w - 356, h - 46, 156, 32)
        # Browse
        self.search.setGeometry(16, t + 40, w - 140, 32)
        self.search_btn.setGeometry(w - 116, t + 40, 100, 32)
        self.sort_tabs.setGeometry(16, t + 82, 210, 28)
        self.loader_tabs.setGeometry(238, t + 82, w - 254, 28)
        self.results.setGeometry(16, t + 118, w - 32, h - (t + 118) - 58)

    # ---- Installed ----

    def refresh(self) -> None:
        self._sync_instance()
        self._render_installed()
        self._check_updates()

    def _render_installed(self) -> None:
        self._items = mods_mgr.list_installed(self._game_dir(), self.kind)
        self._apply_installed_filter()

    def _installed_icon(self, it):
        """Icon rút từ jar/zip (cache theo path+size); None nếu không có."""
        key = (str(it.path), it.size)
        if key not in self._mod_icons:
            pm = None
            data = mods_mgr.content_icon(it.path)
            if data:
                from PySide6.QtGui import QPixmap
                p = QPixmap()
                if p.loadFromData(data) and not p.isNull():
                    pm = p
            self._mod_icons[key] = pm
        return self._mod_icons[key]

    def _apply_installed_filter(self) -> None:
        q = self.inst_search.text().strip().lower()
        rows = []
        for it in self._items:
            if q and q not in it.name.lower():
                continue
            note = human_size(it.size) + ("" if it.enabled else " · disabled")
            rows.append(Row(
                title=it.name,
                subtitle=note,
                right="↑ UPDATE" if it.name in self._updates else "",
                badge="ON" if it.enabled else "OFF",
                badge_on=it.enabled,
                action="delete",
                data=it,
                icon=self._installed_icon(it),
            ))
        self.installed.set_rows(rows)
        has = bool(self._updates) and self.tabs.current == 0
        self.update_btn.setVisible(has)
        if self._updates:
            self.update_btn.setText(f"UPDATE ALL ({len(self._updates)})")

    def _check_updates(self) -> None:
        """Hỏi Modrinth theo hash xem mod nào có bản mới hợp phiên bản instance."""
        items = list(self._items)
        if not items:
            self._updates = {}
            self.update_btn.setVisible(False)
            return
        loaders, gvs = self._target()

        def work():
            by_hash = {}
            for it in items:
                try:
                    by_hash[mods_mgr.file_sha1(it.path)] = it
                except OSError:
                    pass
            res = modrinth.updates(list(by_hash), loaders=loaders, game_versions=gvs)
            found = {}
            for h, ver in res.items():
                it = by_hash.get(h)
                nf = modrinth.pick_file(ver)
                new_sha = (nf or {}).get("hashes", {}).get("sha1")
                if it and nf and new_sha and new_sha != h:
                    found[it.name] = {"url": nf["url"], "filename": nf["filename"],
                                      "sha1": new_sha}
            return found

        self.ctl._run(work, self._apply_updates, lambda _m: None)

    def _apply_updates(self, found: dict) -> None:
        self._updates = found
        self._render_installed()

    def _toggle(self, item) -> None:
        mods_mgr.set_enabled(item.path, not item.enabled)
        self._render_installed()

    def _ask_delete(self, item) -> None:
        dlg = ConfirmDialog(self.window(), f"Remove {self.kind[:-1]}",
                            f"Delete '{item.name}' from disk? This cannot be undone.")
        dlg.confirmed.connect(lambda: (mods_mgr.delete(item.path),
                                       self._updates.pop(item.name, None),
                                       self._render_installed()))
        dlg.show()

    def _on_installed_click(self, item) -> None:
        # Bấm vào hàng có bản mới -> cập nhật ngay mod đó.
        if item.name in self._updates:
            self._update_one(item)

    def _update_one(self, item) -> None:
        nf = self._updates.get(item.name)
        if not nf:
            return
        self.ctl.window.set_status(f"Updating {item.name}…")
        gd = self._game_dir()
        self.ctl._run(lambda: mods_mgr.update_item(gd, self.kind, item, nf),
                      lambda _p: self._updated(item.name),
                      lambda m: self.ctl.window.set_status(f"Update failed: {m}"))

    def _updated(self, name: str) -> None:
        self._updates.pop(name, None)
        self.ctl.window.set_status(f"Updated {name}.")
        self._render_installed()

    def _update_all(self) -> None:
        if not self._updates:
            return
        self.ctl.window.set_status("Updating all…")
        gd = self._game_dir()
        by_name = {it.name: it for it in self._items}
        jobs = [(by_name[n], nf) for n, nf in self._updates.items() if n in by_name]

        def work():
            for it, nf in jobs:
                mods_mgr.update_item(gd, self.kind, it, nf)
            return len(jobs)

        self.ctl._run(work, self._all_updated,
                      lambda m: self.ctl.window.set_status(f"Update failed: {m}"))

    def _all_updated(self, n: int) -> None:
        self._updates = {}
        self.ctl.window.set_status(f"Updated {n} item(s).")
        self.refresh()

    # ---- Browse ----

    def _mc_version(self, version_id: str) -> str:
        """Phiên bản Minecraft gốc từ id (bản Fabric -> lấy mc, vd
        'fabric-loader-0.16-1.20.1' -> '1.20.1')."""
        match = next((v for v in self.ctl.installer.installed_versions()
                      if v["id"] == version_id), None)
        if match and match.get("parent"):
            return match["parent"]
        if version_id.startswith("fabric-loader-"):
            parts = version_id[len("fabric-loader-"):].split("-", 1)
            if len(parts) == 2:
                return parts[1]
        return version_id

    def _target(self):
        """(loaders, game_versions) để lọc Modrinth theo ĐÚNG instance đang chọn
        trên trang này — mod tải về hợp phiên bản của modpack đó."""
        inst = self._instance or self.ctl.active_instance()
        game_versions = [self._mc_version(inst.version)] if inst else None
        loaders = [self._loader] if self.is_mod else None
        return loaders, game_versions

    PER_PAGE = 20

    def _go_page(self, page: int) -> None:
        self._page = max(1, page)
        self._load(reset=False)

    def _load(self, reset: bool = True) -> None:
        """Nạp một trang kết quả: có chữ thì tìm, rỗng thì discover mod hot."""
        if reset:
            self._page = 1
        q = self.search.text().strip()
        self.results.empty_text = "Loading from Modrinth…"
        self.results.set_page([], self._page, 1, {})
        loaders, gvs = self._target()
        offset = (self._page - 1) * self.PER_PAGE
        self.ctl._run(
            lambda: modrinth.search_page(q, self.project_type, loaders=loaders,
                                         game_versions=gvs, index=self._index,
                                         limit=self.PER_PAGE, offset=offset),
            self._show_results,
            self._search_failed,
        )

    def _search_failed(self, msg: str) -> None:
        self.results.empty_text = f"Couldn't reach Modrinth: {msg}"
        self.results.set_page([], self._page, 1, {})

    def _show_results(self, res: dict) -> None:
        self._hits = res.get("hits", [])
        self._total = res.get("total", len(self._hits))
        self.results.empty_text = "Nothing matched on Modrinth."
        self._render_results()
        self._load_icons()

    def _result_badges(self) -> dict:
        b = {}
        for h in self._hits:
            slug = h.get("slug") or h.get("project_id")
            if slug in self._busy:
                b[slug] = "…"
            elif slug in self._done:
                b[slug] = "ADDED"
        return b

    def _pages(self) -> int:
        import math
        return max(1, math.ceil(self._total / self.PER_PAGE)) if self._total else 1

    def _render_results(self) -> None:
        self.results.set_page(self._hits, self._page, self._pages(), self._result_badges())

    def _load_icons(self) -> None:
        """Tải ảnh preview cho từng kết quả (nền, có cache theo URL)."""
        for h in self._hits:
            url = h.get("icon_url")
            if not url or url in self._icons or url in self._icon_wanted:
                continue
            self._icon_wanted.add(url)
            self.ctl._run(
                lambda u=url: modrinth.fetch_icon(u),
                lambda data, u=url: self._icon_ready(u, data),
                lambda _m, u=url: self._icon_wanted.discard(u),
            )

    def _icon_ready(self, url: str, data: bytes) -> None:
        self._icon_wanted.discard(url)
        pm = QPixmap()
        if pm.loadFromData(data):
            self._icons[url] = pm
            self.results.set_state(self._icons, self._result_badges())

    def _install(self, hit) -> None:
        slug = hit.get("slug") or hit.get("project_id")
        if slug in self._busy or slug in self._done:
            return
        self._busy.add(slug)
        self._render_results()
        self.ctl.window.set_status(f"Installing {hit.get('title', slug)}…")
        loaders, gvs = self._target()
        game_dir = self._game_dir()          # cố định instance đích trước khi chạy nền
        kind = self.kind
        title = hit.get("title", slug)

        def work():
            # Cài mod + toàn bộ dependency BẮT BUỘC (đệ quy có giới hạn).
            seen: set = set()
            count = 0
            stack = [(slug, 0)]
            while stack:
                sl, depth = stack.pop()
                if not sl or sl in seen or depth > 4:
                    continue
                seen.add(sl)
                ver = modrinth.best_version(sl, loaders=loaders, game_versions=gvs)
                if not ver:
                    if depth == 0:
                        raise RuntimeError("no compatible version for your Minecraft/loader")
                    continue
                f = modrinth.pick_file(ver)
                if f:
                    mods_mgr.install_file(game_dir, kind, url=f["url"],
                                          filename=f["filename"],
                                          sha1=f.get("hashes", {}).get("sha1"))
                    count += 1
                for dep in ver.get("dependencies", []):
                    if dep.get("dependency_type") == "required" and dep.get("project_id"):
                        stack.append((dep["project_id"], depth + 1))
            return count

        self.ctl._run(work,
                      lambda n: self._installed(slug, title, n),
                      lambda msg: self._install_failed(slug, hit, msg))

    def _installed(self, slug: str, title: str, count: int = 1) -> None:
        self._busy.discard(slug)
        self._done.add(slug)
        self._render_results()
        extra = f" + {count - 1} dependency(ies)" if count > 1 else ""
        self.ctl.window.set_status(f"Added {title}{extra} — see the Installed tab.")

    def _install_failed(self, slug: str, hit, msg: str) -> None:
        self._busy.discard(slug)
        self._render_results()
        self.ctl.window.set_status(f"Couldn't add {hit.get('title', slug)}: {msg}")


class ModsPage(ContentLibraryPage):
    heading = "Mods"
    kind = "mods"
    is_mod = True
    project_type = "mod"


class ResourcePacksPage(ContentLibraryPage):
    heading = "Resource Packs"
    kind = "resourcepacks"
    is_mod = False
    project_type = "resourcepack"


class ShaderPacksPage(ContentLibraryPage):
    heading = "Shaders"
    kind = "shaderpacks"
    is_mod = False
    project_type = "shader"


# ---------- trang chi tiết một instance (kiểu Modrinth) ----------

_WROW = 66   # chiều cao một hàng world


class WorldsView(QWidget):
    """Danh sách thế giới của instance: icon + tên + lần chơi + dung lượng + chế độ.

    Xem nhanh ngay trong launcher, khỏi phải mở thư mục saves. Bấm một world để
    mở thư mục của riêng nó.
    """

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.instance = None
        self._worlds: list = []
        self._scroll = 0
        self._hover = -1
        self._rects: list = []
        self.setMouseTracking(True)

    def set_instance(self, inst) -> None:
        self.instance = inst
        self.refresh()

    def refresh(self) -> None:
        from ..worlds import list_worlds
        self._worlds = []
        if self.instance is not None:
            for w in list_worlds(self.ctl.instance_dir(self.instance) / "saves"):
                img = None
                if w.get("icon"):
                    qi = QImage()
                    if qi.loadFromData(w["icon"]):
                        img = qi
                w["_img"] = img
                self._worlds.append(w)
        self._scroll = 0
        self.update()

    @staticmethod
    def _fmt_last(ms: int) -> str:
        import datetime
        if not ms:
            return "never"
        try:
            return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
        except (OverflowError, OSError, ValueError):
            return "never"

    def wheelEvent(self, e):  # noqa: N802
        maxs = max(0, len(self._worlds) * _WROW - self.height() + 24)
        self._scroll = min(maxs, max(0, self._scroll - e.angleDelta().y()))
        self.update()

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        h = next((i for i, (r, _) in enumerate(self._rects) if r.contains(pos)), -1)
        if h != self._hover:
            self._hover = h
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        for r, folder in self._rects:
            if r.contains(pos) and self.instance:
                self.ctl.open_path(self.ctl.instance_dir(self.instance) / "saves" / folder)
                return

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._rects = []
        if not self._worlds:
            p.setFont(ui_font(11))
            p.setPen(TEXT_DIM)
            p.drawText(self.rect(), Qt.AlignCenter,
                       tr("No worlds yet — press PLAY to create one, or Import World."))
            p.end()
            return
        w = self.width()
        for i, world in enumerate(self._worlds):
            y = 6 - self._scroll + i * _WROW
            if y + _WROW < 0 or y > self.height():
                continue
            row = QRect(4, y, w - 8, _WROW - 8)
            self._rects.append((row, world["folder"]))
            if i == self._hover:
                p.setBrush(QColor(255, 255, 255, 20)); p.setPen(Qt.NoPen)
                p.drawRoundedRect(row, 8, 8)
            # icon 48×48 bo góc (hoặc ô mặc định)
            ic = QRect(row.left() + 10, row.top() + 5, 48, 48)
            p.save()
            p.setClipRect(ic)
            if world.get("_img") is not None:
                p.drawImage(ic, world["_img"])
            else:
                p.fillRect(ic, QColor(40, 60, 90, 160))
                p.setPen(QColor(200, 220, 255, 120)); p.setFont(ui_font(16, bold=True))
                p.drawText(ic, Qt.AlignCenter, "🌍")
            p.restore()
            p.setPen(QColor(255, 255, 255, 40)); p.setBrush(Qt.NoBrush)
            p.drawRect(ic)
            # tên + phụ đề
            tx = ic.right() + 14
            p.setFont(ui_font(12, bold=True)); p.setPen(TEXT)
            title = world["title"] + ("  ⚠ Hardcore" if world.get("hardcore") else "")
            p.drawText(QRect(tx, row.top() + 6, row.right() - tx - 8, 20),
                       Qt.AlignLeft | Qt.AlignVCenter, title)
            bits = [self._fmt_last(world.get("last", 0)), human_size(world.get("size", 0))]
            if world.get("mode"):
                bits.append(world["mode"])
            if world.get("version"):
                bits.append(world["version"])
            p.setFont(ui_font(9)); p.setPen(TEXT_DIM)
            p.drawText(QRect(tx, row.top() + 28, row.right() - tx - 8, 18),
                       Qt.AlignLeft | Qt.AlignVCenter, "  ·  ".join(bits))
            p.setFont(ui_font(8)); p.setPen(TEXT_FAINT)
            p.drawText(QRect(tx, row.top() + 44, row.right() - tx - 8, 14),
                       Qt.AlignLeft | Qt.AlignVCenter, world["folder"])
        p.end()


class InstancePage(Page):
    """Mở khi nhấn vào một instance: quản lý mọi thứ của riêng nó tại một nơi."""

    heading = ""
    CONTENT = [("Mods", "mods", "mod", True),
               ("Resource Packs", "resourcepacks", "resourcepack", False),
               ("Shaders", "shaderpacks", "shader", False)]

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.instance = None
        self.back_btn = AeroButton("‹  BACK", self, height=28, tone="neutral")
        self.back_btn.clicked.connect(lambda: self.ctl.go("installations"))
        self.play_btn = AeroButton("PLAY", self, height=42, arrow=True)
        self.play_btn.clicked.connect(self.ctl.toggle_play)
        self.edit_btn = AeroButton("EDIT", self, height=28, tone="neutral")
        self.edit_btn.clicked.connect(
            lambda: self.ctl.edit_instance(self.instance.name) if self.instance else None)

        # Chỉ hiện với instance legacy (≤1.12.2) — bản mới dùng Sodium/Iris.
        self.optifine_btn = AeroButton("＋ OptiFine", self, height=28, tone="neutral")
        self.optifine_btn.clicked.connect(
            lambda: self.ctl.install_optifine(self.instance) if self.instance else None)
        self.optifine_btn.hide()

        # Bật "shared skins" (CustomSkinLoader) — chỉ instance có loader (Fabric/Forge).
        self.shared_btn = AeroButton("Shared skins", self, height=28, tone="neutral")
        self.shared_btn.clicked.connect(
            lambda: self.ctl.enable_shared_skins(self.instance) if self.instance else None)
        self.shared_btn.hide()

        # Nhập world: chọn file .zip, hoặc mở thư mục saves để kéo-thả (cũng kéo-thả
        # .zip thẳng vào trang này được — xem dropEvent).
        self.import_btn = AeroButton("＋ IMPORT WORLD", self, height=28, tone="neutral")
        self.import_btn.clicked.connect(
            lambda: self.ctl.import_world(self.instance) if self.instance else None)
        self.saves_btn = AeroButton("SAVES FOLDER", self, height=28, tone="neutral")
        self.saves_btn.clicked.connect(
            lambda: self.ctl.open_saves_folder(self.instance) if self.instance else None)
        self.setAcceptDrops(True)

        self.tabs = TabBar([c[0] for c in self.CONTENT] + ["Worlds", "Logs"], self)
        self.tabs.changed.connect(self._tab)

        self.content = ContentLibraryPage(ctl, self)
        self.content.enter_embedded(None)
        self.worlds = WorldsView(ctl, self)
        self.worlds.hide()
        self.logs = QTextBrowser(self)
        self.logs.setStyleSheet(TEXT_QSS)
        self.logs.setFont(QFont("monospace", 8))
        self.logs.hide()

    def open(self, instance) -> None:
        self.instance = instance
        self.content.set_instance(instance)
        self.worlds.set_instance(instance)
        from .. import optifine
        self.optifine_btn.setVisible(
            optifine.is_legacy(optifine.mc_from_version_id(instance.version)))
        v = (instance.version or "").lower()
        self.shared_btn.setVisible(any(k in v for k in ("fabric", "forge", "neoforge")))
        self._relayout_actions()
        self.tabs.current = 0
        self._tab(0)

    def _relayout_actions(self) -> None:
        # Xếp các nút hành động từ phải sang; Import World / Saves luôn hiện.
        x = self.width() - 20
        for btn, w in ((self.import_btn, 150), (self.saves_btn, 128),
                       (self.optifine_btn, 128), (self.shared_btn, 128)):
            if not btn.isHidden():          # ý định hiện (không phụ thuộc parent đã show)
                x -= w
                btn.setGeometry(x, 101, w, 28)
                btn.raise_()                # nổi lên TRÊN thanh tab, không thì tab nuốt click
                x -= 8

    def refresh(self) -> None:
        self.ctl._update_play_button()
        n = len(self.CONTENT)
        if self.tabs.current < n:
            self.content.refresh()
        elif self.tabs.current == n:
            self.worlds.refresh()

    def _tab(self, i: int) -> None:
        self.tabs.current = i
        self.tabs.update()
        n = len(self.CONTENT)
        is_worlds, is_logs = i == n, i == n + 1
        self.content.setVisible(i < n)
        self.worlds.setVisible(is_worlds)
        self.logs.setVisible(is_logs)
        if is_worlds:
            self.worlds.refresh()
        elif is_logs:
            self.logs.setPlainText("".join(self.ctl._log_lines)
                                   or "No log yet — press PLAY to start the game.")
        else:
            self.content.configure(*self.CONTENT[i][1:])

    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        # Cả header nằm DƯỚI dải kéo cửa sổ (cao 46px) — nếu không, dải kéo sẽ
        # nuốt click và các nút không hoạt động; cũng để cách xa nút caption.
        top = 54
        self.back_btn.setGeometry(24, top, 94, 32)
        self.play_btn.setGeometry(w - 178, top - 4, 150, 40)
        self.edit_btn.setGeometry(w - 288, top, 96, 32)
        self.tabs.setGeometry(24, 102, w - 48, 30)
        self._relayout_actions()                              # nút ở cạnh phải hàng tab
        self.content.setGeometry(0, 138, w, h - 138)
        self.worlds.setGeometry(24, 142, w - 48, h - 166)
        self.logs.setGeometry(24, 142, w - 48, h - 166)

    # ---- kéo-thả file .zip world thẳng vào trang để nhập ----
    def _dropped_zips(self, e):
        return [u.toLocalFile() for u in e.mimeData().urls()
                if u.toLocalFile().lower().endswith(".zip")]

    def dragEnterEvent(self, e):  # noqa: N802
        if self.instance and self._dropped_zips(e):
            e.acceptProposedAction()

    def dropEvent(self, e):  # noqa: N802
        if not self.instance:
            return
        for f in self._dropped_zips(e):
            self.ctl._do_import_world(self.instance, f)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        if self.instance:
            p.setFont(ui_font(13, bold=True))
            p.setPen(TEXT)
            p.drawText(QRect(130, 50, self.width() - 460, 24),
                       Qt.AlignLeft | Qt.AlignVCenter, self.instance.name)
            p.setFont(ui_font(8))
            p.setPen(TEXT_DIM)
            pt = self.instance.playtime_sec
            extra = f"  ·  played {pt // 3600}h {(pt % 3600) // 60}m" if pt else ""
            p.drawText(QRect(130, 74, self.width() - 460, 16),
                       Qt.AlignLeft | Qt.AlignVCenter, self.instance.version + extra)
        # đường kẻ dưới header
        p.setPen(QPen(QColor(255, 255, 255, 24), 1))
        p.drawLine(24, 136, self.width() - 24, 136)
        p.end()


# ---------- skin ----------

def _reltime(ts) -> str:
    """'2d ago' — nhận ts theo giây (lịch sử cục bộ) hoặc mili-giây (backend)."""
    import time
    ts = float(ts)
    if ts > 1e12:
        ts /= 1000.0
    secs = max(0.0, time.time() - ts)
    for div, unit in ((86400, "d"), (3600, "h"), (60, "m")):
        n = int(secs // div)
        if n >= 1:
            return f"{n}{unit} ago"
    return "just now"


class SkinsPage(Page):
    heading = "Skin"

    TILE_W = 96      # tile khổ dọc kiểu NameMC: đủ chỗ render cả người
    TILE_H = 132
    GAP = 14

    def __init__(self, ctl, parent=None):
        super().__init__(ctl, parent)
        self.skin: QImage | None = None          # skin đang hiển thị (preview)
        self.note = ""
        self._recent: list[dict] = []            # 5 skin gần nhất (từ skins.recent())
        self._defaults: list[dict] = []          # skin mặc định (Steve/Alex…)
        self._capes: list[dict] = []             # cape sở hữu (tài khoản premium)
        self._cape_img: QImage | None = None     # cape đang mặc, để render 3D
        self._variant = "classic"                # kiểu tay đang chọn: classic/slim
        self._tiles: list[tuple[QRect, str, str, str]] = []  # (rect, action, path, variant)
        self._hover = -1
        self._yaw = -28.0        # góc xoay preview 3D (kéo chuột để đổi)
        self._pitch = 12.0
        self._preview_rect = QRect()
        self._drag_from = None
        self._img_cache: dict = {}    # path -> QImage (tránh load lại đĩa mỗi frame)
        self.setMouseTracking(True)

    def _img(self, path: str) -> QImage:
        im = self._img_cache.get(path)
        if im is None:
            im = QImage()
            im.load(path)
            self._img_cache[path] = im
        return im

    def refresh(self) -> None:
        from .. import skins
        account = self.ctl.current_account()
        self.skin, self.note = None, ""
        self._recent = skins.recent(account.username if account else "")
        if account is None:
            self.note = "No accounts yet — add one on the Home page."
        elif self._recent:
            # ưu tiên hiện skin đã áp gần nhất (chạy được cả offline)
            img = QImage()
            if img.load(self._recent[0]["path"]):
                self.skin = img
                self._variant = self._recent[0].get("variant", "classic")
        if self.skin is None and account and account.kind == "msa" and account.skin_url:
            self.ctl.load_skin(account.skin_url, self._got)
            self.note = "Loading skin…"
        if not self._defaults:
            self.ctl.ensure_default_skins(self._got_defaults)
        # Lịch sử skin THEO TÀI KHOẢN từ backend (đi theo tài khoản, xuyên máy) —
        # thay cho danh sách cục bộ khi lấy được.
        if account:
            self.ctl.load_account_skins(self._got_account_skins)
            self.ctl.load_capes(self._got_capes)
        self.update()

    def _got_capes(self, items) -> None:
        self._capes = items or []
        self._cape_img = None
        active = next((c for c in self._capes if c.get("state") == "ACTIVE"), None)
        if active and active.get("path"):
            img = self._img(active["path"])
            if not img.isNull():
                self._cape_img = img
        self.update()

    def _got_defaults(self, items) -> None:
        self._defaults = items or []
        # Tài khoản chưa có skin/lịch sử -> hiện tạm Steve để preview không trống.
        if self.skin is None and self._defaults:
            img = QImage()
            if img.load(self._defaults[0]["path"]):
                self.skin = img
        self.update()

    def _got_account_skins(self, items) -> None:
        if items:
            self._recent = items
            img = QImage()
            if img.load(items[0]["path"]):
                self.skin = img
                self._variant = items[0].get("variant", "classic")
                self.note = ""
        self.update()

    def _got(self, data: bytes | None) -> None:
        if data:
            img = QImage()
            if img.loadFromData(data):
                self.skin = img
                self.note = ""
        self.update()

    # ---------- vẽ mảnh skin ----------

    @staticmethod
    def _part(p, img, sx, sy, sw, sh, dx, dy, scale):
        p.drawImage(QRectF(dx, dy, sw * scale, sh * scale), img, QRectF(sx, sy, sw, sh))

    def _draw_body(self, p, img, ox, oy, scale, slim=False):
        s = scale
        legacy = img.height() < 64                # skin 64x32 cũ không có tay/chân trái riêng
        aw = 3 if slim else 4                     # tay slim rộng 3px, classic 4px
        self._part(p, img, 8, 8, 8, 8, ox + 4 * s, oy, s)                 # đầu
        self._part(p, img, 20, 20, 8, 12, ox + 4 * s, oy + 8 * s, s)      # thân
        self._part(p, img, 44, 20, aw, 12, ox + 12 * s, oy + 8 * s, s)    # tay phải
        la_x, la_y = (44, 20) if legacy else (36, 52)
        self._part(p, img, la_x, la_y, aw, 12,
                   ox + (1 if slim else 0) * s, oy + 8 * s, s)            # tay trái
        self._part(p, img, 4, 20, 4, 12, ox + 4 * s, oy + 20 * s, s)      # chân phải
        ll_x, ll_y = (4, 20) if legacy else (20, 52)
        self._part(p, img, ll_x, ll_y, 4, 12, ox + 8 * s, oy + 20 * s, s) # chân trái
        self._part(p, img, 40, 8, 8, 8, ox + 4 * s, oy, s)               # lớp mũ

    def _draw_head(self, p, img, rect: QRect):
        s = rect.width() / 8.0
        p.drawImage(QRectF(rect.left(), rect.top(), 8 * s, 8 * s), img, QRectF(8, 8, 8, 8))
        p.drawImage(QRectF(rect.left(), rect.top(), 8 * s, 8 * s), img, QRectF(40, 8, 8, 8))

    # ---------- tương tác ----------

    def mouseMoveEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        if self._drag_from is not None:                # đang xoay preview
            self._yaw += (pos.x() - self._drag_from.x()) * 0.6
            self._pitch = max(-32.0, min(32.0, self._pitch - (pos.y() - self._drag_from.y()) * 0.5))
            self._drag_from = pos
            self.update()
            return
        hit = next((i for i, t in enumerate(self._tiles) if t[0].contains(pos)), -1)
        if hit >= 0:
            self.setCursor(Qt.PointingHandCursor)
        elif self._preview_rect.contains(pos) and self.skin is not None:
            self.setCursor(Qt.OpenHandCursor)          # gợi ý "kéo để xoay"
        else:
            self.setCursor(Qt.ArrowCursor)
        if hit != self._hover:
            self._hover = hit
            self.update()

    def mousePressEvent(self, e):  # noqa: N802
        pos = e.position().toPoint()
        for rect, action, path, variant in self._tiles:
            if rect.contains(pos):
                if action == "toggle":
                    self._variant = variant
                    self.update()
                elif action == "add":
                    self.ctl.pick_and_apply_skin(self._variant)
                elif action == "edit":
                    self.ctl.open_skin_editor(self.skin, self._variant)
                elif action == "cape":
                    self.ctl.apply_cape(path or None)
                else:  # recent | default
                    self._variant = variant
                    self.ctl.apply_skin_file(path, variant)
                return
        if self._preview_rect.contains(pos) and self.skin is not None:
            self._drag_from = pos                      # bắt đầu xoay
            self.setCursor(Qt.ClosedHandCursor)

    def mouseReleaseEvent(self, e):  # noqa: N802
        if self._drag_from is not None:
            self._drag_from = None
            self.setCursor(Qt.OpenHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self._tiles = []
        account = self.ctl.current_account()

        # ----- cột trái: thẻ kính + tên + preview -----
        panel = QRectF(24, 58, 268, self.height() - 74)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(panel, 10, 10)
        p.setBrush(gloss_gradient(90, 0.4))
        p.drawRoundedRect(panel, 10, 10)
        if account:
            name = account.username
            p.setFont(ui_font(11, bold=True))
            fm = p.fontMetrics()
            bw = fm.horizontalAdvance(name) + 26
            badge = QRectF(panel.center().x() - bw / 2, panel.top() + 16, bw, 26)
            p.setBrush(QColor(0, 0, 0, 90))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(badge, 5, 5)
            p.setPen(TEXT)
            p.drawText(badge, Qt.AlignCenter, name)
        # vùng preview 3D (kéo chuột để xoay)
        self._preview_rect = QRect(int(panel.left()), int(panel.top() + 52),
                                   int(panel.width()), int(panel.height() - 100))
        if self.skin is not None and self.skin.width() >= 64:
            from . import skin3d
            skin3d.render(p, self.skin, self._preview_rect.center().x(),
                          self._preview_rect.center().y(), 8.0,
                          self._yaw, self._pitch, self._variant == "slim",
                          cape=self._cape_img)

        # toggle Classic / Slim ở đáy thẻ trái
        self._paint_variant_toggle(p, panel)

        # ----- cột phải: Saved skins -----
        rx = 316
        p.setFont(ui_font(9, bold=True))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(rx, 62, 300, 18), Qt.AlignLeft | Qt.AlignVCenter, "SAVED SKINS")
        y = 88
        add = QRect(rx, y, self.TILE_W, self.TILE_H)
        self._paint_add_tile(p, add, self._hover == len(self._tiles))
        self._tiles.append((add, "add", "", ""))
        edit = QRect(rx + self.TILE_W + self.GAP, y, self.TILE_W, self.TILE_H)
        self._paint_edit_tile(p, edit, self._hover == len(self._tiles))
        self._tiles.append((edit, "edit", "", ""))
        x = edit.right() + self.GAP
        current_path = self._recent[0]["path"] if self._recent else None
        for it in self._recent:
            tile = QRect(x, y, self.TILE_W, self.TILE_H)
            self._paint_skin_tile(p, tile, it, it["path"] == current_path,
                                  self._hover == len(self._tiles))
            self._tiles.append((tile, "recent", it["path"], it.get("variant", "classic")))
            x += self.TILE_W + self.GAP

        # ----- Default skins -----
        y2 = y + self.TILE_H + 34
        if self._defaults:
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(rx, y2, 300, 18), Qt.AlignLeft | Qt.AlignVCenter, "DEFAULT SKINS")
            xy = y2 + 26
            x = rx
            for d in self._defaults:
                tile = QRect(x, xy, self.TILE_W, self.TILE_H)
                self._paint_skin_tile(p, tile, d, d["path"] == current_path,
                                      self._hover == len(self._tiles))
                self._tiles.append((tile, "default", d["path"], d.get("variant", "classic")))
                x += self.TILE_W + self.GAP

        # ----- Capes (chỉ tài khoản premium sở hữu cape) -----
        if self._capes:
            y3 = y2 + 26 + self.TILE_H + 34
            p.setFont(ui_font(9, bold=True))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(rx, y3, 300, 18), Qt.AlignLeft | Qt.AlignVCenter, "CAPES")
            cyr = y3 + 26
            x = rx
            active_id = next((c["id"] for c in self._capes if c.get("state") == "ACTIVE"), None)
            none_tile = QRect(x, cyr, self.TILE_W, self.TILE_H)
            self._paint_cape_tile(p, none_tile, None, active_id is None,
                                  self._hover == len(self._tiles))
            self._tiles.append((none_tile, "cape", "", ""))
            x += self.TILE_W + self.GAP
            for c in self._capes:
                tile = QRect(x, cyr, self.TILE_W, self.TILE_H)
                self._paint_cape_tile(p, tile, c, c["id"] == active_id,
                                      self._hover == len(self._tiles))
                self._tiles.append((tile, "cape", c["id"], ""))
                x += self.TILE_W + self.GAP

        if self.note:
            p.setFont(ui_font(9))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(rx, self.height() - 70, self.width() - rx - 24, 40),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.note)
        p.end()

    def _paint_cape_tile(self, p, rect: QRect, cape, active: bool, hovered: bool):
        self._tile_bg(p, rect, hovered, active)
        if cape and cape.get("path"):
            img = self._img(cape["path"])
            if not img.isNull() and img.width() >= 64:
                f = max(1, img.width() // 64)
                th = rect.height() - 42
                tw = th * 10.0 / 16.0
                p.setRenderHint(QPainter.SmoothPixmapTransform, False)
                p.drawImage(QRectF(rect.center().x() - tw / 2, rect.top() + 14, tw, th),
                            img, QRectF(1 * f, 1 * f, 10 * f, 16 * f))
            label = cape.get("alias", "")
        else:
            cx, cy = rect.center().x(), rect.center().y() - 8
            p.setPen(QPen(TEXT_DIM, 3))
            p.drawLine(cx - 13, cy - 13, cx + 13, cy + 13)
            label = "None"
        p.setFont(ui_font(7))
        p.setPen(TEXT if active else TEXT_FAINT)
        p.drawText(QRect(rect.left(), rect.bottom() - 18, rect.width(), 14),
                   Qt.AlignCenter, label)

    def _paint_variant_toggle(self, p, panel: QRectF) -> None:
        w, h = 88, 26
        gap = 8
        total = w * 2 + gap
        x0 = panel.center().x() - total / 2
        y0 = panel.bottom() - 42
        for i, (label, variant) in enumerate((("Classic", "classic"), ("Slim", "slim"))):
            r = QRect(int(x0 + i * (w + gap)), int(y0), w, h)
            on = self._variant == variant
            hovered = self._hover == len(self._tiles)
            p.setPen(Qt.NoPen)
            if on:
                p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 210))
            else:
                p.setBrush(QColor(255, 255, 255, 30 if hovered else 18))
            p.drawRoundedRect(QRectF(r), 5, 5)
            p.setFont(ui_font(9, bold=on))
            p.setPen(QColor(255, 255, 255) if on else TEXT_DIM)
            p.drawText(r, Qt.AlignCenter, label)
            self._tiles.append((r, "toggle", "", variant))

    def _tile_bg(self, p, rect: QRect, hovered: bool, selected: bool):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 26 if hovered else 16))
        p.drawRoundedRect(QRectF(rect), 8, 8)
        if selected:
            p.setBrush(QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 40))
            p.drawRoundedRect(QRectF(rect), 8, 8)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(ACCENT, 2))
            p.drawRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 8, 8)

    def _paint_add_tile(self, p, rect: QRect, hovered: bool):
        self._tile_bg(p, rect, hovered, False)
        cx, cy = rect.center().x(), rect.center().y() - 8
        p.setPen(QPen(TEXT_DIM, 3))
        p.drawLine(cx - 12, cy, cx + 12, cy)
        p.drawLine(cx, cy - 12, cx, cy + 12)
        p.setFont(ui_font(8))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(rect.left(), rect.bottom() - 26, rect.width(), 18),
                   Qt.AlignCenter, "Add a skin")

    def _paint_edit_tile(self, p, rect: QRect, hovered: bool):
        self._tile_bg(p, rect, hovered, False)
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        cx, cy = rect.center().x(), rect.center().y() - 8
        col = TEXT if hovered else TEXT_DIM
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(cx, cy)
        p.rotate(45)                                   # cây bút nghiêng 45°, mũi hướng xuống
        p.setPen(Qt.NoPen)
        # thân bút
        p.setBrush(col)
        p.drawRoundedRect(QRectF(-4, -13, 8, 18), 1.5, 1.5)
        # phần gỗ vót nhọn (tam giác) + ngòi
        p.drawPolygon(QPolygonF([QPointF(-4, 5), QPointF(4, 5), QPointF(0, 13)]))
        p.setBrush(QColor(18, 28, 44))                 # ngòi than sẫm
        p.drawPolygon(QPolygonF([QPointF(-1.6, 9.5), QPointF(1.6, 9.5), QPointF(0, 13)]))
        # cục tẩy trên đỉnh + đai kim loại (vạch ngăn cách)
        p.setBrush(col)
        p.drawRoundedRect(QRectF(-4, -15, 8, 3.5), 1.5, 1.5)
        p.setPen(QPen(QColor(18, 28, 44), 1.2))
        p.drawLine(QPointF(-4, -10.5), QPointF(4, -10.5))   # đai dưới cục tẩy
        p.drawLine(QPointF(-4, 5), QPointF(4, 5))           # ranh sơn/gỗ
        p.restore()
        p.setFont(ui_font(8))
        p.setPen(TEXT_FAINT)
        p.drawText(QRect(rect.left(), rect.bottom() - 26, rect.width(), 18),
                   Qt.AlignCenter, "Draw skin")

    def _paint_skin_tile(self, p, rect: QRect, item: dict, selected: bool, hovered: bool):
        self._tile_bg(p, rect, hovered, selected)
        img = self._img(item["path"])
        if not img.isNull() and img.width() >= 64:
            scale = 3                                   # render cả người kiểu NameMC
            slim = item.get("variant") == "slim"
            ox = int(rect.center().x() - 8 * scale)
            self._draw_body(p, img, ox, rect.top() + 10, scale, slim)
        ts = item.get("ts")
        if ts:
            p.setFont(ui_font(7))
            p.setPen(TEXT_FAINT)
            p.drawText(QRect(rect.left(), rect.bottom() - 18, rect.width(), 14),
                       Qt.AlignCenter, _reltime(ts))


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

        # Đăng nhập Microsoft luôn dùng client ID của launcher (đã duyệt) — người
        # chơi không cần và không được đổi, nên không có ô nhập ở đây nữa.
        self.snapshots = AeroToggle(s.show_snapshots, self)
        self.snapshots.toggled.connect(self._set_snapshots)
        self.close_on_launch = AeroToggle(s.close_on_launch, self)
        self.close_on_launch.toggled.connect(self._set_close)
        self.check_updates = AeroToggle(s.check_updates, self)
        self.check_updates.toggled.connect(self._set_check_updates)

        self.open_dir = AeroButton("OPEN GAME FOLDER", self, height=32, tone="neutral")
        self.open_dir.clicked.connect(lambda: self.ctl.open_path(self.ctl.settings.game_path))
        self.doctor = AeroButton("CHECK INSTALL", self, height=32, tone="neutral")
        self.doctor.clicked.connect(self.ctl.run_doctor)
        self.bg_btn = AeroButton("CHANGE BACKGROUND", self, height=32, tone="neutral")
        self.bg_btn.clicked.connect(self.ctl.pick_background)

        self.lang_btn = AeroButton(language_name(language()), self, height=30, tone="neutral")
        self.lang_btn.clicked.connect(self._open_language)

    def _open_language(self) -> None:
        g = self.lang_btn.geometry()
        from .window import SIDEBAR_W
        anchor = QRect(g)
        anchor.translate(SIDEBAR_W, 0)
        self.ctl.open_language_menu(anchor)

    def retranslate(self) -> None:
        self.lang_btn.setText(language_name(language()))
        self.update()

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

    def _set_snapshots(self, on: bool) -> None:
        self.ctl.settings.show_snapshots = on
        self.ctl.settings.save()

    def _set_close(self, on: bool) -> None:
        self.ctl.settings.close_on_launch = on
        self.ctl.settings.save()

    def _set_check_updates(self, on: bool) -> None:
        self.ctl.settings.check_updates = on
        self.ctl.settings.save()

    def resizeEvent(self, event) -> None:  # noqa: N802
        w = min(560, self.width() - 52)
        self.mem.setGeometry(26, 60, w, 26)
        self.game_dir.setGeometry(26, 142, w, 32)
        self.java.setGeometry(26, 218, w, 32)
        self.snapshots.setGeometry(26, 282, 44, 22)
        self.close_on_launch.setGeometry(26, 322, 44, 22)
        self.check_updates.setGeometry(26, 362, 44, 22)
        self.lang_btn.setGeometry(26, 422, 200, 30)
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
        label(114, tr("Game folder"))
        label(190, tr("Java path"))
        label(398, tr("Language"))
        p.setFont(ui_font(9))
        p.setPen(TEXT)
        p.drawText(QRect(84, 280, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Show snapshots")
        p.drawText(QRect(84, 320, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Close launcher when the game starts")
        p.drawText(QRect(84, 360, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Check for updates on startup")

        warn = self.ctl.settings.memory_mb > self._max_memory() * 0.9
        if warn:
            p.setFont(ui_font(8))
            p.setPen(DEGRADED)
            p.drawText(QRect(26, 90, self.width() - 52, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       "Setting near all your RAM can freeze the system.")
        p.end()
