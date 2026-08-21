"""Chạy cài đặt + khởi động game ở luồng nền.

Tải assets mất vài phút; làm trên luồng UI thì cửa sổ đứng hình. Qt bắt buộc chỉ
luồng UI được đụng vào widget, nên worker chỉ phát signal, không tự vẽ gì.
"""

from __future__ import annotations

from pathlib import Path

import requests
from PySide6.QtCore import QThread, Signal

from .. import auth, google_auth
from ..accounts import OFFLINE, AccountStore, StoredAccount
from ..install import Installer
from ..launch import build_command, ensure_offline_libraries, launch_game_offline, run


class FnWorker(QThread):
    """Chạy một hàm chặn ở luồng nền rồi trả kết quả về luồng UI."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self) -> None:  # noqa: D102
        try:
            self.done.emit(self.fn())
        except Exception as e:  # noqa: BLE001 - lỗi mạng nào cũng chỉ là "không tải được"
            self.failed.emit(str(e))


class ProgressWorker(QThread):
    """Như FnWorker nhưng hàm nhận (on_progress, on_status) để báo tiến độ."""

    progress = Signal(int, int)   # đã xong, tổng
    status = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self) -> None:  # noqa: D102
        try:
            self.done.emit(self.fn(self.progress.emit, self.status.emit))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class LoginWorker(QThread):
    """Device code flow: phát mã ra UI trước, rồi chờ người dùng xác nhận trên web."""

    code_ready = Signal(str, str)   # verification_uri, user_code
    logged_in = Signal(object)      # auth.MinecraftSession
    failed = Signal(str)

    def __init__(self, client_id: str, parent=None):
        super().__init__(parent)
        self.client_id = client_id

    def run(self) -> None:  # noqa: D102
        try:
            flow = auth.request_device_code(self.client_id)
            self.code_ready.emit(flow["verification_uri"], flow["user_code"])
            tokens = auth.poll_for_token(
                self.client_id, flow["device_code"], flow["interval"], flow["expires_in"]
            )
            self.logged_in.emit(auth.complete_login(tokens))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class GoogleLinkWorker(QThread):
    """Mở trình duyệt rồi chờ Google trả mã về cổng loopback."""

    url_ready = Signal(str)
    linked = Signal(object)   # {"sub", "email", "name"}
    failed = Signal(str)

    def __init__(self, client_id: str, client_secret: str = "", parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.client_secret = client_secret

    def run(self) -> None:  # noqa: D102
        try:
            self.linked.emit(google_auth.login(
                self.client_id, self.client_secret, on_url=self.url_ready.emit
            ))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class LaunchWorker(QThread):
    progress = Signal(str, int, int)  # giai đoạn, đã xong, tổng
    status = Signal(str)
    failed = Signal(str)
    finished_ok = Signal()
    game_started = Signal()           # tiến trình game đã chạy -> đổi PLAY thành STOP
    log_line = Signal(str)            # từng dòng log game -> hiện trong app

    def __init__(self, store: AccountStore, account: StoredAccount, version: str,
                 game_dir: Path, memory_mb: int = 2048, java_path: str = "",
                 offline: bool = False, store_root: Path | None = None,
                 quick_play: dict | None = None, parent=None):
        super().__init__(parent)
        self.store = store
        self.account = account
        self.version = version
        self.game_dir = game_dir          # thư mục game của instance (mods/saves)
        self.store_root = store_root or game_dir   # kho versions/libraries/assets/runtime dùng chung
        self.memory_mb = memory_mb
        self.java_path = java_path
        self.offline = offline
        self.quick_play = quick_play      # vào thẳng server/thế giới (Quick Play)
        self._proc = None            # tiến trình game, để dừng khi bấm STOP
        self._cancelled = False      # bấm STOP khi còn đang tải/chuẩn bị

    def _capture(self, proc) -> None:
        self._proc = proc
        self.game_started.emit()

    def stop(self) -> None:
        """Bấm STOP: nếu game đã chạy thì kết thúc tiến trình; nếu còn đang tải/
        chuẩn bị thì đánh dấu huỷ để KHÔNG bật game lên sau khi tải xong."""
        self._cancelled = True
        self.requestInterruption()
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()

    def _launch_offline(self, installer: Installer, identity):
        if self._interrupted():
            return None
        return launch_game_offline(
            self.version, installer, identity,
            java=self.java_path or None,
            max_memory_mb=self.memory_mb,
            on_status=self.status.emit,
            on_start=self._capture,
            on_line=self.log_line.emit,
            quick_play=self.quick_play,
        )

    def _interrupted(self) -> bool:
        """Đã bấm STOP trong lúc chuẩn bị? Nếu có, báo và bỏ, đừng bật game."""
        if self._cancelled or self.isInterruptionRequested():
            self.status.emit("Stopped.")
            return True
        return False

    def _launch_online(self, installer: Installer, identity):
        self.status.emit(f"Preparing {self.version}…")
        meta = installer.install(self.version)
        if self._interrupted():
            return None

        # Tự tải JRE Mojang nếu người dùng chưa đặt đường dẫn Java và máy chưa có.
        if not self.java_path:
            from .. import jre
            if not jre.is_installed(self.store_root, jre.component_of(meta)):
                self.status.emit("Downloading Java runtime…")
                jre.ensure(self.store_root, meta, on_progress=self.progress.emit)

        if identity.user_type == OFFLINE:
            for warning in ensure_offline_libraries(meta, installer):
                self.status.emit(warning)

        if self._interrupted():   # có thể vừa bấm STOP trong lúc tải JRE
            return None

        cmd = build_command(meta, installer, identity,
                            java=self.java_path or None, max_memory_mb=self.memory_mb,
                            quick_play=self.quick_play)
        self.status.emit(f"Launching {self.version}" + (" (demo)" if identity.demo else ""))
        return run(cmd, self.game_dir, on_start=self._capture, on_line=self.log_line.emit)

    def run(self) -> None:  # noqa: D102
        try:
            identity = self.store.resolve_identity(self.account)
            installer = Installer(self.game_dir, on_progress=self.progress.emit,
                                  store_root=self.store_root)

            if self.offline:
                code = self._launch_offline(installer, identity)
            else:
                try:
                    code = self._launch_online(installer, identity)
                except requests.exceptions.RequestException:
                    # Mất mạng giữa chừng: những gì đã tải vẫn đủ chơi đơn và LAN.
                    self.status.emit("No connection — using what is already downloaded…")
                    code = self._launch_offline(installer, identity)

            if code is None:      # đã bấm STOP khi đang tải/chuẩn bị → huỷ lặng lẽ
                return
            # Bấm STOP hoặc bị reap (kill/đóng stdout) thì mã thoát khác 0 là bình
            # thường — đừng báo lỗi.
            if code != 0 and not self._cancelled:
                self.failed.emit(f"Game exited with code {code}")
                return
            self.finished_ok.emit()
        except Exception as e:  # noqa: BLE001 - lỗi nào cũng phải hiện lên UI
            self.failed.emit(str(e))
