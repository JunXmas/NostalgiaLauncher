"""Cầu nối chính giữa QML và lõi: bản chơi, tài khoản, chơi, tải phiên bản.

Ba cầu nối (`bridge`, `content`, `catalog`) là những file DUY NHẤT trong `ui/` chạm vào
`nostalgia.api`. Khi lõi đổi, chỉ chúng phải sửa, còn QML thì không. Kho tiền nhiệm không làm
vậy — giao diện gọi thẳng sáu module lõi, và mỗi lần lõi đổi là giao diện gãy theo.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.operations.progress import Progress
from nostalgia.ui.worker import WorkerBridge


class LauncherBridge(WorkerBridge):
    """Bề mặt mà QML nhìn thấy: vài thuộc tính đọc được, vài lệnh gọi được, và tín hiệu."""

    instancesChanged = Signal()
    accountsChanged = Signal()
    progressChanged = Signal()
    gameStarted = Signal(str)
    gameStopped = Signal(int)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._progress_text = ""
        self._progress_fraction = 0.0

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
            self.accountsChanged.emit()

        self.run_in_background(work)

    @Slot(str, str)
    def play(self, instance_id: str, player_name: str) -> None:
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
