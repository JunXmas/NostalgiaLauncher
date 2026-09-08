"""Cầu nối trang TÀI KHOẢN: tài khoản kèm skin/cape, làm mới và upload skin, đăng nhập Ely.by.

Danh sách gốc nằm ở `LauncherBridge.accounts_snapshot()` (đọc đĩa một lần). Ở đây ghép thêm
lớp skin (đường dẫn file để QML cắt vùng UV) và giữ kết quả trong RAM: chỉ dựng lại khi kho
tài khoản đổi hoặc vừa tải skin xong, và nhiều tín hiệu tới trong cùng một nhịp được gộp thành
MỘT lần `skinsChanged` cho QML. Skin chỉ tự tải cho tài khoản CHƯA có cache; nút "Làm mới"
mới tải lại tất cả — thêm một tài khoản không phải là lý do để chạm mạng cho mọi tài khoản.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError, TwoFactorRequired
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)

KIND_LABELS = {MICROSOFT: "MICROSOFT", ELY: "ELY.BY", "offline": "NGOẠI TUYẾN"}
ONLINE_KINDS = (MICROSOFT, ELY)


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
        self._rows: list[dict[str, Any]] = []
        self._row_by_name: dict[str, dict[str, Any]] = {}
        self._stale = True
        # Gộp tín hiệu: mọi thay đổi chỉ đánh dấu cũ và khởi timer; timer 0 ms bắn một lần ở
        # cuối nhịp sự kiện, nên QML dựng lại danh sách đúng một lần dù nhiều tín hiệu tới.
        self._notify_timer = QTimer(self)
        self._notify_timer.setSingleShot(True)
        self._notify_timer.timeout.connect(self.skinsChanged)
        self._skinsRefreshed.connect(self._mark_stale)
        main_bridge.accountsChanged.connect(self._mark_stale)
        main_bridge.accountsChanged.connect(self._fetch_missing_skins)

    # ----- danh sách cho QML -----

    def _mark_stale(self) -> None:
        self._stale = True
        self._notify_timer.start(0)

    def _ensure_rows(self) -> None:
        if not self._stale:
            return
        self._rows = [_describe(self._launcher, a) for a in self._main_bridge.accounts_snapshot()]
        self._row_by_name = {row["playerName"]: row for row in self._rows}
        self._stale = False

    @Property(list, notify=skinsChanged)
    def accounts(self) -> list[dict[str, Any]]:
        self._ensure_rows()
        return self._rows

    @Slot(str, result="QVariant")
    def accountNamed(self, player_name: str) -> dict[str, Any]:
        self._ensure_rows()
        return self._row_by_name.get(player_name, {})

    # ----- skin: tải về cache ở luồng nền -----

    @Slot()
    def refreshSkins(self) -> None:
        """Nút "Làm mới": tải lại skin của MỌI tài khoản Microsoft/Ely.by."""
        self._fetch_skins(self._online_accounts(), "Cập nhật skin")

    def _fetch_missing_skins(self) -> None:
        """Kho tài khoản vừa đổi: chỉ tải cho tài khoản chưa có skin trong cache."""
        missing = [a for a in self._online_accounts() if self._launcher.describe_skin(a).is_default]
        self._fetch_skins(missing, "Tải skin")

    def _online_accounts(self) -> list[Account]:
        return [a for a in self._main_bridge.accounts_snapshot() if a.account_kind in ONLINE_KINDS]

    def _fetch_skins(self, accounts: Iterable[Account], activity: str) -> None:
        wanted = list(accounts)
        if not wanted:
            return

        def work() -> None:
            for account in wanted:
                self._launcher.refresh_skin(account)
            self._skinsRefreshed.emit()

        self.run_in_background(work, activity)

    @Slot(str, str, bool)
    def uploadSkin(self, player_name: str, file_url: str, slim: bool) -> None:
        skin_path = Path(QUrl(file_url).toLocalFile())
        account = next(
            (a for a in self._main_bridge.accounts_snapshot() if a.player_name == player_name),
            None,
        )
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

    # ----- Ely.by -----

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
            self._main_bridge.announce_accounts_changed()
            self.elySignedIn.emit(account.player_name)

        self.run_in_background(work, "Đăng nhập Ely.by")


def _describe(launcher: Launcher, account: Account) -> dict[str, Any]:
    try:
        skin = launcher.describe_skin(account)
    except NostalgiaError:
        return {"playerName": account.player_name, "skinFile": "", "capeFile": ""}
    return {
        "playerName": account.player_name,
        "playerUuid": account.player_uuid,
        "accountKind": account.account_kind,
        "kindLabel": KIND_LABELS.get(account.account_kind, account.account_kind.upper()),
        "skinFile": _file_url(skin.skin_path),
        "capeFile": _file_url(skin.cape_path),
        "slim": skin.slim,
        "isDefaultSkin": skin.is_default,
    }


def _file_url(path: Path | None) -> str:
    return QUrl.fromLocalFile(str(path)).toString() if path is not None else ""
