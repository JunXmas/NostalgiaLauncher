"""Cầu nối tab Cape: liệt kê cape sở hữu (chỉ Microsoft) và mặc/gỡ ngay trong launcher.

Bridge riêng thay vì nhét vào `AccountBridge`: file đó đã sát trần 200 dòng, và cape là
việc độc lập — danh sách tải theo yêu cầu (bấm tab Cape mới CHẠM MẠNG), không đi cùng nhịp
làm mới skin.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from nostalgia.account.model import MICROSOFT, Account
from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)


class CapeBridge(WorkerBridge):
    capesChanged = Signal()
    capeApplied = Signal(str)
    capeFailed = Signal(str)
    _loaded = Signal(int, str, object)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._capes: list[dict[str, Any]] = []
        self._loaded_for = ""  # account_id của lần tải gần nhất — đổi tài khoản thì tải lại
        self._loaded.connect(self._finish_load)

    @Property(list, notify=capesChanged)
    def capes(self) -> list[dict[str, Any]]:
        return self._capes

    @Property(str, notify=capesChanged)
    def loadedFor(self) -> str:
        return self._loaded_for

    @Slot(str)
    def loadCapes(self, account_id: str) -> None:
        """Tải danh sách cape của một tài khoản. Gọi khi mở tab Cape — không tải trước."""
        account = self._find_account(account_id)
        generation = self.next_generation()
        if account is None or account.account_kind != MICROSOFT:
            self._capes = []
            self._loaded_for = account_id
            self.capesChanged.emit()
            return

        def work() -> None:
            try:
                owned = self._launcher.list_capes(account)
            except NostalgiaError as exc:
                logger.warning("không đọc được cape cho %s: %s", account_id, exc)
                self.capeFailed.emit(str(exc))
                return
            rows = []
            for cape in owned:
                texture_file = ""
                try:
                    path = self._launcher.cache_cape_texture(cape)
                    if path:
                        texture_file = QUrl.fromLocalFile(str(path)).toString()
                except (NostalgiaError, OSError):
                    pass
                rows.append(
                    {
                        "capeId": cape.cape_id,
                        "alias": cape.alias or "Cape",
                        "textureUrl": cape.texture_url,
                        "active": cape.active,
                        "textureFile": texture_file,
                    }
                )
            self._loaded.emit(generation, account_id, rows)

        self.run_in_background(work, "Đọc cape")

    def _finish_load(self, generation: int, account_id: str, rows: list[dict[str, Any]]) -> None:
        if self.is_current(generation):
            self._capes, self._loaded_for = rows, account_id
            self.capesChanged.emit()

    def rememberApplied(self, account_id: str, cape_id: str) -> None:
        """API vừa xác nhận lưu: cập nhật cờ tại chỗ, không gọi lại danh sách có thể còn cũ."""
        if self._loaded_for == account_id:
            self._capes = [{**cape, "active": cape["capeId"] == cape_id} for cape in self._capes]
            self.capesChanged.emit()

    @Slot(str, str)
    def applyCape(self, account_id: str, cape_id: str) -> None:
        """Mặc cape (``cape_id`` rỗng = gỡ). Xong thì tải lại danh sách để cờ active khớp."""
        account = self._find_account(account_id)
        if account is None:
            self.capeFailed.emit(f"không tìm thấy tài khoản {account_id}")
            return

        def work() -> None:
            try:
                self._launcher.set_cape(account, cape_id)
            except NostalgiaError as exc:
                logger.warning("đổi cape thất bại cho %s: %s", account_id, exc)
                self.capeFailed.emit(str(exc))
                return
            self.capeApplied.emit(account_id)
            self.loadCapes(account_id)

        self.run_in_background(work, "Đổi cape")

    def _find_account(self, account_id: str) -> Account | None:
        return next(
            (a for a in self._main_bridge.accounts_snapshot() if a.account_id == account_id),
            None,
        )
