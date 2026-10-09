"""Chọn skin/cape để xem trước, chỉ Lưu mới đổi dịch vụ; giữ phần chưa lưu khi lỗi."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.appearance_draft import AppearanceDraft, AppearanceResult
from nostalgia.ui.appearance_save import save_selection
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.cape_bridge import CapeBridge
from nostalgia.ui.skin_import import SkinImportBridge


class SkinEditBridge(SkinImportBridge):
    changed = Signal()
    skinSaved = Signal(str)
    capeSaved = Signal(str)
    saved = Signal(str)
    _arrived = Signal(object)

    def __init__(
        self, launcher: Launcher, main: LauncherBridge, accounts: AccountBridge, capes: CapeBridge
    ) -> None:
        super().__init__(accounts.parent())
        self._launcher, self._main, self._accounts, self._capes = launcher, main, accounts, capes
        self._account_id, self._note = "", ""
        self._drafts: dict[str, AppearanceDraft] = {}
        self._baselines: dict[str, AppearanceDraft] = {}
        accounts.skinsChanged.connect(self._refresh)
        accounts.libraryChanged.connect(self.changed)
        capes.capesChanged.connect(self._cape_list)
        self._arrived.connect(self._finish)
        self.imported.connect(self._import_finished)
        self.failed.connect(self._failure)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return self._details()

    def _details(self) -> dict[str, Any]:
        draft = self._drafts.get(self._account_id, AppearanceDraft())
        baseline = self._baselines.get(self._account_id, AppearanceDraft())
        skin_dirty = not draft.skin_matches(baseline)
        cape_dirty = draft.cape_id != baseline.cape_id
        return {
            "accountId": draft.account_id,
            "source": draft.source,
            "slim": draft.slim,
            "capeSource": draft.cape_source,
            "capeId": draft.cape_id,
            "entryId": draft.entry_id,
            "skinDirty": skin_dirty,
            "capeDirty": cape_dirty,
            "dirty": skin_dirty or cape_dirty,
            "note": self._note,
        }

    @Slot(str)
    def showAccount(self, account_id: str) -> None:
        if self._account_id != account_id:
            self._note = ""
        self._account_id = account_id
        self._refresh()

    def _refresh(self) -> None:
        row = self._accounts.accountWithId(self._account_id)
        if row and (self._account_id not in self._drafts or not self._details()["dirty"]):
            previous = self._baselines.get(self._account_id, AppearanceDraft())
            draft = AppearanceDraft(
                self._account_id,
                row.get("skinFile", ""),
                bool(row.get("slim")),
                previous.cape_source
                if row.get("accountKind") == "microsoft"
                and cast(str, self._capes.loadedFor) == self._account_id
                else row.get("capeFile", ""),
                previous.cape_id,
                row.get("skinDigest", ""),
            )
            self._drafts[self._account_id] = self._baselines[self._account_id] = draft
        self.changed.emit()

    def _cape_list(self) -> None:
        account_id = cast(str, self._capes.loadedFor)
        if (
            account_id not in self._drafts
            or self._accounts.accountWithId(account_id).get("accountKind") != "microsoft"
        ):
            return
        active = next(
            (cape for cape in cast(list[dict[str, Any]], self._capes.capes) if cape["active"]), {}
        )
        draft, baseline = self._drafts[account_id], self._baselines[account_id]
        if draft.cape_id == baseline.cape_id:
            updated = replace(
                draft,
                cape_id=active.get("capeId", ""),
                cape_source=active.get("textureFile", "") or draft.cape_source if active else "",
            )
            self._drafts[account_id] = updated
        self._baselines[account_id] = replace(
            baseline,
            cape_id=active.get("capeId", ""),
            cape_source=(active.get("textureFile", "") or baseline.cape_source) if active else "",
        )
        self.changed.emit()

    @Slot(str)
    def selectSkin(self, entry_id: str) -> None:
        if self.busy or self._account_id not in self._drafts:
            return
        skin_entry = next(
            (
                row
                for row in cast(list[dict[str, Any]], self._accounts.skinLibrary)
                if row["entryId"] == entry_id
            ),
            None,
        )
        if skin_entry:
            self._drafts[self._account_id] = replace(
                self._drafts[self._account_id],
                source=skin_entry["skinFile"],
                slim=skin_entry["slim"],
                entry_id=entry_id,
            )
            self._note = "Xem trước · Bấm Lưu để áp dụng."
            self.changed.emit()

    @Slot(bool)
    def setSlim(self, slim: bool) -> None:
        if not self.busy and self._account_id in self._drafts:
            self._drafts[self._account_id] = replace(self._drafts[self._account_id], slim=slim)
            self._note = "Xem trước · Bấm Lưu để áp dụng."
            self.changed.emit()

    @Slot(str)
    def selectCape(self, cape_id: str) -> None:
        if (
            self.busy
            or cast(str, self._capes.loadedFor) != self._account_id
            or self._account_id not in self._drafts
        ):
            return
        cape = next(
            (
                row
                for row in cast(list[dict[str, Any]], self._capes.capes)
                if row["capeId"] == cape_id
            ),
            None,
        )
        if cape_id and not cape:
            return
        self._drafts[self._account_id] = replace(
            self._drafts[self._account_id],
            cape_id=cape_id,
            cape_source=cape.get("textureFile", "") if cape else "",
        )
        self._note = "Xem trước · Bấm Lưu để áp dụng."
        self.changed.emit()

    @Slot()
    def discard(self) -> None:
        if not self.busy and self._account_id in self._baselines:
            self._drafts[self._account_id] = self._baselines[self._account_id]
            self._note = ""
            self.changed.emit()

    @Slot()
    def save(self) -> None:
        if self.busy or self._accounts.busy or self._capes.busy or not self._details()["dirty"]:
            return
        draft = self._drafts[self._account_id]
        account = next(
            (a for a in self._main.accounts_snapshot() if a.account_id == draft.account_id), None
        )
        if not account:
            self._failure("Tài khoản không còn trong launcher.")
            return
        skin_dirty, cape_dirty = self._details()["skinDirty"], self._details()["capeDirty"]

        def work() -> None:
            self._arrived.emit(
                save_selection(self._launcher, account, draft, skin_dirty, cape_dirty)
            )

        self.run_in_background(work, "Lưu skin và cape")

    def _finish(self, result: AppearanceResult) -> None:
        draft = result.draft
        baseline = self._baselines[draft.account_id]
        if result.skin_saved:
            baseline = replace(
                baseline, source=draft.source, slim=draft.slim, entry_id=draft.entry_id
            )
        if result.cape_saved:
            baseline = replace(baseline, cape_source=draft.cape_source, cape_id=draft.cape_id)
        self._baselines[draft.account_id] = baseline
        self._note = (
            ("Skin đã lưu; cape chưa lưu: " if result.skin_saved and result.error else "")
            + result.error
            if result.error
            else "Đã lưu diện mạo."
        )
        self.changed.emit()
        if result.skin_saved:
            self.skinSaved.emit(draft.account_id)
        if result.cape_saved:
            self._capes.rememberApplied(draft.account_id, draft.cape_id)
            self.capeSaved.emit(draft.account_id)
        if not result.error:
            self.saved.emit(draft.account_id)

    def _failure(self, message: str) -> None:
        self._note = message
        self.changed.emit()
