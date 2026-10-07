"""Thuộc tính Qt và tín hiệu cùng lớp để tránh lỗi meta-object khi kế thừa PySide."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import Property, Signal

from nostalgia.api import GoogleLogin, SocialGateway, SocialSnapshot
from nostalgia.ui.worker import WorkerBridge


class SocialState(WorkerBridge):
    changed = Signal()
    sessionChanged = Signal()
    messageSent = Signal(str)
    _gateway: SocialGateway | None
    _snapshot: SocialSnapshot | None
    _messages: list[dict[str, Any]]
    _peer_id: str
    _login: GoogleLogin | None
    _note: str
    _plus_enabled: bool

    @Property(bool, constant=True)
    def configured(self) -> bool:
        return self._gateway is not None

    @Property(bool, notify=changed)
    def signedIn(self) -> bool:
        return self._snapshot is not None

    @Property(bool, notify=changed)
    def signingIn(self) -> bool:
        return self._login is not None

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Property(dict, notify=changed)
    def account(self) -> dict[str, Any]:
        if self._snapshot is None:
            return {}
        account = self._snapshot.account
        return {
            "accountId": account.account_id,
            "name": account.name,
            "avatarUrl": account.avatar_url,
            "friendCode": account.friend_code,
            "plus": self._plus_enabled
            and (account.plus_lifetime or account.plus_until > time.time()),
            "plusLifetime": self._plus_enabled and account.plus_lifetime,
            "badge": {
                "plus-half-year-v1": "Đồng hành",
                "plus-year-v2": "Tiên phong",
                "plus-lifetime-v1": "Sáng lập",
            }.get(account.plus_plan, "")
            if self._plus_enabled and (account.plus_lifetime or account.plus_until > time.time())
            else "",
            "plusUntil": account.plus_until,
            "planName": {
                "plus-month-v1": "Plus",
                "plus-half-year-v1": "Pro",
                "plus-year-v2": "Max",
                "plus-lifetime-v1": "Ultimate",
            }.get(account.plus_plan, "Plus"),
            "accent": account.accent,
            "showBadge": account.show_badge,
            "profilePlus": self._plus_enabled
            and account.plus_plan in ("plus-half-year-v1", "plus-year-v2", "plus-lifetime-v1")
            and (account.plus_lifetime or account.plus_until > time.time()),
            "cosmeticPlus": self._plus_enabled
            and account.plus_plan
            in ("plus-month-v1", "plus-half-year-v1", "plus-year-v2", "plus-lifetime-v1")
            and (account.plus_lifetime or account.plus_until > time.time()),
            "earlyPreview": self._plus_enabled
            and account.plus_plan in ("plus-year-v2", "plus-lifetime-v1")
            and (account.plus_lifetime or account.plus_until > time.time()),
        }

    @Property(list, notify=changed)
    def friends(self) -> list[dict[str, Any]]:
        return (
            [
                {
                    "accountId": friend.account_id,
                    "name": friend.name,
                    "avatarUrl": friend.avatar_url,
                    "online": friend.online,
                    "badge": friend.badge,
                    "accent": friend.accent,
                    "decor": friend.decor,
                }
                for friend in self._snapshot.friends
            ]
            if self._snapshot
            else []
        )

    @Property(list, notify=changed)
    def requests(self) -> list[dict[str, Any]]:
        return (
            [
                {
                    "accountId": friend.account_id,
                    "name": friend.name,
                    "avatarUrl": friend.avatar_url,
                    "incoming": friend.incoming,
                    "online": friend.online,
                }
                for friend in self._snapshot.requests
            ]
            if self._snapshot
            else []
        )

    @Property(list, notify=changed)
    def invitations(self) -> list[dict[str, Any]]:
        return (
            [
                {
                    "inviteId": invitation.invite_id,
                    "name": invitation.name,
                    "world": invitation.world_name,
                }
                for invitation in self._snapshot.invitations
                if invitation.expires_at > time.time()
            ]
            if self._snapshot
            else []
        )

    @Property(list, notify=changed)
    def messages(self) -> list[dict[str, Any]]:
        return self._messages

    @Property(str, notify=changed)
    def peerId(self) -> str:
        return self._peer_id

    @Property(bool, notify=changed)
    def peerOnline(self) -> bool:
        return (
            any(
                friend.account_id == self._peer_id and friend.online
                for friend in self._snapshot.friends
            )
            if self._snapshot
            else False
        )

    @Property(str, notify=changed)
    def peerName(self) -> str:
        if self._snapshot:
            return next(
                (
                    friend.name
                    for friend in self._snapshot.friends
                    if friend.account_id == self._peer_id
                ),
                "",
            )
        return ""
