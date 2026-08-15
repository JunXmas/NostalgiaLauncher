"""Điểm vào GUI: nối cửa sổ với AccountStore, Settings và các luồng nền."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests
from PySide6.QtCore import QRect, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from .. import accounts, content, fabric, identity as identity_mod
from ..install import Installer
from ..settings import Settings, client_id as resolve_client_id
from . import pages as page_mod
from .dialogs import ConfirmDialog, LoginDialog, ReportDialog, TextPrompt
from .menus import MenuItem, popup
from .window import ACCOUNT_HIT, PILL, SIDEBAR_W, TOPBAR_H, LauncherWindow
from .worker import FnWorker, GoogleLinkWorker, LaunchWorker, LoginWorker

SECTIONS = {
    "news": ("TIN TỨC", False, False),
    "game": ("MINECRAFT: JAVA EDITION", True, True),
    "settings": ("CÀI ĐẶT", False, False),
}
TAB_PAGES = ["play", "installations", "skins", "notes"]


def describe(store: accounts.AccountStore, account) -> tuple[str, str]:
    """Trả về (nhãn chế độ, trạng thái chấm màu)."""
    if account is None:
        return "Chưa đăng nhập", "off"
    if account.kind == accounts.OFFLINE:
        return ("Offline", "ok") if store.any_owns_game() else ("Offline → demo", "warn")
    return ("Đã kết nối", "ok") if account.owns_game else ("Demo mode", "warn")


class Controller:
    def __init__(self, window: LauncherWindow):
        self.window = window
        self.settings = Settings.load()
        self.store = accounts.AccountStore()
        self.identities = identity_mod.IdentityStore()
        self.installer = Installer(self.settings.game_path)
        self.section = "game"
        self.tab = 0
        self._workers: list = []          # giữ tham chiếu, tránh bị thu gom giữa chừng
        self._launches: list[LaunchWorker] = []   # cho phép nhiều instance cùng lúc
        self._versions: list[dict] = []
        self._fabric_games: list[str] = []

        self._build_pages()
        self._wire()
        window.closing.connect(self.shutdown)
        self.refresh()
        self._goto("game", tab=0)
        self._ensure_version()

    # ---------- dựng ----------

    def _build_pages(self) -> None:
        self.pages = {
            "play": page_mod.PlayPage(self),
            "installations": page_mod.InstallationsPage(self),
            "skins": page_mod.SkinsPage(self),
            "notes": page_mod.NotesPage(self),
            "news": page_mod.NewsPage(self),
            "settings": page_mod.SettingsPage(self),
        }
        self.window.register_pages(self.pages)

    def _wire(self) -> None:
        w = self.window
        w.play.clicked.connect(self.start_launch)
        w.sidebar.account_clicked.connect(self.open_account_menu)
        w.bottombar.version_clicked.connect(self.open_version_menu)
        w.tabs.changed.connect(self._tab_changed)
        w.nav_news.clicked.connect(lambda: self._goto("news"))
        w.nav_game.clicked.connect(lambda: self._goto("game", tab=self.tab))
        w.nav_settings.clicked.connect(lambda: self._goto("settings"))

    def shutdown(self) -> None:
        """Dừng mọi luồng nền trước khi cửa sổ biến mất.

        Không làm thì Qt kêu "QThread: Destroyed while thread is still running"
        và tiến trình có thể treo lại sau khi đóng.
        """
        for worker in list(self._workers) + list(self._launches):
            worker.requestInterruption()
            worker.quit()
            worker.wait(2000)
        self._workers.clear()
        self._launches.clear()

    # ---------- điều hướng ----------

    def _goto(self, section: str, *, tab: int | None = None) -> None:
        self.section = section
        title, tabs_visible, bottom = SECTIONS[section]
        w = self.window
        for item, key in ((w.nav_news, "news"), (w.nav_game, "game"),
                          (w.nav_settings, "settings")):
            item.setChecked(key == section)

        if section == "game":
            self.tab = self.tab if tab is None else tab
            w.tabs.current = self.tab
            key = TAB_PAGES[self.tab]
            bottom = self.tab == 0
        else:
            key = section
        w.show_page(key, title=title, tabs_visible=tabs_visible, bottom_visible=bottom)

    def _tab_changed(self, index: int) -> None:
        self.tab = index
        self._goto("game", tab=index)

    # ---------- trạng thái ----------

    def current_account(self):
        return self.store.get(None)

    # ---------- danh tính người chơi ----------

    def player_identity(self):
        """Danh tính ổn định của launcher — KHÔNG phải UUID Minecraft.

        Đây là thứ duy nhất không đổi khi người chơi bỏ hồ sơ offline để dùng tài
        khoản premium, nên mọi dữ liệu gắn theo người chơi phải khoá vào ID này.
        """
        return self.identities.active()

    def _adopt_account(self, label: str) -> None:
        self.identities.attach_account(label)

    def link_google(self) -> None:
        client_id = resolve_client_id("google", "GOOGLE_CLIENT_ID")
        secret = resolve_client_id("google_secret", "GOOGLE_CLIENT_SECRET")
        dlg = LoginDialog(self.window)
        dlg.title = "Liên kết tài khoản Google"
        dlg.message = "Đang mở trình duyệt…"
        dlg.show()
        if not client_id:
            dlg.show_result(False, "Chưa đặt GOOGLE_CLIENT_ID.\n\nTạo OAuth client ID "
                                   "kiểu Desktop app tại console.cloud.google.com rồi "
                                   "export GOOGLE_CLIENT_ID.")
            return

        worker = GoogleLinkWorker(client_id, secret)
        worker.url_ready.connect(lambda url: (
            QDesktopServices.openUrl(QUrl(url)),
            dlg.show_result(True, "Đã mở trình duyệt. Chọn tài khoản Google rồi quay lại."),
        ))
        worker.linked.connect(lambda info: self._google_linked(dlg, info))
        worker.failed.connect(lambda m: dlg.show_result(False, m))
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _google_linked(self, dlg, info: dict) -> None:
        ident = self.identities.link_external("google", info["sub"], info.get("email", ""),
                                              info.get("name", ""))
        # Mọi tài khoản Minecraft đang có trên máy thuộc về người vừa liên kết.
        for account in self.store.accounts:
            self.identities.attach_account(account.label, ident.player_id)
        dlg.show_result(True, f"Đã liên kết {info.get('email') or info.get('name')}.\n\n"
                              f"ID người chơi: {ident.player_id}")
        self.refresh()

    def unlink_google(self) -> None:
        self.identities.unlink_external("google")
        self.window.set_status("Đã gỡ liên kết Google.")
        self.refresh()

    def refresh(self) -> None:
        account = self.current_account()
        mode, state = describe(self.store, account)
        self.window.set_account(account.label if account else "—", mode, state)
        self._update_version_label()
        self.window.set_status("Sẵn sàng")
        self.window.set_progress(None)

    def _update_version_label(self) -> None:
        v = self.settings.selected_version
        self.window.set_version(v if v else "Chưa chọn phiên bản")

    def _ensure_version(self) -> None:
        """Chưa chọn gì thì lấy bản release mới nhất, ưu tiên bản đã tải sẵn."""
        if self.settings.selected_version:
            return
        installed = self.installer.installed_versions()
        if installed:
            self.set_version(installed[0]["id"])
            return
        # Kiểm lại lúc callback về: người dùng có thể đã tự chọn phiên bản trong
        # lúc chờ mạng, và mặc định thì không được phép đè lên lựa chọn đó.
        def apply_default(ids):
            if ids and not self.settings.selected_version:
                self.set_version(ids[0])

        self._run(lambda: self.installer.list_versions("release")[:1], apply_default)

    def set_version(self, version_id: str) -> None:
        self.settings.selected_version = version_id
        self.settings.save()
        self._update_version_label()
        self.pages["installations"].refresh()

    def set_game_dir(self, path: str) -> None:
        if not path:
            return
        self.settings.game_dir = path
        self.settings.save()
        self.installer = Installer(self.settings.game_path)
        self.pages["installations"].refresh()

    # ---------- việc chạy nền ----------

    def _run(self, fn, on_done, on_fail=None) -> None:
        worker = FnWorker(fn)
        worker.done.connect(on_done)
        worker.failed.connect(on_fail or (lambda m: self.window.set_status(f"Lỗi: {m}")))
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def load_news(self, cb) -> None:
        self._run(content.fetch_news, cb, lambda _m: cb(None))

    def load_patch_notes(self, cb) -> None:
        self._run(content.fetch_patch_notes, cb, lambda _m: cb(None))

    def load_patch_body(self, path, cb) -> None:
        self._run(lambda: content.fetch_patch_body(path), cb,
                  lambda m: cb(f"Không tải được ghi chú: {m}"))

    def load_skin(self, url, cb) -> None:
        self._run(lambda: requests.get(url, timeout=25).content, cb, lambda _m: cb(None))

    # ---------- menu tài khoản ----------

    def open_account_menu(self) -> None:
        items = [MenuItem(kind="header", label="Tài khoản")]
        for a in self.store.accounts:
            mode, _ = describe(self.store, a)
            items.append(MenuItem(label=a.label, sublabel=mode,
                                  checked=a.label == self.store.default_label,
                                  data=("use", a.label)))
        if not self.store.accounts:
            items.append(MenuItem(label="(chưa có tài khoản nào)", enabled=False))
        items += [
            MenuItem(kind="separator"),
            MenuItem(label="Thêm tài khoản Microsoft…", data=("add", None)),
            MenuItem(label="Thêm hồ sơ offline…", data=("offline", None),
                     enabled=self.store.any_owns_game()),
        ]
        if self.store.accounts:
            items += [MenuItem(kind="separator"),
                      MenuItem(label="Xoá tài khoản đang chọn", data=("remove", None))]

        ident = self.player_identity()
        link = ident.link_for("google")
        items += [MenuItem(kind="separator"), MenuItem(kind="header", label="Danh tính")]
        if link:
            items.append(MenuItem(label=link.email or link.display_name or "Google",
                                  sublabel=f"{len(ident.account_labels)} tài khoản liên kết",
                                  checked=True, data=("unlink_google", None)))
        else:
            items.append(MenuItem(label="Liên kết tài khoản Google…",
                                  sublabel="giữ dữ liệu khi đổi sang tài khoản khác",
                                  data=("link_google", None)))

        anchor = QRect(ACCOUNT_HIT)
        anchor.translate(0, 0)
        popup(self.window, items, anchor, self._account_action, width=250)

    def _account_action(self, data) -> None:
        if not data:
            return
        action, value = data
        if action == "use":
            self.store.set_default(value)
            self.refresh()
            self.pages["skins"].refresh()
        elif action == "add":
            self.begin_login()
        elif action == "offline":
            self.begin_add_offline()
        elif action == "link_google":
            self.link_google()
        elif action == "unlink_google":
            self.unlink_google()
        elif action == "remove":
            account = self.current_account()
            if account:
                dlg = ConfirmDialog(
                    self.window, "Xoá tài khoản",
                    f"Xoá '{account.label}' khỏi launcher?\n\n"
                    "Chỉ xoá khỏi máy này, không ảnh hưởng tài khoản Microsoft.",
                )
                dlg.confirmed.connect(lambda: (self.store.remove(account.label),
                                               self.identities.detach_account(account.label),
                                               self.refresh()))
                dlg.show()

    def begin_add_offline(self) -> None:
        dlg = TextPrompt(
            self.window, "Thêm hồ sơ offline", "Tên hiển thị trong game:",
            placeholder="ví dụ: Lan",
            hint="Hồ sơ offline chỉ mở được khi launcher đã có một tài khoản "
                 "Microsoft sở hữu Minecraft. Xoá tài khoản đó đi thì các hồ sơ "
                 "offline tự hạ xuống demo mode.",
        )
        dlg.accepted.connect(self._add_offline)
        dlg.show()

    def _add_offline(self, name: str) -> None:
        try:
            account = self.store.add_offline(name)
        except accounts.OwnershipRequired as e:
            self.window.set_status(str(e))
            return
        self._adopt_account(account.label)
        self.refresh()

    # ---------- đăng nhập ----------

    def begin_login(self) -> None:
        client_id = resolve_client_id("microsoft", "MC_CLIENT_ID")
        dlg = LoginDialog(self.window)
        dlg.show()
        if not client_id:
            dlg.show_result(False, "Chưa đặt MC_CLIENT_ID.\n\nĐăng ký một Azure "
                                   "application (Personal Microsoft accounts, bật "
                                   "Allow public client flows) rồi export MC_CLIENT_ID.")
            return

        worker = LoginWorker(client_id)
        worker.code_ready.connect(lambda url, code: (dlg.show_code(url, code),
                                                     QDesktopServices.openUrl(QUrl(url))))
        worker.logged_in.connect(lambda s: self._login_ok(dlg, s))
        worker.failed.connect(lambda m: dlg.show_result(False, m))
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    def _login_ok(self, dlg, session) -> None:
        label = self.store.unique_label(
            session.username if session.owns_game else "demo"
        )
        account = accounts.StoredAccount.from_session(session, label)
        if not session.owns_game:
            account.demo_name = label
        self.store.upsert(account)
        self.store.set_default(label)
        self._adopt_account(label)
        kind = "có bản quyền" if session.owns_game else "chưa mua game — sẽ chạy demo"
        dlg.show_result(True, f"Đã thêm '{label}' ({kind}).")
        self.refresh()

    # ---------- menu phiên bản ----------

    def open_version_menu(self) -> None:
        anchor = QRect(PILL)
        anchor.translate(SIDEBAR_W, self.window.height() - self.window.bottombar.height())
        self._show_version_menu(anchor, above=True)

    def open_version_menu_for_install(self) -> None:
        page = self.pages["installations"]
        anchor = QRect(page.add_btn.geometry())
        anchor.translate(SIDEBAR_W, TOPBAR_H)
        self._show_version_menu(anchor, above=True)

    def _show_version_menu(self, anchor: QRect, *, above: bool) -> None:
        if self._versions:
            self._render_version_menu(anchor, above)
            return
        self.window.set_status("Đang lấy danh sách phiên bản…")
        self._run(self._fetch_versions,
                  lambda vs: (self._versions.extend(vs),
                              self.window.set_status("Sẵn sàng"),
                              self._render_version_menu(anchor, above)))

    def _fetch_versions(self) -> list[dict]:
        kind = "all" if self.settings.show_snapshots else "release"
        return [{"id": v} for v in self.installer.list_versions(kind)[:80]]

    def _render_version_menu(self, anchor: QRect, above: bool) -> None:
        installed = {v["id"] for v in self.installer.installed_versions() if v["complete"]}
        current = self.settings.selected_version
        items = [MenuItem(kind="header", label="Phiên bản")]
        for v in self._versions:
            vid = v["id"]
            items.append(MenuItem(
                label=vid,
                sublabel="đã tải" if vid in installed else "",
                checked=vid == current,
                data=vid,
            ))
        popup(self.window, items, anchor, self._pick_version, width=250, above=above)

    def _pick_version(self, version_id) -> None:
        if version_id:
            self.set_version(version_id)

    # ---------- Fabric ----------

    def open_fabric_menu(self) -> None:
        page = self.pages["installations"]
        anchor = QRect(page.fabric_btn.geometry())
        anchor.translate(SIDEBAR_W, TOPBAR_H)
        if self._fabric_games:
            self._render_fabric_menu(anchor)
            return
        self.window.set_status("Đang lấy danh sách phiên bản Fabric hỗ trợ…")
        self._run(lambda: fabric.list_game_versions()[:40],
                  lambda vs: (self._fabric_games.extend(vs),
                              self.window.set_status("Sẵn sàng"),
                              self._render_fabric_menu(anchor)))

    def _render_fabric_menu(self, anchor: QRect) -> None:
        installed = {v["id"] for v in self.installer.installed_versions()}
        items = [MenuItem(kind="header", label="Cài Fabric cho phiên bản")]
        for gv in self._fabric_games:
            done = any(i.startswith("fabric-loader-") and i.endswith(f"-{gv}")
                       for i in installed)
            items.append(MenuItem(label=gv, sublabel="đã cài" if done else "",
                                  checked=done, data=gv))
        popup(self.window, items, anchor, self._install_fabric, width=250, above=True)

    def _install_fabric(self, game_version) -> None:
        if not game_version:
            return
        self.window.set_status(f"Đang cài Fabric cho {game_version}…")

        def done(version_id):
            self.set_version(version_id)
            self.window.set_status(f"Đã cài {version_id}. Bấm CHƠI để tải phần còn lại.")
            self.pages["installations"].refresh()

        self._run(lambda: fabric.install(self.installer, game_version), done,
                  lambda m: self.window.set_status(f"Cài Fabric thất bại: {m}"))

    # ---------- xoá phiên bản ----------

    def ask_delete_version(self, version_id) -> None:
        dlg = ConfirmDialog(
            self.window, "Xoá phiên bản",
            f"Xoá {version_id} khỏi đĩa?\n\nChỉ xoá thư mục phiên bản. "
            "Thư viện và assets dùng chung nên vẫn giữ nguyên.",
        )
        dlg.confirmed.connect(lambda: self._delete_version(version_id))
        dlg.show()

    def _delete_version(self, version_id: str) -> None:
        if self.installer.delete_version(version_id):
            self.window.set_status(f"Đã xoá {version_id}.")
            if self.settings.selected_version == version_id:
                self.settings.selected_version = ""
                self.settings.save()
                self._update_version_label()
        self.pages["installations"].refresh()

    def run_doctor(self) -> None:
        """Soi bản cài đặt đang chọn — kiểm tra launcher mà không cần tài khoản nào."""
        version = self.settings.selected_version
        if not version:
            self.window.set_status("Chưa chọn phiên bản để kiểm tra.")
            return
        dlg = ReportDialog(self.window, f"Kiểm tra {version}")
        dlg.show()

        def work():
            from ..doctor import diagnose
            report = diagnose(self.installer, version, memory_mb=self.settings.memory_mb,
                              java_path=self.settings.java_path, verify_hashes=True)
            return report.text(show_command=True)

        self._run(work, dlg.set_body, lambda m: dlg.set_body(f"Không chạy được: {m}"))

    # ---------- tiện ích ----------

    def open_url(self, url) -> None:
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(path)])

    # ---------- chạy game ----------

    @property
    def running_count(self) -> int:
        return sum(1 for w in self._launches if w.isRunning())

    def start_launch(self) -> None:
        account = self.current_account()
        if account is None:
            self.window.set_status("Chưa có tài khoản — bấm vào tên ở góc trên trái để thêm.")
            return
        version = self.settings.selected_version
        if not version:
            self.window.set_status("Chưa chọn phiên bản — bấm ô phiên bản bên trái nút CHƠI.")
            return

        if account.kind == accounts.MSA:
            client_id = resolve_client_id("microsoft", "MC_CLIENT_ID")
            if client_id:
                account = accounts.refresh_if_online(self.store, account, client_id)

        # Nhiều instance dùng chung một game_dir sẽ tranh nhau khoá file world;
        # multiplayer/LAN thì không sao, singleplayer thì phải tách thư mục.
        if self.running_count:
            self.window.set_status(
                f"Đang mở thêm instance thứ {self.running_count + 1} — "
                "chung thư mục game nên chỉ vào server/LAN được, không mở world đơn."
            )

        worker = LaunchWorker(
            self.store, account, version, self.settings.game_path,
            memory_mb=self.settings.memory_mb, java_path=self.settings.java_path,
        )
        worker.progress.connect(self._on_progress)
        worker.status.connect(self.window.set_status)
        worker.failed.connect(lambda m: (self.window.set_status(f"Lỗi: {m}"),
                                         self.window.set_progress(None)))
        worker.finished_ok.connect(self._launch_done)
        worker.finished.connect(lambda: self._launch_finished(worker))
        self._launches.append(worker)
        worker.start()

    def _launch_done(self) -> None:
        self.window.set_progress(None)

    def _launch_finished(self, worker) -> None:
        if worker in self._launches:
            self._launches.remove(worker)
        self.pages["installations"].refresh()
        left = self.running_count
        self.window.set_status(f"{left} instance đang chạy" if left else "Sẵn sàng")

    def _on_progress(self, stage: str, done: int, total: int) -> None:
        self.window.set_progress(done / total if total else None)
        self.window.set_status(f"{stage} · {done:,} / {total:,} file".replace(",", " "))


def run_gui(game_dir: Path | None = None, version: str = "") -> int:
    app = QApplication(sys.argv)
    window = LauncherWindow()
    ctl = Controller(window)
    if game_dir is not None and str(game_dir) != ctl.settings.game_dir:
        ctl.set_game_dir(str(game_dir))
    if version:
        ctl.set_version(version)
    window.show()
    return app.exec()
