"""Dữ liệu dịch vụ được kiểm tra trước khi tới Qt."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from nostalgia.social.profile_model import ProfileDraft, SocialProfile


@dataclass(frozen=True, slots=True)
class GoogleLogin:
    login_id: str
    authorization_url: str
    expires_at: int
    verifier: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ServiceAccount:
    account_id: str
    name: str
    friend_code: str
    plus_until: int
    plus_lifetime: bool = False
    plus_plan: str = ""
    accent: str = ""
    show_badge: bool = True
    avatar_url: str = ""


@dataclass(frozen=True, slots=True)
class Friend:
    account_id: str
    name: str
    online: bool
    incoming: bool = False
    badge: str = ""
    accent: str = ""
    avatar_url: str = ""
    decor: str = "none"


@dataclass(frozen=True, slots=True)
class RoomInvitation:
    invite_id: str
    sender: str
    name: str
    world_name: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class FriendMessage:
    message_id: str
    sender: str
    body: str
    created_at: int


@dataclass(frozen=True, slots=True)
class SocialSnapshot:
    account: ServiceAccount
    friends: tuple[Friend, ...]
    requests: tuple[Friend, ...]
    invitations: tuple[RoomInvitation, ...]


class SocialGateway(Protocol):
    access_token: str

    def start_login(self) -> GoogleLogin: ...
    def poll_login(self, login: GoogleLogin) -> str: ...
    def fetch_snapshot(self) -> SocialSnapshot: ...
    def fetch_messages(self, account_id: str) -> tuple[FriendMessage, ...]: ...
    def friend_action(self, action: str, account_id: str) -> None: ...
    def send_message(self, account_id: str, text: str, message_id: str) -> None: ...
    def send_invite(
        self, account_id: str, room_code: str, host_ticket: str, world_name: str
    ) -> None: ...
    def accept_invite(self, invite_id: str) -> str: ...
    def decline_invite(self, invite_id: str) -> None: ...
    def update_profile(self, accent: str, show_badge: bool) -> None: ...

    def fetch_profile(self, account_id: str) -> SocialProfile: ...
    def save_profile(self, draft: ProfileDraft) -> SocialProfile: ...

    def fetch_preview_url(self, target: str) -> str: ...

    def logout(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SocialUpdate:
    snapshot: SocialSnapshot
    messages: tuple[FriendMessage, ...]
    peer_id: str


class ServiceSessionStore(Protocol):
    """Kho bí mật hệ điều hành; thiếu kho an toàn thì chỉ giữ phiên trong RAM."""

    def load_access_token(self) -> str: ...
    def save_access_token(self, access_token: str) -> bool: ...
    def remove_access_token(self) -> None: ...
