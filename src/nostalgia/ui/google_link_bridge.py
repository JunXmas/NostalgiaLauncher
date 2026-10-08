"""Lời mời liên kết sau đăng nhập Minecraft; chỉ lưu lựa chọn UI, không cấp quyền."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.social_bridge import SocialBridge


class GoogleLinkBridge(QObject):
    changed = Signal()

    def __init__(
        self,
        launcher: Launcher,
        main_bridge: LauncherBridge,
        accounts: AccountBridge,
        social: SocialBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._social = social
        self._pending = False
        self._provider = ""
        try:
            self._reviewed = launcher.load_google_link_reviewed()
        except (NostalgiaError, OSError):
            self._reviewed = False
        main_bridge.signInFinished.connect(self._microsoft_finished)
        accounts.elySignedIn.connect(self._ely_finished)
        social.changed.connect(self._social_changed)

    @Property(bool, notify=changed)
    def pending(self) -> bool:
        return self._pending

    @Property(str, notify=changed)
    def provider(self) -> str:
        return self._provider

    @Slot(str)
    def _microsoft_finished(self, _player_name: str) -> None:
        self._offer("Microsoft")

    @Slot(str)
    def _ely_finished(self, _player_name: str) -> None:
        self._offer("Ely.by")

    def _offer(self, provider: str) -> None:
        if self._reviewed or self._social.signedIn:
            return
        self._provider = provider
        self._pending = True
        self.changed.emit()

    @Slot()
    def defer(self) -> None:
        if not self._pending:
            return
        self._social.cancelSignIn()
        self._remember()

    @Slot()
    def _social_changed(self) -> None:
        # signedIn is only true after fetching the authenticated service snapshot.
        if self._social.signedIn and not self._reviewed:
            self._remember()

    def _remember(self) -> None:
        self._pending = False
        self._reviewed = True
        try:
            self._launcher.save_google_link_reviewed()
        except (NostalgiaError, OSError):
            logging.warning("Không lưu được lựa chọn liên kết Google.")
        self.changed.emit()
