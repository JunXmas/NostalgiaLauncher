"""Cầu nối chính giữa QML và lõi: bản chơi, tài khoản, chơi, tải phiên bản.

Ba cầu nối (`bridge`, `content`, `catalog`) là những file DUY NHẤT trong `ui/` chạm vào
`nostalgia.api`. Khi lõi đổi, chỉ chúng phải sửa, còn QML thì không. Kho tiền nhiệm không làm
vậy — giao diện gọi thẳng sáu module lõi, và mỗi lần lõi đổi là giao diện gãy theo.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress
from nostalgia.ui.worker import WorkerBridge


class LauncherBridge(WorkerBridge):
    """Bề mặt mà QML nhìn thấy: vài thuộc tính đọc được, vài lệnh gọi được, và tín hiệu."""

    instancesChanged = Signal()
    accountsChanged = Signal()
    progressChanged = Signal()
    gameStarted = Signal(str)
    gameStopped = Signal(int)
    # Đăng nhập Microsoft: mã để người dùng gõ trên trang của Microsoft, rồi kết quả.
    deviceCodeReady = Signal(str, str)
    signInFinished = Signal(str)
    activeAccountChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._progress_text = ""
        self._progress_fraction = 0.0
        self._active_player_name = ""
        self._sign_in_cancel: CancelToken | None = None

    # ----- thuộc tính cho QML -----

    @Property(list, notify=instancesChanged)
    def instances(self) -> list[dict[str, Any]]:
        """Danh sách bản chơi, đã đổi sang dạng QML đọc được."""
        return [
            {
                "instanceId": instance.instance_id,
                "label": instance.label,
                "versionId": instance.version_id,
            }
            for instance in self._launcher.list_instances()
        ]

    @Property(list, notify=accountsChanged)
    def accounts(self) -> list[dict[str, Any]]:
        return [
            {
                "playerName": account.player_name,
                "playerUuid": account.player_uuid,
                "accountKind": account.account_kind,
            }
            for account in self._launcher.list_accounts()
        ]

    @Property(str, notify=activeAccountChanged)
    def activePlayerName(self) -> str:
        """Tài khoản sẽ dùng khi bấm CHƠI: cái người dùng chọn, không thì cái đầu danh sách."""
        names = [account.player_name for account in self._launcher.list_accounts()]
        if self._active_player_name in names:
            return self._active_player_name
        return names[0] if names else ""

    @Slot(str)
    def setActiveAccount(self, player_name: str) -> None:
        self._active_player_name = player_name
        self.activeAccountChanged.emit()

    @Property(list, notify=instancesChanged)
    def installedVersions(self) -> list[str]:
        """Các phiên bản đã tải về máy. Đọc đĩa, không chạm mạng."""
        return list(self._launcher.list_installed_versions())

    @Property(str, notify=progressChanged)
    def progressText(self) -> str:
        return self._progress_text

    @Property(float, notify=progressChanged)
    def progressFraction(self) -> float:
        return self._progress_fraction

    # ----- lệnh từ QML -----

    @Slot(str)
    def installVersion(self, version_id: str) -> None:
        """Tải một phiên bản ở luồng nền; giao diện vẫn vẽ được trong lúc đó."""

        def work() -> None:
            self._launcher.install_version(version_id, on_progress=self.report_progress)
            self.instancesChanged.emit()

        self.run_in_background(work)

    @Slot(str)
    def removeInstance(self, instance_id: str) -> None:
        """Gỡ đăng ký bản chơi; thư mục thế giới vẫn còn nguyên trên đĩa."""

        def work() -> None:
            self._launcher.remove_instance(instance_id)
            self.instancesChanged.emit()

        self.run_in_background(work)

    @Slot(str)
    def addOfflineAccount(self, player_name: str) -> None:
        def work() -> None:
            self._launcher.add_offline_account(player_name)
            self._active_player_name = player_name
            self.accountsChanged.emit()
            self.activeAccountChanged.emit()

        self.run_in_background(work)

    @Slot()
    def signInMicrosoft(self) -> None:
        """Luồng mã thiết bị: mã đi ra `deviceCodeReady`, kết quả đi ra `signInFinished`."""
        cancel_token = CancelToken()
        self._sign_in_cancel = cancel_token

        def work() -> None:
            try:
                account = self._launcher.add_microsoft_account(
                    on_device_code=lambda code: self.deviceCodeReady.emit(
                        code.user_code, code.verification_url
                    ),
                    cancel_token=cancel_token,
                )
            finally:
                self._sign_in_cancel = None
            self._active_player_name = account.player_name
            self.accountsChanged.emit()
            self.activeAccountChanged.emit()
            self.signInFinished.emit(account.player_name)

        self.run_in_background(work)

    @Slot()
    def cancelSignIn(self) -> None:
        if self._sign_in_cancel is not None:
            self._sign_in_cancel.cancel()

    @Slot(str)
    def removeAccount(self, player_name: str) -> None:
        def work() -> None:
            self._launcher.remove_account(player_name)
            self.accountsChanged.emit()
            self.activeAccountChanged.emit()

        self.run_in_background(work)

    @Slot(str)
    def play(self, instance_id: str) -> None:
        """Chơi bằng tài khoản đang hoạt động."""
        player_name = str(self.activePlayerName)

        def work() -> None:
            game = self._launcher.launch_instance(instance_id, player_name)
            self.gameStarted.emit(instance_id)
            self.gameStopped.emit(game.wait())

        self.run_in_background(work)

    # ----- dùng chung với các cầu nối khác -----

    def report_progress(self, progress: Progress) -> None:
        self._progress_text = f"{progress.stage} {progress.done}/{progress.total}"
        self._progress_fraction = progress.fraction
        self.progressChanged.emit()
