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
from nostalgia.social.profile_model import ProfileDraft, SocialProfile


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

    def update_profile(self, accent: str, show_badge: bool) -> None:
        self.snapshot = replace(
            self.snapshot,
            account=replace(self.snapshot.account, accent=accent, show_badge=show_badge),
        )

    def fetch_profile(self, account_id: str) -> SocialProfile:
        account = self.snapshot.account
        if account_id == account.account_id:
            return SocialProfile(
                account_id,
                account.name,
                True,
                account.avatar_url,
                getattr(self, "profile_draft", ProfileDraft()),
            )
        friend = next(f for f in self.snapshot.friends if f.account_id == account_id)
        return SocialProfile(
            account_id,
            friend.name,
            friend.online,
            friend.avatar_url,
            ProfileDraft(),
            friend.badge,
            friend.accent,
        )

    def save_profile(self, draft: ProfileDraft) -> SocialProfile:
        self.profile_draft = draft
        return self.fetch_profile(self.snapshot.account.account_id)

    def fetch_preview_url(self, target: str) -> str:
        del target
        raise RuntimeError("Demo không phân phối bộ cài riêng.")

    def logout(self) -> None:
        self.access_token = ""
