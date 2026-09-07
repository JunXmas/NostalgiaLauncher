"""Cầu nối trang TÀI KHOẢN: skin/cape của từng tài khoản và đăng nhập Ely.by.

Danh sách tài khoản gốc vẫn ở `LauncherBridge.accounts`; ở đây thêm lớp skin (đường dẫn file
trên đĩa để QML cắt vùng UV) và làm mới skin ở luồng nền mỗi khi danh sách đổi.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from nostalgia.account.model import Account
from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError, TwoFactorRequired
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)

KIND_LABELS = {"microsoft": "MICROSOFT", "ely": "ELY.BY", "offline": "NGOẠI TUYẾN"}


class AccountBridge(WorkerBridge):
    skinsChanged = Signal()
    elySignedIn = Signal(str)
    twoFactorRequired = Signal()
    skinUploaded = Signal(str)   # playerName — upload thành công
    skinUploadFailed = Signal(str)  # thông báo lỗi
    _skinsRefreshed = Signal()

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._skinsRefreshed.connect(self.skinsChanged)
        main_bridge.accountsChanged.connect(self.refreshSkins)
        main_bridge.accountsChanged.connect(self.skinsChanged)

    @Property(list, notify=skinsChanged)
    def accounts(self) -> list[dict[str, Any]]:
        """Tài khoản kèm skin: đọc cache trên đĩa, chưa có thì Steve/Alex — vẽ được ngay."""
        return self._rows()

    @Slot(str, result="QVariant")
    def accountNamed(self, player_name: str) -> dict[str, Any]:
        for row in self._rows():
            if row["playerName"] == player_name:
                return row
        return {}

    def _rows(self) -> list[dict[str, Any]]:
        return [self._describe(account) for account in self._launcher.list_accounts()]

    @Slot()
    def refreshSkins(self) -> None:
        """Tải skin mới cho Microsoft/Ely ở luồng nền; lỗi mạng không làm phiền người dùng."""
        accounts = self._launcher.list_accounts()
        if not any(account.account_kind in ("microsoft", "ely") for account in accounts):
            return

        def work() -> None:
            for account in accounts:
                self._launcher.refresh_skin(account)
            self._skinsRefreshed.emit()

        self.run_in_background(work, "Cập nhật skin")

    @Slot(str, str, bool)
    def uploadSkin(self, player_name: str, file_url: str, slim: bool) -> None:
        """Upload skin PNG lên Mojang cho tài khoản Microsoft đang chọn."""
        skin_path = Path(QUrl(file_url).toLocalFile())
        accounts = self._launcher.list_accounts()
        account = next((a for a in accounts if a.player_name == player_name), None)
        if account is None:
            self.skinUploadFailed.emit(f"không tìm thấy tài khoản {player_name}")
            return

        def work() -> None:
            try:
                self._launcher.upload_skin(account, skin_path, slim=slim)
                self._skinsRefreshed.emit()
                self.skinUploaded.emit(player_name)
            except NostalgiaError as exc:
                logger.warning("upload skin thất bại cho %s: %s", player_name, exc)
                self.skinUploadFailed.emit(str(exc))

        self.run_in_background(work, "Upload skin")

    @Slot(str, str, str)
    def signInEly(self, email_or_name: str, password: str, totp_code: str) -> None:
        """Mật khẩu chỉ đi thẳng vào lõi rồi lên Ely.by, không giữ lại ở đâu."""

        def work() -> None:
            try:
                account = self._launcher.add_ely_account(
                    email_or_name.strip(), password, totp_code=totp_code
                )
            except TwoFactorRequired:
                self.twoFactorRequired.emit()
                return
            self._main_bridge.setActiveAccount(account.player_name)
            self._main_bridge.accountsChanged.emit()
            self.elySignedIn.emit(account.player_name)

        self.run_in_background(work, "Đăng nhập Ely.by")

    def _describe(self, account: Account) -> dict[str, Any]:
        try:
            skin = self._launcher.describe_skin(account)
        except NostalgiaError:
            return {"playerName": account.player_name, "skinFile": "", "capeFile": ""}
        return {
            "playerName": account.player_name,
            "playerUuid": account.player_uuid,
            "accountKind": account.account_kind,
            "kindLabel": KIND_LABELS.get(account.account_kind, account.account_kind.upper()),
            "skinFile": _file_url(skin.skin_path),
            "capeFile": QUrl.fromLocalFile(str(skin.cape_path)).toString()
            if skin.cape_path
            else "",
            "slim": skin.slim,
            "isDefaultSkin": skin.is_default,
        }


def _file_url(path: Path | None) -> str:
    return QUrl.fromLocalFile(str(path)).toString() if path is not None else ""
