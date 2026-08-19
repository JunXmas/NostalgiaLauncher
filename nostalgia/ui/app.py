"""Điểm vào GUI: nối cửa sổ với AccountStore, Settings và các luồng nền."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PySide6.QtCore import QRect, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog

from .. import (
    __version__, accounts, content, fabric, identity as identity_mod,
    instances as instances_mod, loaders as loaders_mod, modpack as modpack_mod,
    modrinth as modrinth_mod, updater,
)
from ..install import Installer
from ..settings import Settings, client_id as resolve_client_id, save_client_id
from . import pages as page_mod
from .dashboard import HomeDashboard
from .modpack_page import ModpackBrowsePage
from .dialogs import ConfirmDialog, LoginDialog, ReportDialog, TextPrompt
from .menus import MenuItem, popup
from .window import SIDEBAR_W, LauncherWindow
from .worker import FnWorker, GoogleLinkWorker, LaunchWorker, LoginWorker, ProgressWorker


def open_native(target: str) -> bool:
    """Mở một đường dẫn hoặc URL bằng handler mặc định của hệ điều hành.

    Dùng subprocess với env đã làm sạch (updater.clean_child_env) thay cho
    QDesktopServices.openUrl, vì cái sau kế thừa nguyên môi trường (gồm
    LD_LIBRARY_PATH của bundle) cho tiến trình con — thủ phạm khiến 'Open folder'
    và các link không hoạt động ở bản cài.
    """
    if not target:
        return False
    try:
        if os.name == "nt":
            os.startfile(target)  # noqa: S606 - handler mặc định của Windows
            return True
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen(
            [opener, target], env=updater.clean_child_env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except OSError:
        # Còn nước còn tát: để Qt thử, ít nhất chạy-từ-nguồn vẫn mở được.
        from urllib.parse import urlparse
        is_url = bool(urlparse(target).scheme) and not os.path.exists(target)
        return QDesktopServices.openUrl(
            QUrl(target) if is_url else QUrl.fromLocalFile(target))


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
        from .. import i18n
        i18n.set_language(self.settings.language)
        self.store = accounts.AccountStore()
        self.identities = identity_mod.IdentityStore()
        self.installer = Installer(self.settings.game_path)
        self.instances = instances_mod.InstanceStore()
        window.background_path = self.settings.background_path
        self._pending_bg = True
        self._workers: list = []          # giữ tham chiếu, tránh bị thu gom giữa chừng
        self._launches: list[LaunchWorker] = []   # cho phép nhiều instance cùng lúc
        self._versions: list[dict] = []
        self._fabric_games: list[str] = []
        self._log_lines: list[str] = []           # log game gần nhất
        self._log_dialog = None
        self._launching = False        # có launch đang khởi động (tải/chuẩn bị) không

        self._build_pages()
        window.nav_clicked.connect(self.go)
        window.closing.connect(self.shutdown)
        self.refresh()
        self.go("home")
        self.window.rebuild_hero()
        self._ensure_version()
        self._bootstrap_instances()
        self._maybe_check_updates()

    # ---------- dựng ----------

    def _build_pages(self) -> None:
        self.pages = {
            "home": HomeDashboard(self),
            "installations": page_mod.InstallationsPage(self),
            "instance": page_mod.InstancePage(self),
            "mods": page_mod.ModsPage(self),
            "resourcepacks": page_mod.ResourcePacksPage(self),
            "shaders": page_mod.ShaderPacksPage(self),
            "modpacks": ModpackBrowsePage(self),
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
        if key == "discord":                 # nav item Discord = mở link mời
            from .window import DISCORD_INVITE
            self.open_url(DISCORD_INVITE)
            return
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
            self.open_url(url),
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
        inst = self.active_instance()
        if inst:
            return f"{inst.name}  ·  {inst.version}"
        return self.settings.selected_version or "No instance yet"

    def open_instance_menu(self, anchor: QRect) -> None:
        items = [MenuItem(kind="header", label="Instance")]
        for inst in self.instances.all():
            items.append(MenuItem(label=inst.name, sublabel=inst.version,
                                  checked=inst.name == self.instances.active,
                                  data=inst.name))
        if not self.instances.all():
            items.append(MenuItem(label="(none — click NEW INSTANCE)", enabled=False))
        items.append(MenuItem(kind="separator"))
        items.append(MenuItem(label="＋ Pick a version (Optimized)",
                              sublabel="Fabulously Optimized, ready to play",
                              data="\x00optimized"))
        popup(self.window, items, anchor, self._instance_menu_chosen, width=260)

    def _instance_menu_chosen(self, data) -> None:
        if data == "\x00optimized":
            self.begin_optimized_instance()
        elif data:
            self.set_active_instance(data)

    def begin_optimized_instance(self) -> None:
        """Chọn nhanh phiên bản -> tạo instance Fabulously Optimized, không hỏi tên."""
        self._new_instance_name = None
        self._new_instance_loader = "optimized"
        self.window.set_status("Fetching Fabulously Optimized versions…")
        self._run(self._fo_info, self._fo_ready,
                  lambda m: self.window.set_status(f"Couldn't reach Modrinth: {m}"))

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

    # ---------- instance (modpack riêng) ----------

    @property
    def store_root(self) -> Path:
        """Kho versions/libraries/assets/runtime dùng chung cho mọi instance."""
        return self.settings.game_path

    def active_instance(self):
        return self.instances.active_instance()

    def instance_dir(self, inst) -> Path:
        return inst.dir(self.store_root)

    def active_instance_dir(self) -> Path:
        inst = self.active_instance()
        return self.instance_dir(inst) if inst else self.store_root

    def set_active_instance(self, name: str) -> None:
        self.instances.set_active(name)
        inst = self.active_instance()
        if inst:
            self.settings.selected_version = inst.version
            self.settings.save()
        self.window.set_java(self._java_status())
        self.pages["home"].refresh()
        self.pages["installations"].refresh()

    def open_instance(self, name: str) -> None:
        """Mở trang chi tiết của một instance (đặt nó làm active)."""
        inst = self.instances.get(name)
        if not inst:
            return
        self.set_active_instance(name)
        self.pages["instance"].open(inst)
        self.go("instance")

    def create_instance(self, name: str, version: str):
        inst = self.instances.add(name, version)
        self.set_active_instance(inst.name)
        self.window.set_status(f"Created instance '{inst.name}' ({version}).")
        return inst

    def delete_instance(self, name: str) -> None:
        import shutil
        inst = self.instances.get(name)
        if inst:
            shutil.rmtree(self.instance_dir(inst), ignore_errors=True)
        self.instances.remove(name)
        self.set_active_instance(self.instances.active)
        self.window.set_status(f"Removed instance '{name}'.")

    def ask_delete_instance(self, name: str) -> None:
        dlg = ConfirmDialog(
            self.window, "Remove instance",
            f"Delete instance '{name}' and its mods/saves?\n\n"
            "Shared versions, libraries and assets are kept.",
        )
        dlg.confirmed.connect(lambda: (self.delete_instance(name),
                                       self.pages["installations"].refresh()))
        dlg.show()

    def edit_instance(self, name: str) -> None:
        from .dialogs import InstanceSettingsDialog
        from .pages import SettingsPage
        inst = self.instances.get(name)
        if not inst:
            return
        dlg = InstanceSettingsDialog(self.window, inst,
                                     default_memory=self.settings.memory_mb,
                                     max_memory=SettingsPage._max_memory())
        dlg.saved.connect(lambda nm, mem, jv: self._apply_instance_settings(name, nm, mem, jv))
        dlg.duplicate.connect(lambda: self.duplicate_instance(name))
        dlg.repair.connect(lambda: self.repair_instance(name))
        dlg.set_icon.connect(lambda: self._pick_instance_icon(name))
        dlg.reset_icon.connect(lambda: self._reset_instance_icon(name))
        dlg.show()

    def _pick_instance_icon(self, name: str) -> None:
        from PySide6.QtGui import QImage
        inst = self.instances.get(name)
        if not inst:
            return
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Choose an icon", "", "Image (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        img = QImage()
        if not img.load(path):
            self.window.set_status("Couldn't read that image.")
            return
        dest = self.instance_dir(inst) / "icon.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(dest), "PNG")          # chuẩn hoá về PNG (nhận jpg/webp)
        self.pages["home"].refresh()
        self.window.set_status(f"Icon set for '{name}'.")

    def _reset_instance_icon(self, name: str) -> None:
        inst = self.instances.get(name)
        if inst:
            (self.instance_dir(inst) / "icon.png").unlink(missing_ok=True)
            self.pages["home"].refresh()
            self.window.set_status(f"Icon reset for '{name}'.")

    def _apply_instance_settings(self, old_name, new_name, memory, java) -> None:
        import shutil
        final = old_name
        if new_name and new_name != old_name:
            old_inst = self.instances.get(old_name)
            old_dir = self.instance_dir(old_inst) if old_inst else None
            renamed = self.instances.rename(old_name, new_name)
            if renamed:
                final = renamed
                new_dir = self.instance_dir(self.instances.get(renamed))
                if old_dir and old_dir.exists() and old_dir != new_dir:
                    shutil.move(str(old_dir), str(new_dir))
        self.instances.set_settings(final, memory_mb=memory, java_path=java)
        self.pages["installations"].refresh()
        self.pages["home"].refresh()
        self.window.set_status(f"Saved settings for '{final}'.")

    def duplicate_instance(self, name: str) -> None:
        import shutil
        inst = self.instances.get(name)
        if not inst:
            return
        new = self.instances.add(f"{inst.name} copy", inst.version)
        self.instances.set_settings(new.name, memory_mb=inst.memory_mb,
                                    java_path=inst.java_path)
        src, dst = self.instance_dir(inst), self.instance_dir(new)
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        self.set_active_instance(new.name)
        self.pages["installations"].refresh()
        self.pages["home"].refresh()
        self.window.set_status(f"Duplicated to '{new.name}'.")

    def repair_instance(self, name: str) -> None:
        inst = self.instances.get(name)
        if not inst:
            return
        self.window.set_status(f"Repairing '{name}' — re-downloading files…")
        self._run(lambda: self.installer.install(inst.version),
                  lambda _m: (self.pages["installations"].refresh(),
                              self.window.set_status(f"Repaired '{name}'.")),
                  lambda m: self.window.set_status(f"Repair failed: {m}"))

    def begin_browse_modpacks(self) -> None:
        self.go("modpacks")

    def install_modpack(self, hit, game_version: str | None = None) -> None:
        slug = hit.get("slug") or hit.get("project_id")
        title = hit.get("title") or slug
        name = self.instances.unique_name(title)
        inst_dir = self.store_root / "instances" / instances_mod.slug(name)
        self.window.set_status(f"Installing modpack '{title}'…")

        def work(on_progress, on_status):
            import tempfile
            from .. import jre
            from ..install import download
            f = modrinth_mod.best_file(
                slug, game_versions=[game_version] if game_version else None)
            if not f:
                raise RuntimeError("no downloadable modpack file")
            on_status("Downloading modpack…")
            mrpack = Path(tempfile.mkdtemp()) / f["filename"]
            download(f["url"], mrpack, f.get("sha1"))
            index = modpack_mod.install_contents(mrpack, inst_dir,
                                                 on_status=on_status, on_progress=on_progress)
            # Lưu icon modpack làm thumbnail cho card ở Home (best-effort).
            icon_url = hit.get("icon_url")
            if icon_url:
                try:
                    ir = requests.get(icon_url, timeout=20)
                    if ir.status_code == 200 and ir.content:
                        inst_dir.mkdir(parents=True, exist_ok=True)
                        (inst_dir / "icon.png").write_bytes(ir.content)
                except requests.RequestException:
                    pass
            loader, mc = modpack_mod.loader_and_mc(index)
            if loader == "quilt":
                raise RuntimeError("Quilt modpacks aren't supported yet")
            on_status(f"Installing {loader} {mc}…")
            java = None
            if loader in ("forge", "neoforge"):
                meta = self.installer.install(mc)
                jre.ensure(self.store_root, meta)
                java = str(jre.java_binary(self.store_root, jre.component_of(meta)))
            # on_status -> hiện tiến trình khi chạy Forge/NeoForge installer (chậm vài phút).
            vid = loaders_mod.install(self.installer, loader, mc, java_binary=java,
                                      on_status=on_status)
            return name, vid

        w = ProgressWorker(work)
        w.progress.connect(self._set_progress)
        w.status.connect(self.window.set_status)
        w.done.connect(lambda r: self._modpack_installed(*r))
        w.failed.connect(lambda m: (self.window.set_progress(None),
                                    self.window.set_status(f"Modpack install failed: {m}")))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        self._workers.append(w)
        w.start()

    def install_optifine(self, inst) -> None:
        """Tải OptiFine từ optifine.net (client-side, giữ quảng cáo, không mirror)
        vào thư mục mods của instance legacy."""
        from .. import mods as mods_mgr, optifine
        mc = optifine.mc_from_version_id(inst.version)
        if not optifine.is_legacy(mc):
            self.window.set_status(
                "OptiFine is for legacy (≤1.12.2). On this version use Sodium/Iris instead.")
            return
        mods_dir = mods_mgr.folder(self.instance_dir(inst), "mods")

        def work(on_progress, on_status):
            on_status(f"Finding OptiFine for {mc}…")
            v = optifine.latest_for(mc)
            if not v:
                raise RuntimeError(f"No OptiFine build listed for Minecraft {mc}.")
            optifine.download(v["file"], mods_dir / v["file"],
                              on_status=on_status, on_progress=on_progress)
            return v["file"]

        w = ProgressWorker(work)
        w.progress.connect(self._set_progress)
        w.status.connect(self.window.set_status)
        w.done.connect(lambda f: (self.window.set_progress(None),
                                  self.window.set_status(
                                      f"Installed {f} (from optifine.net)."),
                                  self.pages["instance"].refresh()))
        w.failed.connect(lambda m: (self.window.set_progress(None),
                                    self.window.set_status(f"OptiFine failed: {m}")))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        self._workers.append(w)
        w.start()

    def enable_shared_skins(self, inst, *, silent: bool = False) -> None:
        """Cài CustomSkinLoader + cấu hình trỏ về backend, để offline nhìn skin nhau.

        silent=True: chạy nền khi tạo instance / cài modpack, không báo lỗi ra UI.
        """
        from .. import mods as mods_mgr, optifine, skins
        from .. import modrinth as mr
        v = (inst.version or "").lower()
        loader = ("fabric" if "fabric" in v else "neoforge" if "neoforge" in v
                  else "forge" if "forge" in v else "")
        if not loader:                       # vanilla không có loader -> không thể cài CSL
            if not silent:
                self.window.set_status("Shared skins need a Fabric/Forge instance.")
            return
        mc = optifine.mc_from_version_id(inst.version)
        game_dir = self.instance_dir(inst)

        def work():
            f = mr.best_file(skins.CSL_PROJECT, loaders=[loader],
                             game_versions=[mc] if mc else None)
            if not f:
                raise RuntimeError(f"No CustomSkinLoader build for {loader} {mc}.")
            mods_mgr.install_file(game_dir, "mods", url=f["url"],
                                  filename=f["filename"], sha1=f.get("sha1"))
            skins.write_csl_config(game_dir, self.settings.backend_url)
            return f["filename"]

        if not silent:
            self.window.set_status("Installing CustomSkinLoader…")
        self._run(
            work,
            (lambda _n: None) if silent else
            (lambda _n: self.window.set_status(
                "Shared skins enabled — you'll see other players' skins in-game.")),
            (lambda _m: None) if silent else
            (lambda m: self.window.set_status(f"Couldn't enable shared skins: {m}")))

    def _set_progress(self, done: int, total: int) -> None:
        self.window.set_progress(done / total if total else None)

    def _modpack_installed(self, name: str, version: str) -> None:
        self.window.set_progress(None)
        inst = self.instances.add(name, version)
        self.set_active_instance(name)
        self.enable_shared_skins(inst, silent=True)   # để offline nhìn skin nhau
        self.apply_aero_ui(inst, silent=True)         # UI kính Aero đi kèm sẵn
        self.window.set_status(f"Modpack '{name}' installed — press PLAY.")
        self.go("home")

    def apply_aero_ui(self, inst, silent: bool = False) -> None:
        """Cài resource pack Aero UI vào instance (nút/slider/tab thành kính).

        Bản modern dùng sprite ship sẵn; bản legacy (≤1.20.1) ghép nút Aero vào
        widgets.png rút từ jar của chính bản đó. Nhẹ nên chạy thẳng, không cần luồng.
        """
        from .. import aero
        jar = None
        try:
            meta = self.installer.offline_version_json(inst.version)
            cj = self.installer.client_jar(meta)
            jar = cj if cj and Path(cj).exists() else None
        except Exception:  # noqa: BLE001 - thiếu meta/jar thì cứ dùng sprite modern
            jar = None
        try:
            kind = aero.apply_to_instance(self.instance_dir(inst), jar)
        except Exception as e:  # noqa: BLE001
            if not silent:
                self.window.set_status(f"Couldn't install Aero UI: {e}")
            return
        if not silent:
            self.window.set_status(f"Aero UI installed ({kind}) for '{inst.name}'.")

    def remove_aero_ui(self, inst) -> None:
        from .. import aero
        aero.remove_from_instance(self.instance_dir(inst))
        self.window.set_status(f"Aero UI removed from '{inst.name}'.")

    def aero_ui_enabled(self, inst) -> bool:
        return (self.instance_dir(inst) / "resourcepacks" / "Aero UI.zip").exists()

    def _bootstrap_instances(self) -> None:
        """Lần đầu chạy bản có instance: dựng instance từ các version đã cài và
        chuyển mods/resourcepacks dùng chung cũ vào instance đang chọn."""
        if self.instances.all():
            return
        # Đã có file instances.json = KHÔNG phải lần đầu -> đừng tự dựng lại (kẻo
        # tạo instance đặt tên theo version id và làm world cũ bị orphan).
        if self.instances.path.exists():
            return
        versions = self.installer.installed_versions()
        if not versions:
            return                      # chưa có version -> để người dùng tự tạo
        for v in versions:
            self.instances.add(v["id"], v["id"])
        want = self.settings.selected_version
        target = want if any(v["id"] == want for v in versions) else versions[0]["id"]
        self.instances.set_active(target)
        self._migrate_legacy_content(self.active_instance())
        self.pages["home"].refresh()

    def _migrate_legacy_content(self, inst) -> None:
        if inst is None:
            return
        for kind in ("mods", "resourcepacks"):
            old = self.store_root / kind
            new = self.instance_dir(inst) / kind
            if not old.is_dir() or new.exists():
                continue
            files = [p for p in old.iterdir() if p.is_file()]
            if not files:
                continue
            new.mkdir(parents=True, exist_ok=True)
            for p in files:
                p.rename(new / p.name)

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

    def set_language(self, code) -> None:
        if not code:
            return
        from .. import i18n
        i18n.set_language(code)
        self.settings.language = code
        self.settings.save()
        self.window.retranslate()

    def open_language_menu(self, anchor: QRect) -> None:
        from .. import i18n
        items = [MenuItem(kind="header", label="Language")]
        for code, name in i18n.LANGUAGES:
            items.append(MenuItem(label=name, checked=code == i18n.language(), data=code))
        popup(self.window, items, anchor, self.set_language, width=220)

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
                            ok_text="INSTALL UPDATE", tone="green")
        dlg.confirmed.connect(self._get_update)
        dlg.show()

    def _get_update(self) -> None:
        info = self._update_info or {}
        asset = info.get("asset")
        if not asset:
            # Không có installer khớp hệ điều hành -> mở trang release.
            self.open_url(info.get("page_url", ""))
            return
        self._update_asset = asset
        self.window.set_status(f"Downloading {asset['name']}…")
        self._run(self._fetch_and_install, self._update_done, self._update_failed)

    def _fetch_and_install(self) -> str:
        # Chạy trong luồng nền: tải rồi cài thẳng vào máy (Linux pkexec chặn ở đây).
        path = updater.download_asset(self._update_asset)
        return updater.install(path)

    def _update_done(self, mode: str) -> None:
        if mode == "quit":
            # Windows: installer đang chạy nền, app phải thoát để nó thay file .exe
            # rồi tự mở lại (xem [Run] trong file .iss).
            self.window.set_status("Update installed — restarting…")
            QApplication.quit()
        elif mode == "installed":
            # Linux: đã cài xong -> tự mở lại bản mới rồi tắt bản cũ, không hỏi gì.
            self.window.set_status("Update installed — restarting…")
            updater.relaunch()
            QApplication.quit()
        else:  # opened
            self.window.set_status("Opened the installer — follow its steps to finish updating.")

    def _update_failed(self, msg: str) -> None:
        # Lùi an toàn: mở trang release để người dùng tự tải/cài.
        self.open_url((self._update_info or {}).get("page_url", ""))
        self.window.set_status(f"Auto-update failed ({msg}); opened the release page.")

    def load_news(self, cb) -> None:
        self._run(content.fetch_news, cb, lambda _m: cb(None))

    def load_continue(self, cb) -> None:
        """Thế giới + server chơi gần nhất và tổng giờ chơi, cho thẻ 'Continue playing'."""
        from .. import worlds

        def work():
            from concurrent.futures import ThreadPoolExecutor
            root = self.settings.game_path
            store = self.instances
            items = worlds.recent_worlds(store, root, 8) + worlds.recent_servers(store, root, 8)
            items.sort(key=lambda i: i["last"], reverse=True)
            items = items[:8]
            # Ping song song để lấy MOTD + số người + favicon mới (như danh sách trong game).
            servers = [i for i in items if i["kind"] == "server" and i.get("ip")]
            if servers:
                with ThreadPoolExecutor(max_workers=min(6, len(servers))) as ex:
                    futs = {ex.submit(worlds.ping_server, s["ip"]): s for s in servers}
                    for f, s in futs.items():
                        try:
                            r = f.result(timeout=2.0)
                        except Exception:  # noqa: BLE001
                            r = None
                        if r:
                            s["motd"] = r["motd"]
                            s["online"], s["max"] = r["online"], r["max"]
                            if r["favicon"]:
                                s["icon"] = r["favicon"]
            total = sum(i.playtime_sec for i in store.all())
            return {"items": items, "playtime": total}

        self._run(work, cb, lambda _m: cb({"items": [], "playtime": 0}))

    def play_continue_item(self, item: dict) -> None:
        """Bấm một mục 'Continue playing' -> hỏi xác nhận rồi vào thẳng server/thế giới."""
        from ..i18n import tr
        inst = self.instances.get(item.get("instance", ""))
        if inst is None:
            self.window.set_status(tr("That instance no longer exists."))
            return
        name = item.get("_title") or item.get("title") or item.get("instance")
        if item.get("kind") == "server":
            title = tr("Join server?")
            msg = tr("Launch “{inst}” and connect to {name}?").format(
                inst=inst.name, name=name)
        else:
            title = tr("Open world?")
            msg = tr("Launch “{inst}” and load the world “{name}”?").format(
                inst=inst.name, name=name)
        dlg = ConfirmDialog(self.window, title, msg, ok_text="PLAY", tone="green")
        dlg.confirmed.connect(lambda: self._do_play_continue(item))
        dlg.show()

    def _do_play_continue(self, item: dict) -> None:
        self.set_active_instance(item.get("instance", ""))
        quick = None
        if item.get("kind") == "server" and item.get("ip"):
            quick = {"type": "multiplayer", "target": item["ip"]}
        elif item.get("kind") == "world" and item.get("folder"):
            quick = {"type": "singleplayer", "target": item["folder"]}
        self.start_launch(quick_play=quick)

    def load_patch_notes(self, cb) -> None:
        self._run(content.fetch_patch_notes, cb, lambda _m: cb(None))

    def load_patch_body(self, path, cb) -> None:
        self._run(lambda: content.fetch_patch_body(path), cb,
                  lambda m: cb(f"Could not load patch notes: {m}"))

    def load_skin(self, url, cb) -> None:
        self._run(lambda: requests.get(url, timeout=25).content, cb, lambda _m: cb(None))

    # ---------- đổi skin ----------

    def ensure_default_skins(self, cb) -> None:
        from .. import skins
        self._run(skins.ensure_defaults, cb, lambda _m: cb([]))

    def load_account_skins(self, cb) -> None:
        """5 skin gần nhất của TÀI KHOẢN hiện tại từ backend (đi theo tài khoản)."""
        from .. import skins
        account = self.current_account()
        if not account:
            cb([])
            return
        self._run(lambda: skins.fetch_account_skins(self.settings.backend_url,
                                                    account.username),
                  cb, lambda _m: cb([]))

    def _premium(self):
        a = self.current_account()
        if a and a.kind == "msa" and a.owns_game and a.access_token and a.access_token != "0":
            return a
        return None

    def load_capes(self, cb) -> None:
        """Cape sở hữu của tài khoản premium hiện tại."""
        from .. import skins
        a = self._premium()
        if not a:
            cb([])
            return
        self._run(lambda: skins.fetch_capes(a.access_token), cb, lambda _m: cb([]))

    def apply_cape(self, cape_id) -> None:
        from .. import skins
        a = self._premium()
        if not a:
            self.window.set_status("Capes need a Microsoft account that owns the game.")
            return
        self.window.set_status("Applying cape…")
        self._run(lambda: skins.set_cape(a.access_token, cape_id),
                  lambda _r: (self.pages["skins"].refresh(),
                              self.window.set_status("Cape updated.")),
                  lambda m: self.window.set_status(f"Couldn't change cape: {m}"))

    def pick_and_apply_skin(self, variant: str = "classic") -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Choose a skin (64×64 PNG)", "", "Skin image (*.png)")
        if path:
            self.apply_skin_file(path, variant)

    def open_skin_editor(self, start_img=None, variant: str = "classic") -> None:
        """Mở trình vẽ skin; khi LƯU thì áp qua luồng đổi skin sẵn có."""
        from .skin_editor import SkinEditorDialog
        dlg = SkinEditorDialog(self.window, start_img, variant)
        dlg.saved.connect(lambda png, var: self.apply_skin_bytes(png, var))
        dlg.show()

    def apply_skin_file(self, path: str, variant: str = "classic") -> None:
        try:
            with open(path, "rb") as f:
                png = f.read()
        except OSError as e:
            self.window.set_status(f"Couldn't read skin: {e}")
            return
        self.apply_skin_bytes(png, variant)

    def apply_skin_bytes(self, png: bytes, variant: str = "classic") -> None:
        from .. import skins
        account = self.current_account()
        online = bool(account and account.kind == "msa" and account.owns_game
                      and account.access_token and account.access_token != "0")

        def work():
            if online:
                skins.apply_to_mojang(account.access_token, png, slim=variant == "slim")
            skins.remember(png, variant, account.username if account else "")
            # Đẩy lên backend chung để offline nhìn thấy nhau (qua CustomSkinLoader).
            # Lỗi backend không được chặn việc đổi skin cục bộ.
            if account:
                try:
                    skins.upload_to_backend(self.settings.backend_url, account.username,
                                            png, variant, account.access_token)
                except Exception:  # noqa: BLE001
                    pass
            return online

        self.window.set_status("Applying skin…")
        self._run(
            work,
            lambda was_online: (
                self.pages["skins"].refresh(),
                self.window.set_status(
                    "Skin changed on your Microsoft account." if was_online else
                    "Skin saved locally — others will see it once the skin server is set up.")),
            lambda m: self.window.set_status(f"Couldn't change skin: {m}"))

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
                                                     self.open_url(url)))
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

    def _show_version_menu(self, anchor: QRect, *, above: bool, on_pick=None) -> None:
        if self._versions:
            self._render_version_menu(anchor, above, on_pick)
            return
        self.window.set_status("Fetching version list…")
        self._run(self._fetch_versions,
                  lambda vs: (self._versions.extend(vs),
                              self.window.set_status("Ready"),
                              self._render_version_menu(anchor, above, on_pick)))

    def _fetch_versions(self) -> list[dict]:
        kind = "all" if self.settings.show_snapshots else "release"
        return [{"id": v} for v in self.installer.list_versions(kind)[:80]]

    def _render_version_menu(self, anchor: QRect, above: bool, on_pick=None) -> None:
        inst_versions = self.installer.installed_versions()
        installed = {v["id"] for v in inst_versions if v["complete"]}
        current = self.settings.selected_version
        listed = {v["id"] for v in self._versions}
        items = [MenuItem(kind="header", label="Version")]
        # Version đã cài không nằm trong danh sách vanilla (vd bản Fabric) đưa lên
        # đầu, để tạo instance Fabric hay chọn nhanh bản đã tải.
        for v in inst_versions:
            if v["id"] not in listed:
                items.append(MenuItem(
                    label=v["id"], sublabel=v.get("loader") or "downloaded",
                    checked=v["id"] == current, data=v["id"]))
        for v in self._versions:
            vid = v["id"]
            items.append(MenuItem(
                label=vid,
                sublabel="downloaded" if vid in installed else "",
                checked=vid == current,
                data=vid,
            ))
        popup(self.window, items, anchor, on_pick or self._pick_version,
              width=250, above=above)

    def _pick_version(self, version_id) -> None:
        if version_id:
            self.set_version(version_id)

    # ---------- tạo instance (đặt tên + chọn phiên bản) ----------

    def begin_create_instance(self) -> None:
        dlg = TextPrompt(
            self.window, "New instance", "Instance name:",
            placeholder="ví dụ: Fabric Fun",
            hint="Mỗi instance là một modpack riêng — mods, save, config tách biệt. "
                 "Chọn xong tên sẽ tới bước chọn phiên bản Minecraft.",
            ok_text="NEXT",
        )
        dlg.accepted.connect(self._instance_name_chosen)
        dlg.show()

    def _instance_name_chosen(self, name: str) -> None:
        self._new_instance_name = name.strip() or "Instance"
        # Bước 2: chọn loader (Vanilla / Fabric / Forge / NeoForge) trong thẻ gọn ở giữa.
        from .dialogs import LoaderDialog
        dlg = LoaderDialog(self.window)
        dlg.picked.connect(self._instance_loader_chosen)
        dlg.show()
        dlg.setFocus()

    def _instance_loader_chosen(self, loader) -> None:
        if loader is None:
            return
        self._new_instance_loader = loader
        self.window.set_status("Fetching versions…")
        if loader == "optimized":
            self.window.set_status("Fetching Fabulously Optimized versions…")
            self._run(self._fo_info, self._fo_ready,
                      lambda m: self.window.set_status(f"Couldn't reach Modrinth: {m}"))
        elif loader in ("", "vanilla"):
            self._run(lambda: self.installer.list_versions("release"),
                      lambda vs: self._open_version_picker(vs, vanilla=True),
                      lambda m: self.window.set_status(f"Couldn't list versions: {m}"))
        else:
            self._run(lambda: loaders_mod.game_versions(loader) or [],
                      lambda vs: self._open_version_picker(vs, vanilla=False),
                      lambda m: self.window.set_status(f"Couldn't list {loader} versions: {m}"))

    FO_SLUG = "fabulously-optimized"
    # Phiên bản legacy dùng modpack khác (FO chỉ Fabric 1.16+).
    LEGACY_OPT = {"1.12.2": "max-fps-optimized"}

    def _fo_info(self):
        """(danh sách phiên bản tối ưu, {slug: icon_url}) cho luồng 'Optimized'."""
        icons = {}
        fo = modrinth_mod.search("Fabulously Optimized", "modpack", limit=1)
        if fo:
            icons[self.FO_SLUG] = fo[0].get("icon_url", "")
        seen, gvs = set(), []
        for v in modrinth_mod.versions(self.FO_SLUG):
            for gv in v.get("game_versions", []):
                if gv not in seen and gv[:1].isdigit() and "-" not in gv and "w" not in gv:
                    seen.add(gv)
                    gvs.append(gv)
        gvs.sort(key=lambda s: [int(x) for x in s.split(".") if x.isdigit()], reverse=True)
        # thêm các bản legacy (vd 1.12.2) từ modpack riêng, kèm icon của chúng
        for mc, slug in self.LEGACY_OPT.items():
            hits = modrinth_mod.search(slug, "modpack", limit=3)
            h = next((x for x in hits if x.get("slug") == slug), None)
            if h:
                icons[slug] = h.get("icon_url", "")
            if mc not in seen:
                gvs.append(mc)
        return gvs, icons

    def _fo_ready(self, info) -> None:
        gvs, icons = info
        self._opt_icons = icons
        if not gvs:
            self.window.set_status("Couldn't list optimized versions.")
            return
        self._open_version_picker(gvs, vanilla=False)

    def _open_version_picker(self, versions, *, vanilla: bool) -> None:
        from .dialogs import VersionPickerDialog
        self.window.set_status("Ready")
        installed = {v["id"] for v in self.installer.installed_versions() if v["complete"]}
        dlg = VersionPickerDialog(
            self.window, versions, installed=installed,
            on_snapshots=self._toggle_snapshots if vanilla else None,
        )
        self._version_dlg = dlg
        dlg.picked.connect(self._create_with_loader)
        dlg.show()

    def _toggle_snapshots(self, on: bool) -> None:
        dlg = getattr(self, "_version_dlg", None)
        if dlg is None:
            return
        kind = "all" if on else "release"
        self._run(lambda: self.installer.list_versions(kind), dlg.set_versions)

    def _create_with_loader(self, mc) -> None:
        if not mc:
            return
        name, loader = self._new_instance_name, self._new_instance_loader
        if loader == "optimized":
            slug = self.LEGACY_OPT.get(mc, self.FO_SLUG)
            default = "Fabulously Optimized" if slug == self.FO_SLUG else "MAX FPS Optimized"
            hit = {"slug": slug, "title": name or f"{default} {mc}",
                   "icon_url": getattr(self, "_opt_icons", {}).get(slug, "")}
            self.install_modpack(hit, game_version=mc)
            return
        if loader in ("", "vanilla"):
            self.create_instance(name, mc)
            self.go("home")
            return
        self.window.set_status(f"Installing {loader} for {mc} — this can take a minute…")

        def work():
            java = None
            if loader in ("forge", "neoforge"):
                from .. import jre
                meta = self.installer.install(mc)         # tải vanilla + có meta để lấy Java
                jre.ensure(self.store_root, meta)
                java = str(jre.java_binary(self.store_root, jre.component_of(meta)))
            return loaders_mod.install(self.installer, loader, mc, java_binary=java)

        self._run(
            work,
            lambda vid: self._instance_created(name, vid),
            lambda m: self.window.set_status(f"Couldn't install {loader}: {m}"),
        )

    def _instance_created(self, name: str, vid: str) -> None:
        inst = self.create_instance(name, vid)
        self.enable_shared_skins(inst, silent=True)   # tự cài CSL để offline thấy skin nhau
        self.go("home")

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
                self.pages["home"].refresh()
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
            open_native(str(url))

    def open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        open_native(str(path))

    # ---------- chạy game ----------

    @property
    def running_count(self) -> int:
        return sum(1 for w in self._launches if w.isRunning())

    def _any_game_running(self) -> bool:
        return any(w._proc is not None and w._proc.poll() is None for w in self._launches)

    def _launch_active(self) -> bool:
        """Có launch nào đang diễn ra không — tính CẢ lúc đang tải/chuẩn bị,
        chứ không chỉ khi tiến trình game đã chạy. Nhờ vậy nút đổi sang STOP ngay
        khi bấm Play, để người chơi thấy rõ 'đang khởi động', không tưởng là đơ."""
        return self._launching or any(w.isRunning() for w in self._launches)

    def _update_play_button(self) -> None:
        active = self._launch_active()
        for key in ("home", "instance"):
            btn = getattr(self.pages.get(key), "play_btn", None)
            if btn is not None:
                btn.setText("STOP" if active else "PLAY")
                btn.arrow = not active
                btn.tone = "danger" if active else "green"
                btn.update()

    def toggle_play(self) -> None:
        if self._launch_active():
            self.stop_launch()
        else:
            self.start_launch()

    def stop_launch(self) -> None:
        # Đặt cờ tắt trước để nút phản hồi ngay, rồi mới bảo worker dừng: nếu game
        # đã chạy thì kết thúc tiến trình; nếu còn đang tải thì huỷ, không bật game.
        self._launching = False
        for w in list(self._launches):
            w.stop()
        self.window.set_status("Stopping…")
        self._update_play_button()

    def start_launch(self, quick_play: dict | None = None) -> None:
        account = self.current_account()
        if account is None:
            self.window.set_status("No account — click the name at the top left to add one.")
            return
        # Chạy instance đang chọn (thư mục game riêng); nếu chưa có instance thì
        # lùi về kho chung với phiên bản đã chọn.
        inst = self.active_instance()
        if inst is not None:
            version, game_dir = inst.version, self.instance_dir(inst)
        else:
            version, game_dir = self.settings.selected_version, self.store_root
        if not version:
            self.window.set_status("No instance yet — click NEW INSTANCE to make one.")
            return

        # Phản hồi tức thì: đổi nút sang STOP ngay khi bấm Play, TRƯỚC cả bước làm
        # mới token (có thể gọi mạng) và tải. Người chơi thấy ngay là 'đang khởi
        # động', không tưởng bấm hụt. Cờ được worker.isRunning() tiếp quản bên dưới.
        self._launching = True
        self.window.set_status("Starting…")
        self._update_play_button()

        if account.kind == accounts.MSA:
            client_id = resolve_client_id("microsoft", "MC_CLIENT_ID")
            if client_id:
                account = accounts.refresh_if_online(self.store, account, client_id)

        if self.running_count:
            self.window.set_status(f"Launching another game (#{self.running_count + 1})…")

        # Cấu hình riêng của instance đè lên mặc định chung (0/rỗng = dùng chung).
        memory = (inst.memory_mb if inst and inst.memory_mb else self.settings.memory_mb)
        java = (inst.java_path if inst and inst.java_path else self.settings.java_path)
        worker = LaunchWorker(
            self.store, account, version, game_dir,
            memory_mb=memory, java_path=java, store_root=self.store_root,
            quick_play=quick_play,
        )
        worker.instance_name = inst.name if inst else ""
        worker.started_ts = 0.0
        worker.game_started.connect(lambda w=worker: setattr(w, "started_ts", time.time()))
        worker.progress.connect(self._on_progress)
        worker.status.connect(self.window.set_status)
        worker.failed.connect(lambda m: self.window.set_status(f"Error: {m}"))
        worker.finished_ok.connect(self._launch_done)
        worker.game_started.connect(self._update_play_button)
        worker.log_line.connect(self._append_log)
        worker.finished.connect(lambda: self._launch_finished(worker))
        self._launches.append(worker)
        worker.start()
        # Worker đã chạy → isRunning() giữ trạng thái STOP; bỏ cờ tạm.
        self._launching = False
        self._update_play_button()

    def _append_log(self, line: str) -> None:
        self._log_lines.append(line)
        if len(self._log_lines) > 3000:
            del self._log_lines[:len(self._log_lines) - 3000]
        if self._log_dialog is not None:
            self._log_dialog.append_line(line)

    def show_logs(self) -> None:
        dlg = ReportDialog(self.window, "Game log",
                           "".join(self._log_lines)
                           or "No log yet — press PLAY to start a game.")
        self._log_dialog = dlg
        dlg.closed.connect(lambda: setattr(self, "_log_dialog", None))
        dlg.show()

    def _launch_done(self) -> None:
        self.window.set_status("Everything is up to date!")

    def _launch_finished(self, worker) -> None:
        # Ghi nhận thời gian chơi cho instance vừa thoát.
        started = getattr(worker, "started_ts", 0.0)
        name = getattr(worker, "instance_name", "")
        if started and name:
            self.instances.add_playtime(name, time.time() - started)
        if worker in self._launches:
            self._launches.remove(worker)
        self.pages["installations"].refresh()
        self._update_play_button()
        self.window.set_progress(None)
        left = self.running_count
        self.window.set_status(f"{left} instance(s) running" if left else "Ready")

    def _on_progress(self, stage: str, done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 0
        self.window.set_status(f"{stage} · {done:,} / {total:,} files ({pct}%)".replace(",", " "))
        self.window.set_progress(done / total if total else None)


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
