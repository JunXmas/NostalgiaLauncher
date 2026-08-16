"""Điểm vào GUI: nối cửa sổ với AccountStore, Settings và các luồng nền."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from PySide6.QtCore import QRect, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog

from .. import __version__, accounts, content, fabric, identity as identity_mod, updater
from ..install import Installer
from ..settings import Settings, client_id as resolve_client_id, save_client_id
from . import pages as page_mod
from .dashboard import HomeDashboard
from .dialogs import ConfirmDialog, LoginDialog, ReportDialog, TextPrompt
from .menus import MenuItem, popup
from .window import SIDEBAR_W, LauncherWindow
from .worker import FnWorker, GoogleLinkWorker, LaunchWorker, LoginWorker


def describe(store: accounts.AccountStore, account) -> tuple[str, str]:
    """Trả về (nhãn chế độ, trạng thái chấm màu)."""
    if account is None:
        return "Not signed in", "off"
    if account.kind == accounts.OFFLINE:
        return "Offline", "ok"
    return ("Connected", "ok") if account.owns_game else ("Demo mode", "warn")


class Controller:
    def __init__(self, window: LauncherWindow):
        self.window = window
        self.settings = Settings.load()
        self.store = accounts.AccountStore()
        self.identities = identity_mod.IdentityStore()
        self.installer = Installer(self.settings.game_path)
        window.background_path = self.settings.background_path
        self._pending_bg = True
        self._workers: list = []          # giữ tham chiếu, tránh bị thu gom giữa chừng
        self._launches: list[LaunchWorker] = []   # cho phép nhiều instance cùng lúc
        self._versions: list[dict] = []
        self._fabric_games: list[str] = []

        self._build_pages()
        window.nav_clicked.connect(self.go)
        window.closing.connect(self.shutdown)
        self.refresh()
        self.go("home")
        self.window.rebuild_hero()
        self._ensure_version()
        self._maybe_check_updates()

    # ---------- dựng ----------

    def _build_pages(self) -> None:
        self.pages = {
            "home": HomeDashboard(self),
            "installations": page_mod.InstallationsPage(self),
            "mods": page_mod.ModsPage(self),
            "resourcepacks": page_mod.ResourcePacksPage(self),
            "servers": page_mod.StubPage(self, "Servers",
                "A server list is not built yet."),
            "skins": page_mod.SkinsPage(self),
            "settings": page_mod.SettingsPage(self),
        }
        self.window.register_pages(self.pages)

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

    def go(self, key: str) -> None:
        self.window.show_page(key)

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
        dlg.title = "Link Google account"
        dlg.message = "Opening browser…"
        dlg.show()
        if not client_id:
            dlg.show_result(False, "GOOGLE_CLIENT_ID is not set.\n\nCreate an OAuth client ID "
                                   "of type Desktop app at console.cloud.google.com, then "
                                   "export GOOGLE_CLIENT_ID.")
            return

        worker = GoogleLinkWorker(client_id, secret)
        worker.url_ready.connect(lambda url: (
            QDesktopServices.openUrl(QUrl(url)),
            dlg.show_result(True, "Browser opened. Pick your Google account, then come back."),
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
        dlg.show_result(True, f"Linked {info.get('email') or info.get('name')}.\n\n"
                              f"Player ID: {ident.player_id}")
        self.refresh()

    def unlink_google(self) -> None:
        self.identities.unlink_external("google")
        self.window.set_status("Google unlinked.")
        self.refresh()

    def refresh(self) -> None:
        account = self.current_account()
        mode, state = describe(self.store, account)
        self.window.set_account(account.label if account else "—", mode, state)
        self.window.set_status("Everything is up to date!")
        self.window.set_java(self._java_status())
        self._refresh_pages()

    def _refresh_pages(self) -> None:
        if self.window.current_page is not None:
            self.window.current_page.refresh()

    def version_display(self) -> str:
        return self.settings.selected_version or "No version selected"

    def _java_status(self) -> str:
        """Java hiển thị ở status bar — chỉ đọc dữ liệu cục bộ, không gọi mạng."""
        from .. import jre
        v = self.settings.selected_version
        local = self.installer.versions_dir / v / f"{v}.json" if v else None
        if not local or not local.is_file():
            return "Java: managed by launcher"
        try:
            meta = self.installer.version_json(v)
        except Exception:  # noqa: BLE001
            return "Java: managed by launcher"
        major = meta.get("javaVersion", {}).get("majorVersion", 8)
        comp = jre.component_of(meta)
        ready = jre.is_installed(self.settings.game_path, comp)
        return f"Java {major}" + (" ✓" if ready else " (will download)")

    def select_version(self, version_id: str) -> None:
        self.set_version(version_id)


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
        self.window.set_java(self._java_status())
        self.pages["installations"].refresh()
        self.pages["home"].refresh()

    def pick_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Choose a background image",
            str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.set_background(path)
            self.window.set_status("Background changed.")

    def set_background(self, path: str) -> None:
        self.settings.background_path = path
        self.settings.save()
        self.window.background_path = path
        self.window.rebuild_hero()

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
        worker.failed.connect(on_fail or (lambda m: self.window.set_status(f"Error: {m}")))
        worker.finished.connect(lambda: self._workers.remove(worker)
                                if worker in self._workers else None)
        self._workers.append(worker)
        worker.start()

    # ---------- tự cập nhật ----------

    def _maybe_check_updates(self) -> None:
        """Tìm bản mới trên GitHub (im lặng nếu lỗi mạng hoặc đã tắt trong Settings)."""
        if not self.settings.check_updates:
            return
        self._update_info = None
        self._run(updater.check, self._on_update_found, lambda _m: None)

    def _on_update_found(self, info) -> None:
        if not info:
            return
        self._update_info = info
        notes = info.get("notes", "")
        snippet = (notes[:200] + "…") if len(notes) > 200 else notes
        msg = f"Version {info['version']} is out — you have {__version__}."
        if snippet:
            msg += "\n\n" + snippet
        dlg = ConfirmDialog(self.window, "Update available", msg,
                            ok_text="GET UPDATE", tone="green")
        dlg.confirmed.connect(self._get_update)
        dlg.show()

    def _get_update(self) -> None:
        info = self._update_info or {}
        asset = info.get("asset")
        page = info.get("page_url", "")
        if not asset:
            # Không có installer khớp hệ điều hành (vd Linux) -> mở trang release.
            self.open_url(page)
            return
        self.window.set_status(f"Downloading {asset['name']}…")
        self._run(
            lambda: updater.download_asset(asset),
            self._update_ready,
            lambda m: (self.open_url(page),
                       self.window.set_status(f"Download failed ({m}); opened the release page.")),
        )

    def _update_ready(self, path) -> None:
        self.window.set_status(f"Saved {path.name} to your Downloads — opening the installer…")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def load_news(self, cb) -> None:
        self._run(content.fetch_news, cb, lambda _m: cb(None))

    def load_patch_notes(self, cb) -> None:
        self._run(content.fetch_patch_notes, cb, lambda _m: cb(None))

    def load_patch_body(self, path, cb) -> None:
        self._run(lambda: content.fetch_patch_body(path), cb,
                  lambda m: cb(f"Could not load patch notes: {m}"))

    def load_skin(self, url, cb) -> None:
        self._run(lambda: requests.get(url, timeout=25).content, cb, lambda _m: cb(None))

    # ---------- menu tài khoản ----------

    def open_account_menu(self) -> None:
        items = [MenuItem(kind="header", label="Accounts")]
        for a in self.store.accounts:
            mode, _ = describe(self.store, a)
            items.append(MenuItem(label=a.label, sublabel=mode,
                                  checked=a.label == self.store.default_label,
                                  data=("use", a.label)))
        if not self.store.accounts:
            items.append(MenuItem(label="(no accounts yet)", enabled=False))
        items += [
            MenuItem(kind="separator"),
            MenuItem(label="Add Microsoft account…", data=("add", None)),
            MenuItem(label="Change Client ID…", data=("client_id", None)),
            MenuItem(label="Add offline profile…", data=("offline", None)),
        ]
        if self.store.accounts:
            items += [MenuItem(kind="separator"),
                      MenuItem(label="Remove selected account", data=("remove", None))]

        ident = self.player_identity()
        link = ident.link_for("google")
        items += [MenuItem(kind="separator"), MenuItem(kind="header", label="Identity")]
        if link:
            items.append(MenuItem(label=link.email or link.display_name or "Google",
                                  sublabel=f"{len(ident.account_labels)} accounts linked",
                                  checked=True, data=("unlink_google", None)))
        else:
            items.append(MenuItem(label="Link Google account…",
                                  sublabel="keep data when switching accounts",
                                  data=("link_google", None)))

        popup(self.window, items, self._account_anchor, self._account_action, width=252)

    def open_account_menu_dashboard(self) -> None:
        self.open_account_menu()

    @property
    def _account_anchor(self) -> QRect:
        """Neo menu tài khoản dưới nút Manage Account của dashboard nếu đang ở Home,
        không thì neo ở góc trên phải."""
        home = self.pages.get("home")
        if home is not None and home.isVisible():
            btn = home.manage_btn
            origin = btn.mapTo(self.window, btn.rect().topLeft())
            return QRect(origin, btn.size())
        return QRect(self.window.width() - 280, 40, 250, 20)

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
        elif action == "client_id":
            self.change_client_id()
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
                    self.window, "Remove account",
                    f"Remove '{account.label}' from the launcher?\n\n"
                    "This only removes it from this machine, not your Microsoft account.",
                )
                dlg.confirmed.connect(lambda: (self.store.remove(account.label),
                                               self.identities.detach_account(account.label),
                                               self.refresh()))
                dlg.show()

    def begin_add_offline(self) -> None:
        dlg = TextPrompt(
            self.window, "Add offline profile", "In-game display name:",
            placeholder="ví dụ: Lan",
            hint="Tạo profile offline không giới hạn để chơi local hoặc test server.",
        )
        dlg.accepted.connect(self._add_offline)
        dlg.show()

    def _add_offline(self, name: str) -> None:
        account = self.store.add_offline(name)
        self._adopt_account(account.label)
        self.refresh()

    # ---------- đăng nhập ----------

    def begin_login(self) -> None:
        client_id = resolve_client_id("microsoft", "MC_CLIENT_ID")
        if not client_id:
            self._prompt_client_id()
            return
        self._start_login(client_id)

    def _prompt_client_id(self, *, prefill: str = "", then_login: bool = True) -> None:
        dlg = TextPrompt(
            self.window, "Microsoft Client ID",
            "Application (client) ID:",
            placeholder="dán Application (client) ID từ Azure",
            hint="Tạo app tại portal.azure.com (Personal accounts, bật Allow "
                 "public client flows), dán ID vào đây — sẽ được lưu lại.",
            ok_text="CONTINUE" if then_login else "SAVE",
        )
        if prefill:
            dlg.edit.setText(prefill)
        dlg.accepted.connect(lambda v: self._client_id_entered(v, then_login))
        dlg.show()

    def change_client_id(self) -> None:
        """Mở prompt điền sẵn Client ID hiện tại để sửa mà không cần đăng nhập lại."""
        current = resolve_client_id("microsoft", "MC_CLIENT_ID")
        self._prompt_client_id(prefill=current, then_login=False)

    def _client_id_entered(self, value: str, then_login: bool = True) -> None:
        client_id = value.strip()
        if not client_id:
            return
        save_client_id("microsoft", client_id)
        if not then_login:
            self.window.set_status("Microsoft Client ID saved.")
            return
        self._start_login(client_id)

    def _start_login(self, client_id: str) -> None:
        dlg = LoginDialog(self.window)
        dlg.show()
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
        kind = "owns the game" if session.owns_game else "no game — will run demo"
        dlg.show_result(True, f"Added '{label}' ({kind}).")
        self.refresh()

    # ---------- menu phiên bản ----------

    def open_version_menu(self, anchor: QRect | None = None) -> None:
        if anchor is None:
            anchor = QRect(self.window.width() // 2 - 120, 150, 250, 34)
        self._show_version_menu(anchor, above=False)

    def open_version_menu_for_install(self) -> None:
        page = self.pages["installations"]
        anchor = QRect(page.add_btn.geometry())
        anchor.translate(SIDEBAR_W, 0)
        self._show_version_menu(anchor, above=True)

    def _show_version_menu(self, anchor: QRect, *, above: bool) -> None:
        if self._versions:
            self._render_version_menu(anchor, above)
            return
        self.window.set_status("Fetching version list…")
        self._run(self._fetch_versions,
                  lambda vs: (self._versions.extend(vs),
                              self.window.set_status("Ready"),
                              self._render_version_menu(anchor, above)))

    def _fetch_versions(self) -> list[dict]:
        kind = "all" if self.settings.show_snapshots else "release"
        return [{"id": v} for v in self.installer.list_versions(kind)[:80]]

    def _render_version_menu(self, anchor: QRect, above: bool) -> None:
        installed = {v["id"] for v in self.installer.installed_versions() if v["complete"]}
        current = self.settings.selected_version
        items = [MenuItem(kind="header", label="Version")]
        for v in self._versions:
            vid = v["id"]
            items.append(MenuItem(
                label=vid,
                sublabel="downloaded" if vid in installed else "",
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
        anchor.translate(SIDEBAR_W, 0)
        if self._fabric_games:
            self._render_fabric_menu(anchor)
            return
        self.window.set_status("Fetching Fabric-supported versions…")
        self._run(lambda: fabric.list_game_versions()[:40],
                  lambda vs: (self._fabric_games.extend(vs),
                              self.window.set_status("Ready"),
                              self._render_fabric_menu(anchor)))

    def _render_fabric_menu(self, anchor: QRect) -> None:
        installed = {v["id"] for v in self.installer.installed_versions()}
        items = [MenuItem(kind="header", label="Install Fabric for version")]
        for gv in self._fabric_games:
            done = any(i.startswith("fabric-loader-") and i.endswith(f"-{gv}")
                       for i in installed)
            items.append(MenuItem(label=gv, sublabel="installed" if done else "",
                                  checked=done, data=gv))
        popup(self.window, items, anchor, self._install_fabric, width=250, above=True)

    def _install_fabric(self, game_version) -> None:
        if not game_version:
            return
        self.window.set_status(f"Installing Fabric for {game_version}…")

        def done(version_id):
            self.set_version(version_id)
            self.window.set_status(f"Installed {version_id}. Press PLAY to download the rest.")
            self.pages["installations"].refresh()

        self._run(lambda: fabric.install(self.installer, game_version), done,
                  lambda m: self.window.set_status(f"Fabric install failed: {m}"))

    # ---------- xoá phiên bản ----------

    def ask_delete_version(self, version_id) -> None:
        dlg = ConfirmDialog(
            self.window, "Remove version",
            f"Delete {version_id} from disk?\n\nOnly the version folder is removed. "
            "Shared libraries and assets are kept.",
        )
        dlg.confirmed.connect(lambda: self._delete_version(version_id))
        dlg.show()

    def _delete_version(self, version_id: str) -> None:
        if self.installer.delete_version(version_id):
            self.window.set_status(f"Removed {version_id}.")
            if self.settings.selected_version == version_id:
                self.settings.selected_version = ""
                self.settings.save()
                self._update_version_label()
        self.pages["installations"].refresh()

    def run_doctor(self) -> None:
        """Soi bản cài đặt đang chọn — kiểm tra launcher mà không cần tài khoản nào."""
        version = self.settings.selected_version
        if not version:
            self.window.set_status("No version selected to check.")
            return
        dlg = ReportDialog(self.window, f"Check {version}")
        dlg.show()

        def work():
            from ..doctor import diagnose
            report = diagnose(self.installer, version, memory_mb=self.settings.memory_mb,
                              java_path=self.settings.java_path, verify_hashes=True)
            return report.text(show_command=True)

        self._run(work, dlg.set_body, lambda m: dlg.set_body(f"Could not run: {m}"))

    # ---------- tiện ích ----------

    def open_url(self, url) -> None:
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def open_path(self, path: Path) -> None:
        # Qt tự biết gọi Explorer, Finder hay xdg-open tuỳ hệ điều hành, nên khỏi
        # phải tự phân nhánh — `xdg-open` vốn chỉ có trên Linux.
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ---------- chạy game ----------

    @property
    def running_count(self) -> int:
        return sum(1 for w in self._launches if w.isRunning())

    def start_launch(self) -> None:
        account = self.current_account()
        if account is None:
            self.window.set_status("No account — click the name at the top left to add one.")
            return
        version = self.settings.selected_version
        if not version:
            self.window.set_status("No version selected — click the version box next to PLAY.")
            return

        if account.kind == accounts.MSA:
            client_id = resolve_client_id("microsoft", "MC_CLIENT_ID")
            if client_id:
                account = accounts.refresh_if_online(self.store, account, client_id)

        # Nhiều instance dùng chung một game_dir sẽ tranh nhau khoá file world;
        # multiplayer/LAN thì không sao, singleplayer thì phải tách thư mục.
        if self.running_count:
            self.window.set_status(
                f"Opening instance #{self.running_count + 1} — "
                "same game folder, so only servers/LAN work, not singleplayer worlds."
            )

        worker = LaunchWorker(
            self.store, account, version, self.settings.game_path,
            memory_mb=self.settings.memory_mb, java_path=self.settings.java_path,
        )
        worker.progress.connect(self._on_progress)
        worker.status.connect(self.window.set_status)
        worker.failed.connect(lambda m: self.window.set_status(f"Error: {m}"))
        worker.finished_ok.connect(self._launch_done)
        worker.finished.connect(lambda: self._launch_finished(worker))
        self._launches.append(worker)
        worker.start()

    def _launch_done(self) -> None:
        self.window.set_status("Everything is up to date!")

    def _launch_finished(self, worker) -> None:
        if worker in self._launches:
            self._launches.remove(worker)
        self.pages["installations"].refresh()
        left = self.running_count
        self.window.set_status(f"{left} instance(s) running" if left else "Ready")

    def _on_progress(self, stage: str, done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 0
        self.window.set_status(f"{stage} · {done:,} / {total:,} files ({pct}%)".replace(",", " "))


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
