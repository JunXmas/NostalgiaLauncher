"""Các trang nội dung nằm giữa thanh trên và thanh dưới."""

from __future__ import annotations

import os

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLineEdit, QTextBrowser, QWidget

from .. import mods as mods_mgr
from .. import modrinth
from ..settings import client_id as resolve_client_id, save_client_id
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

        self.results = ListView(self, empty_text="Loading popular picks from Modrinth…")
        self.results.activated.connect(self._install)
        self.results.badge_clicked.connect(self._install)

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
        self.results.set_rows([])
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
        for w in (self.installed, self.open_btn):
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
        # Installed
        self.installed.setGeometry(16, t + 40, w - 32, h - (t + 40) - 58)
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
        rows = []
        for it in self._items:
            note = human_size(it.size) + ("" if it.enabled else " · disabled")
            rows.append(Row(
                title=it.name,
                subtitle=note,
                right="↑ UPDATE" if it.name in self._updates else "",
                badge="ON" if it.enabled else "OFF",
                badge_on=it.enabled,
                action="delete",
                data=it,
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

    def _load(self) -> None:
        """Nạp kết quả: có chữ thì tìm, rỗng thì discover mod hot theo sort/loader."""
        q = self.search.text().strip()
        self.results.empty_text = "Loading from Modrinth…"
        self.results.set_rows([])
        loaders, gvs = self._target()
        self.ctl._run(
            lambda: modrinth.search(q, self.project_type, loaders=loaders,
                                    game_versions=gvs, index=self._index, limit=30),
            self._show_results,
            self._search_failed,
        )

    def _search_failed(self, msg: str) -> None:
        self.results.empty_text = f"Couldn't reach Modrinth: {msg}"
        self.results.set_rows([])

    def _show_results(self, hits: list) -> None:
        self._hits = hits
        self.results.empty_text = "Nothing matched on Modrinth."
        self._render_results()
        self._load_icons()

    def _render_results(self) -> None:
        rows = []
        for h in self._hits:
            slug = h.get("slug") or h.get("project_id")
            if slug in self._busy:
                badge, on = "…", False
            elif slug in self._done:
                badge, on = "ADDED", False
            else:
                badge, on = "GET", True
            rows.append(Row(
                title=h.get("title", slug),
                subtitle=f"{h.get('author', '?')} · {human_count(h.get('downloads', 0))} downloads",
                badge=badge,
                badge_on=on,
                icon=self._icons.get(h.get("icon_url") or ""),
                data=h,
            ))
        self.results.set_rows(rows)

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
            self._render_results()

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

        self.tabs = TabBar([c[0] for c in self.CONTENT] + ["Logs"], self)
        self.tabs.changed.connect(self._tab)

        self.content = ContentLibraryPage(ctl, self)
        self.content.enter_embedded(None)
        self.logs = QTextBrowser(self)
        self.logs.setStyleSheet(TEXT_QSS)
        self.logs.setFont(QFont("monospace", 8))
        self.logs.hide()

    def open(self, instance) -> None:
        self.instance = instance
        self.content.set_instance(instance)
        from .. import optifine
        self.optifine_btn.setVisible(
            optifine.is_legacy(optifine.mc_from_version_id(instance.version)))
        v = (instance.version or "").lower()
        self.shared_btn.setVisible(any(k in v for k in ("fabric", "forge", "neoforge")))
        self._relayout_actions()
        self.tabs.current = 0
        self._tab(0)

    def _relayout_actions(self) -> None:
        # Xếp các nút hành động (Shared skins / OptiFine) từ phải sang, chỉ cái đang hiện.
        x = self.width() - 20
        for btn in (self.optifine_btn, self.shared_btn):
            if btn.isVisible():
                x -= 128
                btn.setGeometry(x, 101, 128, 28)
                x -= 8

    def refresh(self) -> None:
        self.ctl._update_play_button()
        if self.tabs.current < len(self.CONTENT):
            self.content.refresh()

    def _tab(self, i: int) -> None:
        self.tabs.current = i
        self.tabs.update()
        is_logs = i == len(self.CONTENT)
        self.content.setVisible(not is_logs)
        self.logs.setVisible(is_logs)
        if is_logs:
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
        self.logs.setGeometry(24, 142, w - 48, h - 166)

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
        self._variant = "classic"                # kiểu tay đang chọn: classic/slim
        self._tiles: list[tuple[QRect, str, str, str]] = []  # (rect, action, path, variant)
        self._hover = -1
        self._yaw = -28.0        # góc xoay preview 3D (kéo chuột để đổi)
        self._pitch = 12.0
        self._preview_rect = QRect()
        self._drag_from = None
        self.setMouseTracking(True)

    def refresh(self) -> None:
        from .. import skins
        account = self.ctl.current_account()
        self.skin, self.note = None, ""
        self._recent = skins.recent()
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
        self.update()

    def _got_defaults(self, items) -> None:
        self._defaults = items or []
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
                          self._yaw, self._pitch, self._variant == "slim")

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
        x = rx + self.TILE_W + self.GAP
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

        if self.note:
            p.setFont(ui_font(9))
            p.setPen(TEXT_DIM)
            p.drawText(QRect(rx, self.height() - 70, self.width() - rx - 24, 40),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.note)
        p.end()

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

    def _paint_skin_tile(self, p, rect: QRect, item: dict, selected: bool, hovered: bool):
        self._tile_bg(p, rect, hovered, selected)
        img = QImage()
        if img.load(item["path"]) and img.width() >= 64:
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
        self.check_updates = AeroToggle(s.check_updates, self)
        self.check_updates.toggled.connect(self._set_check_updates)

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

    def _set_check_updates(self, on: bool) -> None:
        self.ctl.settings.check_updates = on
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
        self.check_updates.setGeometry(26, 448, 44, 22)
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
        p.drawText(QRect(84, 446, 400, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   "Check for updates on startup")

        warn = self.ctl.settings.memory_mb > self._max_memory() * 0.9
        if warn:
            p.setFont(ui_font(8))
            p.setPen(DEGRADED)
            p.drawText(QRect(26, 90, self.width() - 52, 16), Qt.AlignLeft | Qt.AlignVCenter,
                       "Setting near all your RAM can freeze the system.")
        p.end()
