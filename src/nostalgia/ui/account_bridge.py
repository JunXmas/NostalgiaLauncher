"""Cầu nối trang TÀI KHOẢN: danh sách tài khoản kèm skin, cache trong bộ nhớ.

Trước đây mỗi lần QML đọc property `accounts` hoặc gọi `accountNamed()` đều chạy lại
`describe_skin()` cho MỌI tài khoản (đọc đĩa). QML binding gọi hai hàm đó 6-10 lần mỗi
render cycle → lag rõ rệt khi có 2+ tài khoản.

Giờ: cache `_cached_rows` (list) và `_by_name` (dict) trong RAM. Chỉ rebuild khi
`_invalidate()` được gọi (từ `accountsChanged` hoặc `_skinsRefreshed`). Lookup O(1).
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
    skinUploaded = Signal(str)
    skinUploadFailed = Signal(str)
    _skinsRefreshed = Signal()

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._cached_rows: list[dict[str, Any]] = []
        self._by_name: dict[str, dict[str, Any]] = {}
        self._dirty = True
        self._skinsRefreshed.connect(self._invalidate)
        self._skinsRefreshed.connect(self.skinsChanged)
        main_bridge.accountsChanged.connect(self._invalidate)
        main_bridge.accountsChanged.connect(self.refreshSkins)
        main_bridge.accountsChanged.connect(self.skinsChanged)

    def _invalidate(self) -> None:
        self._dirty = True

    def _ensure_cache(self) -> None:
        if not self._dirty:
            return
        rows = [_describe(self._launcher, a) for a in self._launcher.list_accounts()]
        self._cached_rows = rows
        self._by_name = {row["playerName"]: row for row in rows}
        self._dirty = False

    @Property(list, notify=skinsChanged)
    def accounts(self) -> list[dict[str, Any]]:
        self._ensure_cache()
        return self._cached_rows

    @Slot(str, result="QVariant")
    def accountNamed(self, player_name: str) -> dict[str, Any]:
        self._ensure_cache()
        return self._by_name.get(player_name, {})

    @Slot()
    def refreshSkins(self) -> None:
        """Tải skin mới cho Microsoft/Ely ở luồng nền."""
        accounts = self._launcher.list_accounts()
        if not any(a.account_kind in ("microsoft", "ely") for a in accounts):
            return

        def work() -> None:
            for account in accounts:
                self._launcher.refresh_skin(account)
            self._skinsRefreshed.emit()

        self.run_in_background(work, "Cập nhật skin")

    @Slot(str, str, bool)
    def uploadSkin(self, player_name: str, file_url: str, slim: bool) -> None:
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


def _describe(launcher: Launcher, account: Account) -> dict[str, Any]:
    try:
        skin = launcher.describe_skin(account)
    except NostalgiaError:
        return {"playerName": account.player_name, "skinFile": "", "capeFile": ""}
    cape = QUrl.fromLocalFile(str(skin.cape_path)).toString() if skin.cape_path else ""
    return {
        "playerName": account.player_name,
        "playerUuid": account.player_uuid,
        "accountKind": account.account_kind,
        "kindLabel": KIND_LABELS.get(account.account_kind, account.account_kind.upper()),
        "skinFile": _file_url(skin.skin_path),
        "capeFile": cape,
        "slim": skin.slim,
        "isDefaultSkin": skin.is_default,
    }


def _file_url(path: Path | None) -> str:
    return QUrl.fromLocalFile(str(path)).toString() if path is not None else ""
