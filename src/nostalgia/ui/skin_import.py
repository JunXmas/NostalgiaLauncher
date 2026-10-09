"""Nhập PNG vào kho và bản xem trước; không upload hoặc đổi skin đang mặc."""

from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QUrl, Signal, Slot
from PySide6.QtGui import QImageReader

from nostalgia.api import Launcher
from nostalgia.errors import SkinError
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.appearance_draft import AppearanceDraft
from nostalgia.ui.worker import WorkerBridge


def import_preview(launcher: Launcher, file_url: str) -> AppearanceDraft:
    path = Path(QUrl(file_url).toLocalFile())
    reader = QImageReader(str(path), b"png")
    if (
        path.stat().st_size > 256 * 1024
        or reader.size().width() != 64
        or reader.size().height() not in (32, 64)
        or reader.read().isNull()
    ):
        raise SkinError("Chọn ảnh skin PNG 64x64 hoặc 64x32 hợp lệ.")
    skin_entry = launcher.import_skin(path)
    return AppearanceDraft(
        source=QUrl.fromLocalFile(str(skin_entry.skin_path)).toString(),
        slim=skin_entry.slim,
        entry_id=skin_entry.entry_id,
    )


class SkinImportBridge(WorkerBridge):
    changed: Signal
    imported = Signal(str, str, bool)
    _launcher: Launcher
    _accounts: AccountBridge
    _account_id: str
    _note: str
    _drafts: dict[str, AppearanceDraft]

    @Slot(str)
    def importSkin(self, file_url: str) -> None:
        if self.busy or not QUrl(file_url).isLocalFile():
            return
        account_id = self._account_id

        def work() -> None:
            draft = import_preview(self._launcher, file_url)
            self.imported.emit(account_id, draft.entry_id, draft.slim)

        self.run_in_background(work, "Nhập skin để xem trước")

    def _import_finished(self, account_id: str, entry_id: str, slim: bool) -> None:
        self._accounts.libraryChanged.emit()
        row = next(
            (
                row
                for row in cast(list[dict[str, Any]], self._accounts.skinLibrary)
                if row["entryId"] == entry_id
            ),
            None,
        )
        if row and account_id in self._drafts:
            self._drafts[account_id] = replace(
                self._drafts[account_id], source=row["skinFile"], slim=slim, entry_id=entry_id
            )
            if account_id == self._account_id:
                self._note = "Xem trước · Bấm Lưu để áp dụng."
            self.changed.emit()
