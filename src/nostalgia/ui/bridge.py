"""Cầu nối chính giữa QML và lõi: tài khoản, chơi game, nhật ký game (phần bản chơi và tiến
độ nằm ở `instance_bridge.py`, cùng một đối tượng `bridge` với QML).

Các cầu nối trong `ui/` là những file DUY NHẤT chạm vào `nostalgia.api`. Khi lõi đổi, chỉ
chúng phải sửa, còn QML thì không. Kho tiền nhiệm không làm vậy — giao diện gọi thẳng sáu
module lõi, và mỗi lần lõi đổi là giao diện gãy theo.
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.account.model import Account
from nostalgia.api import Launcher
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.game_log import GameLogFeed, describe_game_failure
from nostalgia.ui.instance_bridge import InstanceBridge


class LauncherBridge(InstanceBridge):
    """Bề mặt mà QML nhìn thấy: vài thuộc tính đọc được, vài lệnh gọi được, và tín hiệu."""

    accountsChanged = Signal()
    gameStarted = Signal(str)
    gameStopped = Signal(int)
    gameRunningChanged = Signal()
    # Đăng nhập Microsoft: mã để người dùng gõ trên trang của Microsoft, rồi kết quả.
    deviceCodeReady = Signal(str, str)
    signInFinished = Signal(str)
    activeAccountChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(launcher, parent)
        self._active_player_name = ""
        self._sign_in_cancel: CancelToken | None = None
        self._game_running = False
        # Kho tài khoản đọc từ đĩa MỘT lần rồi giữ trong RAM. Trước đây mỗi binding QML đọc
        # `accounts`/`activePlayerName` là một lần đọc + parse accounts.json — một cú bấm chọn
        # tài khoản kéo theo 11 lần đọc, thêm tài khoản 26 lần (đo bằng harness).
        self._accounts: tuple[Account, ...] | None = None
        # Nhật ký game: luồng đọc output đổ vào đây, trang NHẬT KÝ đọc model của nó.
        self._game_log = GameLogFeed(self)
        # `play` chạy ở luồng nền; timer gom lô phải bật/tắt ở luồng giao diện → đi qua tín hiệu.
        self.gameRunningChanged.connect(self._sync_game_log_session)

    # ----- kho tài khoản trong RAM -----

    def accounts_snapshot(self) -> tuple[Account, ...]:
        """Danh sách tài khoản hiện tại; chỉ chạm đĩa khi chưa có hoặc vừa có thay đổi."""
        if self._accounts is None:
            self._accounts = self._launcher.list_accounts()
        return self._accounts

    def announce_accounts_changed(self) -> None:
        """Gọi sau MỌI thay đổi kho tài khoản (kể cả từ cầu nối khác): quên bản trong RAM
        rồi mới báo, để binding nào đọc lại cũng thấy dữ liệu mới."""
        self._accounts = None
        self.accountsChanged.emit()
        self.activeAccountChanged.emit()

    # ----- thuộc tính cho QML -----

    @Property(list, notify=accountsChanged)
    def accounts(self) -> list[dict[str, Any]]:
        return [
            {
                "playerName": account.player_name,
                "playerUuid": account.player_uuid,
                "accountKind": account.account_kind,
            }
            for account in self.accounts_snapshot()
        ]

    @Property(str, notify=activeAccountChanged)
    def activePlayerName(self) -> str:
        """Tài khoản sẽ dùng khi bấm CHƠI: cái người dùng chọn, không thì cái đầu danh sách."""
        names = [account.player_name for account in self.accounts_snapshot()]
        if self._active_player_name in names:
            return self._active_player_name
        return names[0] if names else ""

    @Slot(str)
    def setActiveAccount(self, player_name: str) -> None:
        self._active_player_name = player_name
        self.activeAccountChanged.emit()

    @Property(QObject, constant=True)
    def gameLog(self) -> GameLogFeed:
        return self._game_log

    @Property(bool, notify=gameRunningChanged)
    def gameRunning(self) -> bool:
        """Game đang chạy: cầu nối vẫn bận (chờ tiến trình) nhưng popup loading không hiện."""
        return self._game_running

    # ----- lệnh từ QML -----

    @Slot(str)
    def addOfflineAccount(self, player_name: str) -> None:
        def work() -> None:
            self._launcher.add_offline_account(player_name)
            self._active_player_name = player_name
            self.announce_accounts_changed()

        self.run_in_background(work, "Thêm tài khoản")

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
            self.announce_accounts_changed()
            self.signInFinished.emit(account.player_name)

        self.run_in_background(work, "Đăng nhập Microsoft — chờ bạn nhập mã")

    @Slot()
    def cancelSignIn(self) -> None:
        if self._sign_in_cancel is not None:
            self._sign_in_cancel.cancel()

    @Slot(str)
    def removeAccount(self, player_name: str) -> None:
        def work() -> None:
            self._launcher.remove_account(player_name)
            self.announce_accounts_changed()

        self.run_in_background(work, f"Gỡ tài khoản {player_name}")

    @Slot(str)
    def play(self, instance_id: str) -> None:
        """Chơi bằng tài khoản đang hoạt động."""
        player_name = str(self.activePlayerName)

        def work() -> None:
            # Bù phần thiếu TRƯỚC khi chạy: bản cài hụt một jar thì JVM chết ngay với mã 1 và
            # không để lại log nào (đã xảy ra với Fabric thiếu fabric-loader). Đủ rồi thì bước
            # này chỉ mất ~1 giây soi kích thước file.
            version_id = next(
                (
                    i.version_id
                    for i in self._launcher.list_instances()
                    if i.instance_id == instance_id
                ),
                "",
            )
            if version_id:
                self._launcher.install_version(version_id, on_progress=self.report_progress)
            # Output của game đổ vào nhật ký; đuôi của nó là bằng chứng khi game chết.
            self._game_log.reset()
            game = self._launcher.launch_instance(
                instance_id, player_name, on_output=self._game_log.receive
            )
            started_at = time.time()
            self._set_game_running(True)
            self.gameStarted.emit(instance_id)
            try:
                exit_code = game.wait()
            finally:
                self._set_game_running(False)
            # Thống kê: cộng phiên chơi rồi báo danh sách đổi để thẻ bản chơi cập nhật số liệu.
            self._launcher.record_play_session(instance_id, started_at, time.time())
            self.instancesChanged.emit()
            self.gameStopped.emit(exit_code)
            if exit_code != 0:
                self.failed.emit(describe_game_failure(exit_code, self._game_log.tail))

        self.run_in_background(work, f"Khởi động {instance_id}")

    # ----- nội bộ -----

    @Slot()
    def _sync_game_log_session(self) -> None:
        if self._game_running:
            self._game_log.begin_session()
        else:
            self._game_log.end_session()

    def _set_game_running(self, running: bool) -> None:
        self._game_running = running
        self.gameRunningChanged.emit()
