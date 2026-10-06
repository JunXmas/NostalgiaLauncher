"""Danh sách bạn, chat và lời mời; mã phòng chỉ đi giữa gateway và dịch vụ relay."""

from __future__ import annotations

import uuid

from PySide6.QtCore import Slot
from PySide6.QtGui import QGuiApplication

from nostalgia.ui.social_session import SocialSession


class SocialBridge(SocialSession):
    @Slot(bool)
    def setWatching(self, watching: bool) -> None:
        self._timer.setInterval(3000 if watching else 15000)

    @Slot(str)
    def selectFriend(self, account_id: str) -> None:
        if not account_id:
            self._peer_id, self._messages = "", []
            self.changed.emit()
            return
        if self._snapshot and any(
            friend.account_id == account_id for friend in self._snapshot.friends
        ):
            self._peer_id, self._messages = account_id, []
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
        if self.signedIn and gateway and not self.busy:
            self._request("changed", lambda: gateway.friend_action(action, account_id))

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        gateway, account_id = self._gateway, self._peer_id
        if (
            self.signedIn
            and gateway
            and account_id
            and text.strip()
            and len(text) <= 1000
            and not self.busy
        ):
            message_id = uuid.uuid4().hex

            def send() -> str:
                gateway.send_message(account_id, text.strip(), message_id)
                return text.strip()

            self._request("message", send)

    @Slot(str)
    def inviteFriend(self, account_id: str) -> None:
        gateway, status = self._gateway, self._multiplayer.room_snapshot()
        if self.signedIn and gateway and not self.busy and status.role == "hosting":
            self._request(
                "changed",
                lambda: gateway.send_invite(
                    account_id, status.room_code, status.host_ticket, status.world_name
                ),
            )

    @Slot(str)
    def acceptInvite(self, invite_id: str) -> None:
        gateway = self._gateway
        if self.signedIn and gateway and not self.busy and not self._multiplayer.active:
            self._request("join", lambda: gateway.accept_invite(invite_id))

    @Slot(str)
    def declineInvite(self, invite_id: str) -> None:
        gateway = self._gateway
        if self.signedIn and gateway and not self.busy:
            self._request("changed", lambda: gateway.decline_invite(invite_id))

    @Slot()
    def copyFriendCode(self) -> None:
        if self._snapshot:
            QGuiApplication.clipboard().setText(self._snapshot.account.friend_code)
