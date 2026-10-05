"""Tài khoản offline: tên người chơi quyết định UUID, không có gì ngẫu nhiên.

**Đây là chỗ dễ sai nhất và hậu quả nặng nhất.** Minecraft gắn thế giới, đồ đạc và tiến độ
theo UUID. Sinh UUID ngẫu nhiên (`uuid4`) thì mỗi lần chơi là một người khác: rương trống,
toạ độ về điểm sinh, quyền trên máy chủ mất sạch. Máy chủ Minecraft tự tính UUID offline
theo đúng công thức dưới đây, nên launcher phải khớp từng bit.

Công thức là `UUID.nameUUIDFromBytes` của Java áp lên `"OfflinePlayer:<tên>"`: băm MD5 rồi
đặt lại 4 bit phiên bản và 2 bit biến thể. Chú ý `uuid.uuid3` của Python **không** dùng được
— nó chèn thêm 16 byte không gian tên vào trước dữ liệu.
"""

from __future__ import annotations

import hashlib
import re
import uuid

from nostalgia.account.model import OFFLINE, Account
from nostalgia.errors import AccountError

OFFLINE_UUID_PREFIX = "OfflinePlayer:"

# Luật đặt tên của Mojang cho tài khoản đời cũ. Kiểm ở đây để lỗi hiện ra lúc thêm tài khoản,
# chứ không phải lúc game đã chạy rồi tự thoát không nói gì.
PLAYER_NAME_PATTERN = re.compile(r"\A[A-Za-z0-9_]{3,16}\Z")


def offline_uuid(player_name: str) -> str:
    """UUID offline của một tên, dạng có gạch. Cùng tên luôn ra cùng UUID."""
    digest = bytearray(hashlib.md5((OFFLINE_UUID_PREFIX + player_name).encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # phiên bản 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # biến thể RFC 4122
    return str(uuid.UUID(bytes=bytes(digest)))


def build_offline_account(player_name: str) -> Account:
    """Dựng tài khoản offline từ tên. Tên sai luật thì báo ngay."""
    if PLAYER_NAME_PATTERN.match(player_name) is None:
        message = (
            f"tên người chơi {player_name!r} không hợp lệ: cần 3-16 ký tự, "
            "chỉ gồm chữ cái, chữ số và dấu gạch dưới"
        )
        raise AccountError(message)
    return Account(
        player_name=player_name,
        player_uuid=offline_uuid(player_name),
        account_kind=OFFLINE,
    )
