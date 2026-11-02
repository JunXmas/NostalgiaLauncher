"""Thuộc tính Qt và tín hiệu cùng lớp để tránh lỗi meta-object khi kế thừa PySide."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import Property, Signal

from nostalgia.api import (
    EARLY_SUPPORTER_BADGE,
    EARLY_SUPPORTER_PLANS,
    PLUS_BADGE,
    GoogleLogin,
    SocialGateway,
    SocialSnapshot,
)
from nostalgia.ui.worker import WorkerBridge


class SocialState(WorkerBridge):
    changed = Signal()
    sessionChanged = Signal()
    _gateway: SocialGateway | None
    _snapshot: SocialSnapshot | None
    _login: GoogleLogin | None
    _note: str
    _plus_enabled: bool

    def access_token(self) -> str:
        return self._gateway.access_token if self._gateway is not None else ""

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
        plus = self._plus_enabled and (account.plus_lifetime or account.plus_until > time.time())
        early_supporter = account.plus_plan in EARLY_SUPPORTER_PLANS
        return {
            "accountId": account.account_id,
            "name": account.name,
            "avatarUrl": account.avatar_url,
            "friendCode": account.friend_code,
            "plus": plus,
            "badge": (EARLY_SUPPORTER_BADGE if early_supporter else PLUS_BADGE) if plus else "",
            "accent": account.accent,
            "showBadge": account.show_badge,
            "previewAvailable": plus and account.preview_available,
        }

    @Property(list, notify=changed)
    def friends(self) -> list[dict[str, Any]]:
        return (
            [
                {
                    "accountId": friend.account_id,
                    "name": friend.name,
                    "avatarUrl": friend.avatar_url,
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
