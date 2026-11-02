"""Không để dữ liệu mạng tùy ý trở thành rich text, đường dẫn hay mã phòng."""

from __future__ import annotations

import re

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.payment.catalog import (
    EARLY_SUPPORTER_BADGE,
    LIFETIME_PLANS,
    OLD_BADGES,
    PLANS,
    PLUS_BADGE,
)
from nostalgia.social.model import (
    Friend,
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
    if not isinstance(plus_lifetime, bool) or plus_plan not in PLANS | {""}:
        raise SocialError("Quyền lợi dịch vụ không hợp lệ.")
    if plus_lifetime and plus_plan not in LIFETIME_PLANS:
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
        # Launcher không hiện trạng thái online: máy chủ cũ còn gửi "online" thì bỏ qua.
        fields = as_mapping(document)
        return Friend(
            identifier(text(fields.get("account_id"), 96)),
            text(fields.get("name")),
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


def accent(document: JsonValue) -> str:
    value = as_string(document) or ""
    if value not in ("", "amethyst", "emerald", "amber"):
        raise SocialError("Màu hồ sơ không hợp lệ.")
    return value


def badge(document: JsonValue) -> str:
    value = as_string(document) or ""
    if value in OLD_BADGES:
        return EARLY_SUPPORTER_BADGE
    if value not in ("", PLUS_BADGE, EARLY_SUPPORTER_BADGE):
        raise SocialError("Huy hiệu không hợp lệ.")
    return value


def decor(document: JsonValue) -> str:
    from nostalgia.social.cosmetic import is_cosmetic_id

    value = as_string(document) or "none"
    if not is_cosmetic_id(value):
        raise SocialError("Khung hồ sơ không hợp lệ.")
    return value
