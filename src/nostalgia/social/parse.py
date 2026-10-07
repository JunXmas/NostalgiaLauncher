"""Không để dữ liệu mạng tùy ý trở thành rich text, đường dẫn hay mã phòng."""

from __future__ import annotations

import re

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.social.model import (
    Friend,
    FriendMessage,
    RoomInvitation,
    ServiceAccount,
    SocialSnapshot,
)
from nostalgia.social.profile_image import image_url


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", value):
        raise SocialError("Mã tài khoản không hợp lệ.")
    return value


def text(document: JsonValue, maximum: int = 80) -> str:
    value = as_string(document) or ""
    if not value.strip() or len(value) > maximum or re.search(r"[\x00-\x1f\x7f<>]", value):
        raise SocialError("Dữ liệu dịch vụ không hợp lệ.")
    return value


def rows(document: JsonValue, limit: int = 200) -> list[JsonValue]:
    if not isinstance(document, list) or len(document) > limit:
        raise SocialError("Danh sách dịch vụ không hợp lệ.")
    return document


def timestamp(document: JsonValue) -> int:
    value = as_integer(document)
    if value is None or not 0 <= value <= 4_102_444_800:
        raise SocialError("Thời hạn dịch vụ không hợp lệ.")
    return value


def parse_snapshot(document: JsonValue) -> SocialSnapshot:
    fields = as_mapping(document)
    account_fields = as_mapping(fields.get("account"))
    friend_code = text(account_fields.get("friend_code"))
    if not re.fullmatch(r"[A-F0-9]{16}", friend_code):
        raise SocialError("Mã kết bạn không hợp lệ.")
    plus_lifetime = account_fields.get("plus_lifetime", False)
    plus_plan = as_string(account_fields.get("plus_plan")) or ""
    if not isinstance(plus_lifetime, bool) or plus_plan not in (
        "",
        "plus-month-v1",
        "plus-half-year-v1",
        "plus-year-v2",
        "plus-lifetime-v1",
    ):
        raise SocialError("Quyền lợi dịch vụ không hợp lệ.")
    if plus_lifetime and plus_plan != "plus-lifetime-v1":
        raise SocialError("Gói mua đứt không hợp lệ.")
    account = ServiceAccount(
        identifier(text(account_fields.get("account_id"), 96)),
        text(account_fields.get("name")),
        friend_code,
        timestamp(account_fields.get("plus_until")),
        plus_lifetime,
        plus_plan,
        accent(account_fields.get("accent")),
        account_fields.get("show_badge", True) is True,
        image_url(account_fields.get("avatar_url")),
    )

    def parse_friend(document: JsonValue) -> Friend:
        fields = as_mapping(document)
        if not isinstance(fields.get("online"), bool):
            raise SocialError("Trạng thái bạn bè không hợp lệ.")
        return Friend(
            identifier(text(fields.get("account_id"), 96)),
            text(fields.get("name")),
            fields.get("online") is True,
            fields.get("incoming") is True,
            badge(fields.get("badge")),
            accent(fields.get("accent")),
            image_url(fields.get("avatar_url")),
            decor(fields.get("decor")),
        )

    invitations = []
    for document in rows(fields.get("invitations"), 20):
        invite = as_mapping(document)
        invitations.append(
            RoomInvitation(
                identifier(text(invite.get("invite_id"), 96)),
                identifier(text(invite.get("sender"), 96)),
                text(invite.get("name")),
                text(invite.get("world_name")),
                timestamp(invite.get("expires_at")),
            )
        )
    return SocialSnapshot(
        account,
        tuple(map(parse_friend, rows(fields.get("friends")))),
        tuple(map(parse_friend, rows(fields.get("requests")))),
        tuple(invitations),
    )


def parse_messages(document: JsonValue) -> tuple[FriendMessage, ...]:
    messages = []
    for message_document in rows(document, 100):
        fields = as_mapping(message_document)
        messages.append(
            FriendMessage(
                identifier(text(fields.get("message_id"), 96)),
                identifier(text(fields.get("sender"), 96)),
                text(fields.get("body"), 1000),
                timestamp(fields.get("created_at")),
            )
        )
    return tuple(messages)


def accent(document: JsonValue) -> str:
    value = as_string(document) or ""
    if value not in ("", "amethyst", "emerald", "amber"):
        raise SocialError("Màu hồ sơ không hợp lệ.")
    return value


def badge(document: JsonValue) -> str:
    value = as_string(document) or ""
    if value not in ("", "Đồng hành", "Tiên phong", "Sáng lập"):
        raise SocialError("Huy hiệu không hợp lệ.")
    return value


def decor(document: JsonValue) -> str:
    value = as_string(document) or "none"
    if value not in ("none", "amethyst", "emerald", "amber"):
        raise SocialError("Khung hồ sơ không hợp lệ.")
    return value
