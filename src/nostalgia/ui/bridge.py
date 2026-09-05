"""Cầu nối giữa QML và lõi. Đây là **file duy nhất** trong `ui/` chạm vào `nostalgia.api`.

Gom một chỗ có lý do: khi lõi đổi, chỉ file này phải sửa, còn hàng nghìn dòng QML thì không.
Kho tiền nhiệm không làm vậy — giao diện của nó gọi thẳng vào sáu module lõi, và mỗi lần lõi
đổi một chi tiết là giao diện gãy theo.

Mọi việc dài (tải, đăng nhập, chạy game) **không được chặn luồng vẽ**: chúng chạy ở luồng nền
và báo về bằng tín hiệu. Một giao diện đứng hình vì đang tải 3.629 file là giao diện hỏng.
"""

from __future__ import annotations

import threading
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.operations.progress import Progress


class LauncherBridge(QObject):
    """Bề mặt mà QML nhìn thấy: vài thuộc tính đọc được, vài lệnh gọi được, và tín hiệu."""

    instancesChanged = Signal()
    accountsChanged = Signal()
    busyChanged = Signal()
    progressChanged = Signal()
    failed = Signal(str)
    gameStarted = Signal(str)
    gameStopped = Signal(int)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._busy = False
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

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

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
        self._run_in_background(lambda: self._install(version_id))

    @Slot(str, str)
    def createInstance(self, instance_id: str, version_id: str) -> None:
        from nostalgia.instance.model import Instance

        def work() -> None:
            self._launcher.create_instance(Instance(instance_id=instance_id, version_id=version_id))
            self.instancesChanged.emit()

        self._run_in_background(work)

    @Slot(str)
    def addOfflineAccount(self, player_name: str) -> None:
        def work() -> None:
            self._launcher.add_offline_account(player_name)
            self.accountsChanged.emit()

        self._run_in_background(work)

    @Slot(str, str)
    def play(self, instance_id: str, player_name: str) -> None:
        def work() -> None:
            game = self._launcher.launch_instance(instance_id, player_name)
            self.gameStarted.emit(instance_id)
            self.gameStopped.emit(game.wait())

        self._run_in_background(work)

    # ----- phần nền -----

    def _install(self, version_id: str) -> None:
        self._launcher.install_version(version_id, on_progress=self._report)
        self.instancesChanged.emit()

    def _report(self, progress: Progress) -> None:
        self._progress_text = f"{progress.stage} {progress.done}/{progress.total}"
        self._progress_fraction = progress.fraction
        self.progressChanged.emit()

    def _run_in_background(self, work: object) -> None:
        """Chạy một việc dài, báo lỗi ra giao diện thay vì để nó chết lặng trong luồng nền."""

        def guarded() -> None:
            try:
                work()  # type: ignore[operator]
            except NostalgiaError as error:
                self.failed.emit(str(error))
            except Exception as error:
                self.failed.emit(f"lỗi không lường trước: {error}")
            finally:
                self._set_busy(False)

        self._set_busy(True)
        threading.Thread(target=guarded, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()
