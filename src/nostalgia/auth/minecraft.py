"""Chặng bốn: vé XSTS → vé Minecraft, rồi đọc hồ sơ người chơi.

Hai mã trả về ở đây nói hai chuyện hoàn toàn khác nhau, và lẫn chúng là dẫn người dùng đi
sai đường hàng giờ:

- **403 ở bước đổi vé**: app Azure của bạn chưa được Microsoft duyệt cho gọi Minecraft API.
  Không phải sai mã, không phải sai vé. Phải nộp đơn ở https://aka.ms/mce-reviewappid.
- **404 ở bước đọc hồ sơ**: đăng nhập hoàn toàn hợp lệ, nhưng tài khoản **chưa mua game**.
  Đó không phải lỗi — chỉ là tài khoản này chỉ chơi được bản dùng thử.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from nostalgia.auth.endpoints import MINECRAFT_LOGIN_URL, MINECRAFT_PROFILE_URL
from nostalgia.auth.transport import fetch_with_bearer, post_json, response_fields
from nostalgia.auth.xbox import XboxTicket
from nostalgia.errors import AuthError
from nostalgia.model.json_value import JsonValue, as_string
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

APP_NOT_APPROVED = (
    "Minecraft Services từ chối (403): app Azure của bạn chưa được cấp quyền gọi Minecraft "
    "API. Nộp đơn duyệt ở https://aka.ms/mce-reviewappid; sau khi được duyệt có thể mất tới "
    "24 giờ mới có hiệu lực."
)

UNDASHED_UUID_PATTERN = re.compile(r"\A[0-9a-fA-F]{32}\Z")


@dataclass(frozen=True, slots=True)
class MinecraftSession:
    """Kết quả cuối của một lần đăng nhập.

    `owns_game=False` nghĩa là tài khoản hợp lệ nhưng chưa mua — khi đó không có hồ sơ, nên
    `player_uuid` và `player_name` đều rỗng.
    """

    access_token: str = field(repr=False)
    owns_game: bool = False
    player_uuid: str = ""
    player_name: str = ""

    def __repr__(self) -> str:
        return (
            f"MinecraftSession(access_token='***', owns_game={self.owns_game}, "
            f"player_uuid={self.player_uuid!r}, player_name={self.player_name!r})"
        )


def login_with_xbox(
    http_client: HttpClient,
    ticket: XboxTicket,
    *,
    url: str = MINECRAFT_LOGIN_URL,
    cancel_token: CancelToken | None = None,
) -> str:
    """Đổi vé XSTS lấy vé Minecraft. Định dạng `XBL3.0 x=<hash>;<token>` là bắt buộc."""
    document: JsonValue = {"identityToken": f"XBL3.0 x={ticket.user_hash};{ticket.xbox_token}"}
    response = post_json(http_client, url, document, cancel_token=cancel_token)
    if response.status == 403:
        raise AuthError(APP_NOT_APPROVED)
    if not response.is_ok:
        message = f"Minecraft Services từ chối vé XSTS (HTTP {response.status})"
        raise AuthError(message)
    access_token = as_string(response_fields(response, what="vé Minecraft").get("access_token"))
    if not access_token:
        message = "Minecraft Services trả về phản hồi không có access_token"
        raise AuthError(message)
    return access_token


def fetch_session(
    http_client: HttpClient,
    minecraft_access_token: str,
    *,
    url: str = MINECRAFT_PROFILE_URL,
    cancel_token: CancelToken | None = None,
) -> MinecraftSession:
    """Đọc hồ sơ. Chưa mua game thì trả về phiên dùng thử chứ không ném lỗi."""
    response = fetch_with_bearer(
        http_client, url, minecraft_access_token, cancel_token=cancel_token
    )
    if response.status == 404:
        return MinecraftSession(access_token=minecraft_access_token, owns_game=False)
    if not response.is_ok:
        message = f"không đọc được hồ sơ người chơi (HTTP {response.status})"
        raise AuthError(message)

    fields = response_fields(response, what="hồ sơ người chơi")
    player_uuid = as_string(fields.get("id"))
    player_name = as_string(fields.get("name"))
    if not player_uuid or not player_name:
        message = "hồ sơ người chơi thiếu id hoặc name"
        raise AuthError(message)
    return MinecraftSession(
        access_token=minecraft_access_token,
        owns_game=True,
        player_uuid=to_dashed_uuid(player_uuid),
        player_name=player_name,
    )


def to_dashed_uuid(undashed: str) -> str:
    """Mojang trả UUID **không gạch**; kho tài khoản lưu dạng có gạch.

    Thống nhất một dạng lưu để tài khoản Microsoft và tài khoản offline hiển thị giống nhau,
    và để `PlayerProfile.undashed_uuid` chỉ có đúng một việc phải làm.
    """
    if UNDASHED_UUID_PATTERN.match(undashed) is None:
        return undashed
    return f"{undashed[:8]}-{undashed[8:12]}-{undashed[12:16]}-{undashed[16:20]}-{undashed[20:]}"
