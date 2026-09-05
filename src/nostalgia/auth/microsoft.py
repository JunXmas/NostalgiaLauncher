"""Ghép bốn chặng thành một lần đăng nhập.

Ở đây chỉ còn **trình tự**; mọi luật của từng chặng nằm ở module của chặng đó. Chia như vậy
để khi Microsoft đổi một chặng — họ đã đổi vài lần — thì chỉ một file phải sửa.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from nostalgia.auth.device_code import (
    DeviceCode,
    MicrosoftTokens,
    poll_for_tokens,
    refresh_tokens,
    request_device_code,
)
from nostalgia.auth.endpoints import (
    CLIENT_ID_ENV,
    DEFAULT_AUTH_ENDPOINTS,
    DEFAULT_CLIENT_ID,
    AuthEndpoints,
)
from nostalgia.auth.minecraft import MinecraftSession, fetch_session, login_with_xbox
from nostalgia.auth.xbox import XboxTicket, authenticate_xbox_live, authorize_xsts
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

type DeviceCodeFn = Callable[[DeviceCode], None]


def ignore_device_code(_device_code: DeviceCode) -> None:
    """Mặc định: không hiển thị gì. Người gọi nào muốn thấy mã thì truyền hàm của mình vào."""


@dataclass(frozen=True, slots=True)
class MicrosoftLogin:
    """Kết quả trọn vẹn: phiên Minecraft để chơi, và vé Microsoft để lần sau khỏi đăng nhập."""

    minecraft_session: MinecraftSession
    tokens: MicrosoftTokens


def resolve_client_id(environ: Mapping[str, str]) -> str:
    """Mã ứng dụng dùng để đăng nhập.

    Mặc định là app đã duyệt của chính launcher này, nên người chơi **không phải làm gì cả**.
    Biến môi trường chỉ để ai fork mà muốn dùng app Azure riêng của họ.
    """
    return environ.get(CLIENT_ID_ENV, "").strip() or DEFAULT_CLIENT_ID


def exchange_for_session(
    http_client: HttpClient,
    microsoft_access_token: str,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> MinecraftSession:
    """Ba chặng cuối: Xbox Live → XSTS → Minecraft. Dùng lại được sau khi làm mới vé."""
    xbox_ticket = authenticate_xbox_live(
        http_client, microsoft_access_token, url=endpoints.xbox_live_url, cancel_token=cancel_token
    )
    xsts_ticket = authorize_xsts(
        http_client, xbox_ticket.xbox_token, url=endpoints.xsts_url, cancel_token=cancel_token
    )
    # `user_hash` đến từ chặng Xbox Live, không phải từ XSTS — XSTS chỉ trả lại vé.
    minecraft_token = login_with_xbox(
        http_client,
        XboxTicket(xbox_token=xsts_ticket.xbox_token, user_hash=xbox_ticket.user_hash),
        url=endpoints.minecraft_login_url,
        cancel_token=cancel_token,
    )
    return fetch_session(
        http_client, minecraft_token, url=endpoints.minecraft_profile_url, cancel_token=cancel_token
    )


def sign_in(
    http_client: HttpClient,
    client_id: str,
    on_device_code: DeviceCodeFn = ignore_device_code,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    sleep_seconds: float | None = None,
    cancel_token: CancelToken | None = None,
) -> MicrosoftLogin:
    """Đăng nhập từ đầu. `on_device_code` nhận mã để hiển thị cho người dùng.

    Lõi không in ra màn hình, nên mã phải đi ra ngoài qua callback — đúng cách `on_progress`
    làm với tiến độ tải.
    """
    device_code = request_device_code(
        http_client, client_id, url=endpoints.device_code_url, cancel_token=cancel_token
    )
    on_device_code(device_code)
    tokens = poll_for_tokens(
        http_client,
        client_id,
        device_code,
        url=endpoints.token_url,
        sleep_seconds=sleep_seconds,
        cancel_token=cancel_token,
    )
    minecraft_session = exchange_for_session(
        http_client, tokens.access_token, endpoints=endpoints, cancel_token=cancel_token
    )
    return MicrosoftLogin(minecraft_session=minecraft_session, tokens=tokens)


def sign_in_again(
    http_client: HttpClient,
    client_id: str,
    refresh_token: str,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> MicrosoftLogin:
    """Làm mới vé mà không cần người dùng nhập lại mã."""
    tokens = refresh_tokens(
        http_client, client_id, refresh_token, url=endpoints.token_url, cancel_token=cancel_token
    )
    minecraft_session = exchange_for_session(
        http_client, tokens.access_token, endpoints=endpoints, cancel_token=cancel_token
    )
    return MicrosoftLogin(minecraft_session=minecraft_session, tokens=tokens)


__all__ = [
    "DeviceCode",
    "DeviceCodeFn",
    "MicrosoftLogin",
    "exchange_for_session",
    "resolve_client_id",
    "sign_in",
    "sign_in_again",
]
