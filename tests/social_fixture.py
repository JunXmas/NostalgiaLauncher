"""Dịch vụ bạn bè mẫu cho test Qt, không có đường cấp Plus thật."""

from __future__ import annotations

import time
from dataclasses import replace

from nostalgia.errors import SessionRevoked
from nostalgia.social.model import (
    Friend,
    FriendMessage,
    GoogleLogin,
    RoomInvitation,
    ServiceAccount,
    SocialSnapshot,
)


class SocialFixture:
    def __init__(self) -> None:
        self.access_token = ""
        self.revoked = False
        self.accepted: list[str] = []
        self.sent: list[str] = []
        self.invited: list[str] = []
        self.snapshot = SocialSnapshot(
            ServiceAccount("jun", "Jun PREVIEW", "ABCDEF0123456789", 0),
            (Friend("misa", "Misa", True),),
            (Friend("minh", "Minh", True, True),),
            (RoomInvitation("invite", "misa", "Misa", "World", int(time.time()) + 300),),
        )
        self.messages = [FriendMessage("hello", "misa", "Xin chào", int(time.time()))]

    def start_login(self) -> GoogleLogin:
        return GoogleLogin(
            "login",
            "https://accounts.google.com/o/oauth2/v2/auth?fixture=1",
            int(time.time()) + 300,
            "v" * 64,
        )

    def poll_login(self, login: GoogleLogin) -> str:
        del login
        return "a" * 64

    def fetch_snapshot(self) -> SocialSnapshot:
        if self.revoked:
            raise SessionRevoked("Phiên đã đăng nhập trên máy khác.")
        return self.snapshot

    def fetch_messages(self, account_id: str) -> tuple[FriendMessage, ...]:
        assert account_id == "misa"
        return tuple(self.messages)

    def friend_action(self, action: str, account_id: str) -> None:
        if action == "accept":
            self.accepted.append(account_id)
            self.snapshot = replace(self.snapshot, requests=())

    def send_message(self, account_id: str, text: str, message_id: str) -> None:
        assert account_id == "misa"
        self.sent.append(text)
        self.messages.append(FriendMessage(message_id, "jun", text, int(time.time())))

    def send_invite(
        self, account_id: str, room_code: str, host_ticket: str, world_name: str
    ) -> None:
        assert room_code == "ABCDEFABCDEFGHJKMN" and host_ticket == "opaque-ticket"
        assert world_name == "World"
        self.invited.append(account_id)

    def accept_invite(self, invite_id: str) -> str:
        assert invite_id == "invite"
        self.snapshot = replace(self.snapshot, invitations=())
        return "ABCDEFABCDEFGHJKMN"

    def decline_invite(self, invite_id: str) -> None:
        del invite_id
        self.snapshot = replace(self.snapshot, invitations=())

    def update_profile(self, accent: str, show_badge: bool) -> None:
        self.snapshot = replace(
            self.snapshot,
            account=replace(self.snapshot.account, accent=accent, show_badge=show_badge),
        )

    def fetch_preview_url(self, target: str) -> str:
        del target
        raise RuntimeError("Demo không phân phối bộ cài riêng.")

    def logout(self) -> None:
        self.revoked = True
