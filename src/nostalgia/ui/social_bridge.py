"""Danh sách bạn, chat và lời mời; mã phòng chỉ đi giữa gateway và dịch vụ relay."""

from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from nostalgia.api import ServiceSessionStore, SocialGateway
from nostalgia.ui.chat_sender import ChatSender
from nostalgia.ui.friend_sender import FriendSender
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_invitations import SocialInvitations


class SocialBridge(SocialInvitations):
    chatBusyChanged = Signal()
    friendBusyChanged = Signal()

    def __init__(
        self,
        gateway: SocialGateway | None,
        multiplayer: MultiplayerBridge,
        sync_bridge: RoomSyncBridge,
        parent: QObject | None = None,
        session_store: ServiceSessionStore | None = None,
        plus_enabled: bool = True,
    ) -> None:
        super().__init__(gateway, multiplayer, sync_bridge, parent, session_store, plus_enabled)
        self._chat = ChatSender(self)
        self._chat.busyChanged.connect(self.chatBusyChanged)
        self._chat.completed.connect(self._apply_delivery)
        self._friend_sender = FriendSender(self)
        self._friend_sender.busyChanged.connect(self.friendBusyChanged)
        self._friend_sender.completed.connect(self._apply_friend_action)
        self.changed.connect(self._configure_poll_interval)

    @Property(bool, notify=friendBusyChanged)
    def friendBusy(self) -> bool:
        return bool(self._friend_sender.busy)

    @Slot(str, bool)
    def _apply_friend_action(self, error: str, revoked: bool) -> None:
        if revoked:
            if self._session_store:
                self._session_store.remove_access_token()
            self._reset_session(error)
        elif error:
            self._note = error
        else:
            self._note = "Đã gửi."
            self.refresh()
        self.changed.emit()

    @Property(bool, notify=chatBusyChanged)
    def chatBusy(self) -> bool:
        return bool(self._chat.busy)

    @Slot(str, str, str, bool)
    def _apply_delivery(self, peer_id: str, text: str, error: str, revoked: bool) -> None:
        if revoked:
            if self._session_store:
                self._session_store.remove_access_token()
            self._reset_session(error)
        elif error:
            self._note = error
        else:
            if peer_id == self._peer_id:
                self.messageSent.emit(text)
            self._note = "Đã gửi."
            self.refresh()
        self.changed.emit()

    @Slot()
    def shutdown(self) -> None:
        self._chat.cancel()
        self._friend_sender.cancel()
        super().shutdown()

    def _reset_session(self, note: str) -> None:
        self._chat.cancel()
        self._friend_sender.cancel()
        super()._reset_session(note)

    @Slot(bool)
    def setWatching(self, watching: bool) -> None:
        changed = watching != self._watching
        self._watching = watching
        self._configure_poll_interval()
        if watching and changed:
            self.refresh()

    def _configure_poll_interval(self) -> None:
        interval = 5000 if self._watching and self._peer_id else 15000
        if self._timer.interval() != interval:
            self._timer.setInterval(interval)

    @Slot(str)
    def selectFriend(self, account_id: str) -> None:
        if not account_id:
            self._peer_id, self._messages = "", []
            self._configure_poll_interval()
            self.changed.emit()
            return
        if self._snapshot and any(
            friend.account_id == account_id for friend in self._snapshot.friends
        ):
            self._peer_id, self._messages = account_id, []
            self._configure_poll_interval()
            self.changed.emit()
            self.refresh()

    @Slot(str)
    def requestFriend(self, friend_code: str) -> None:
        self._friend_action("request", friend_code)

    @Slot(str)
    def acceptFriend(self, account_id: str) -> None:
        self._friend_action("accept", account_id)

    @Slot(str)
    def removeFriend(self, account_id: str) -> None:
        self._friend_action("remove", account_id)

    @Slot(str)
    def blockFriend(self, account_id: str) -> None:
        self._friend_action("block", account_id)

    def _friend_action(self, action: str, account_id: str) -> None:
        gateway = self._gateway
        if self.signedIn and gateway and account_id and not self.friendBusy:
            self._friend_sender.submit(gateway, action, account_id)

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        gateway, account_id = self._gateway, self._peer_id
        if (
            self.signedIn
            and gateway
            and account_id
            and text.strip()
            and len(text) <= 1000
            and not self.chatBusy
            and self._snapshot
            and any(friend.account_id == account_id for friend in self._snapshot.friends)
        ):
            self._chat.submit(gateway, account_id, text.strip())

    @Slot(str, bool)
    def setProfile(self, accent: str, show_badge: bool) -> None:
        gateway = self._gateway
        if self._plus_enabled and gateway and self.signedIn and not self.busy:
            self._request("changed", lambda: gateway.update_profile(accent, show_badge))

    @Slot()
    def downloadEarlyPreview(self) -> None:
        gateway = self._gateway
        if self._plus_enabled and gateway and self.signedIn and not self.busy:
            target = (
                "windows-x64"
                if sys.platform == "win32"
                else ("macos-arm64" if platform.machine() == "arm64" else "macos-x64")
                if sys.platform == "darwin"
                else "linux-x64"
            )
            self._request("preview", lambda: gateway.fetch_preview_url(target))

    @Slot()
    def copyFriendCode(self) -> None:
        if self._snapshot:
            QGuiApplication.clipboard().setText(self._snapshot.account.friend_code)
