"""Dữ liệu minh họa để chụp Qt; không xác thực Google hoặc mở quyền dịch vụ thật."""

from __future__ import annotations

import time
from dataclasses import replace

from nostalgia.social.model import (
    Friend,
    FriendMessage,
    GoogleLogin,
    RoomInvitation,
    ServiceAccount,
    SocialSnapshot,
)


class DemoSocialGateway:
    def __init__(self) -> None:
        self.access_token = "preview-only-session"
        self.snapshot = SocialSnapshot(
            ServiceAccount(
                "preview-jun", "Jun · PREVIEW", "ABCDEF0123456789", int(time.time()) + 86400
            ),
            (
                Friend("preview-misa", "Misa", True),
                Friend("preview-minh", "Minh", True),
                Friend("preview-ha", "Hà", False),
            ),
            (Friend("preview-an", "An", True, True),),
            (
                RoomInvitation(
                    "preview-invite",
                    "preview-misa",
                    "Misa",
                    "Cuối tuần · Forge 1.20.1",
                    int(time.time()) + 300,
                ),
            ),
        )
        self.messages = [
            FriendMessage(
                "preview-1", "preview-misa", "Tối nay chơi Better MC nhé?", int(time.time())
            ),
            FriendMessage(
                "preview-2",
                "preview-jun",
                "Được! Mình chia sẻ pack rồi mời cả nhóm.",
                int(time.time()),
            ),
        ]

    def start_login(self) -> GoogleLogin:
        raise RuntimeError("DEMO không có Google thật")

    def poll_login(self, login: GoogleLogin) -> str:
        del login
        return ""

    def fetch_snapshot(self) -> SocialSnapshot:
        return self.snapshot

    def fetch_messages(self, account_id: str) -> tuple[FriendMessage, ...]:
        del account_id
        return tuple(self.messages)

    def friend_action(self, action: str, account_id: str) -> None:
        if action == "accept":
            requested = next(
                friend for friend in self.snapshot.requests if friend.account_id == account_id
            )
            self.snapshot = replace(
                self.snapshot, friends=(*self.snapshot.friends, requested), requests=()
            )
        elif action in ("block", "remove"):
            self.snapshot = replace(
                self.snapshot,
                friends=tuple(
                    friend for friend in self.snapshot.friends if friend.account_id != account_id
                ),
            )

    def send_message(self, account_id: str, text: str, message_id: str) -> None:
        del account_id
        self.messages.append(FriendMessage(message_id, "preview-jun", text, int(time.time())))

    def send_invite(
        self, account_id: str, room_code: str, host_ticket: str, world_name: str
    ) -> None:
        del account_id, room_code, host_ticket, world_name

    def accept_invite(self, invite_id: str) -> str:
        del invite_id
        self.snapshot = replace(self.snapshot, invitations=())
        return "ABCDEFABCDEFGHJKMN"

    def decline_invite(self, invite_id: str) -> None:
        del invite_id
        self.snapshot = replace(self.snapshot, invitations=())

    def logout(self) -> None:
        self.access_token = ""
