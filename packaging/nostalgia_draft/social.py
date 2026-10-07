"""Persistent test identity and simulated friends; never contacts the account service."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import cast

from nostalgia.errors import NostalgiaError, SocialError
from nostalgia.model.json_value import JsonValue
from nostalgia.social.model import (
    Friend,
    FriendMessage,
    GoogleLogin,
    ServiceAccount,
    SocialSnapshot,
)
from nostalgia.social.profile_model import ProfileDraft, SocialProfile
from nostalgia.social.profile_parse import parse_profile
from nostalgia.storage.files import atomic_write_json, read_json


class ReviewSocial:
    def __init__(self, directory: Path) -> None:
        self.access_token = "draft-local-session-not-a-service-credential"
        self._profile_path = directory / "profile.json"
        self.profile_draft = ProfileDraft()
        if self._profile_path.is_file():
            try:
                self.profile_draft = parse_profile(read_json(self._profile_path)).details
            except (OSError, ValueError, NostalgiaError):
                self.profile_draft = ProfileDraft()
        self.snapshot = SocialSnapshot(
            ServiceAccount(
                "draft-reviewer",
                "Bạn · TEST",
                "DRAFT00000000000",
                4_000_000_000,
                plus_lifetime=True,
                plus_plan="plus-lifetime-v1",
                accent="amethyst",
            ),
            (
                Friend("draft-misa", "Misa · TEST", True, decor="amethyst"),
                Friend("draft-huy", "Huy · TEST", True, decor="emerald"),
                Friend("draft-minh", "Minh · TEST", False, decor="amber"),
            ),
            (Friend("draft-linh", "Linh · TEST", True, True),),
            (),
        )
        self.messages = [
            FriendMessage(
                "draft-hello",
                "draft-misa",
                "Đây là chat mô phỏng để thử giao diện.",
                int(time.time()),
            )
        ]

    def select_plan(self, plan_id: str) -> None:
        if plan_id not in (
            "plus-month-v1",
            "plus-half-year-v1",
            "plus-year-v2",
            "plus-lifetime-v1",
        ):
            raise SocialError("Gói thử không hợp lệ.")
        self.snapshot = replace(
            self.snapshot,
            account=replace(
                self.snapshot.account,
                plus_plan=plan_id,
                plus_lifetime=plan_id == "plus-lifetime-v1",
            ),
        )

    def start_login(self) -> GoogleLogin:
        raise SocialError(
            "Phiên TEST không đăng nhập Google. Mở Công cụ Draft để khôi phục phiên thử."
        )

    def poll_login(self, login: GoogleLogin) -> str:
        del login
        return ""

    def fetch_snapshot(self) -> SocialSnapshot:
        if not self.access_token:
            raise SocialError("Phiên thử đã đóng. Khôi phục từ Công cụ Draft.")
        return self.snapshot

    def fetch_messages(self, account_id: str) -> tuple[FriendMessage, ...]:
        return tuple(m for m in self.messages if m.sender in (account_id, "draft-reviewer"))

    def friend_action(self, action: str, account_id: str) -> None:
        if action == "accept":
            requested = next(
                (f for f in self.snapshot.requests if f.account_id == account_id), None
            )
            if requested:
                self.snapshot = replace(
                    self.snapshot, friends=(*self.snapshot.friends, requested), requests=()
                )
        elif action in ("block", "remove"):
            self.snapshot = replace(
                self.snapshot,
                friends=tuple(f for f in self.snapshot.friends if f.account_id != account_id),
            )
        elif action == "request":
            raise SocialError(
                "Bạn bè trong chế độ TEST là dữ liệu mô phỏng; cần backend để kết bạn thật."
            )

    def send_message(self, account_id: str, text: str, message_id: str) -> None:
        self.messages.extend(
            (
                FriendMessage(message_id, "draft-reviewer", text, int(time.time())),
                FriendMessage(
                    message_id + "-echo", account_id, "TEST · Đã nhận: " + text, int(time.time())
                ),
            )
        )
        self.messages = self.messages[-100:]

    def send_invite(
        self, account_id: str, room_code: str, host_ticket: str, world_name: str
    ) -> None:
        del account_id, room_code, host_ticket, world_name
        raise SocialError("Lời mời TEST không gửi qua mạng. Thử đồng bộ local trong Công cụ Draft.")

    def accept_invite(self, invite_id: str) -> str:
        del invite_id
        raise SocialError("Không có lời mời online trong chế độ TEST.")

    def decline_invite(self, invite_id: str) -> None:
        del invite_id

    def update_profile(self, accent: str, show_badge: bool) -> None:
        if self.snapshot.account.plus_plan == "plus-month-v1":
            raise SocialError("Huy hiệu/màu hồ sơ cần Pro trở lên.")
        self.snapshot = replace(
            self.snapshot,
            account=replace(self.snapshot.account, accent=accent, show_badge=show_badge),
        )

    def fetch_profile(self, account_id: str) -> SocialProfile:
        if account_id == "draft-reviewer":
            return SocialProfile(
                account_id,
                self.snapshot.account.name,
                True,
                "data:image/png;base64," + self.profile_draft.avatar_png
                if self.profile_draft.avatar_mode == "skin" and self.profile_draft.avatar_png
                else "",
                self.profile_draft,
                "Sáng lập" if self.snapshot.account.plus_plan == "plus-lifetime-v1" else "",
            )
        friend = next((f for f in self.snapshot.friends if f.account_id == account_id), None)
        if not friend:
            raise SocialError("Bạn thử không còn trong danh sách.")
        return SocialProfile(
            account_id,
            friend.name,
            friend.online,
            "",
            ProfileDraft(bio="Hồ sơ mô phỏng trong bản Draft.", decor=friend.decor),
        )

    def save_profile(self, draft: ProfileDraft) -> SocialProfile:
        document = cast(dict[str, JsonValue], json.loads(json.dumps(asdict(draft))))
        document.update(account_id="draft-reviewer", name=self.snapshot.account.name)
        self.profile_draft = parse_profile(document).details
        atomic_write_json(self._profile_path, document)
        return self.fetch_profile("draft-reviewer")

    def fetch_preview_url(self, target: str) -> str:
        del target
        if self.snapshot.account.plus_plan not in ("plus-year-v2", "plus-lifetime-v1"):
            raise SocialError("Preview sớm cần Max hoặc Ultimate.")
        return "https://github.com/JunXmas/NostalgiaLauncher/releases"

    def logout(self) -> None:
        self.access_token = ""
