"""Một Microsoft + Xbox + Minecraft Services giả, đủ để đi trọn luồng đăng nhập offline.

Dựng đúng bốn máy chủ thật mà một lần đăng nhập phải đi qua, trên cùng một máy chủ cục bộ.
Nhờ vậy mọi nhánh hỏng — app chưa duyệt, chưa có hồ sơ Xbox, chưa mua game — đều kiểm được
mà không cần tài khoản thật và không cần mã ứng dụng Azure nào.
"""

from __future__ import annotations

import json

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.endpoints import AuthEndpoints

USER_CODE = "ABCD-EFGH"
DEVICE_CODE = "ma-thiet-bi-bi-mat"
VERIFICATION_URL = "https://microsoft.com/link"
MICROSOFT_ACCESS_TOKEN = "ve-microsoft"
REFRESH_TOKEN = "ve-lam-moi"
XBOX_TOKEN = "ve-xbox"
USER_HASH = "1234567890"
XSTS_TOKEN = "ve-xsts"
MINECRAFT_TOKEN = "ve-minecraft"
PLAYER_UUID_UNDASHED = "b50ad385829d3141a2167e7d7539ba7f"
PLAYER_NAME = "Notch"


def body(document: object) -> bytes:
    return json.dumps(document).encode()


def publish(server: LocalHttpsServer, state: ServerState) -> AuthEndpoints:
    """Đăng ký cả bốn chặng ở trạng thái "mọi thứ suôn sẻ"."""
    device_code = state.add(
        "/devicecode",
        body(
            {
                "device_code": DEVICE_CODE,
                "user_code": USER_CODE,
                "verification_uri": VERIFICATION_URL,
                "interval": 1,
                "expires_in": 900,
            }
        ),
    )
    token_route = state.add(
        "/token",
        body(
            {
                "access_token": MICROSOFT_ACCESS_TOKEN,
                "refresh_token": REFRESH_TOKEN,
                "expires_in": 3600,
            }
        ),
    )
    xbox_live = state.add(
        "/xbox",
        body({"Token": XBOX_TOKEN, "DisplayClaims": {"xui": [{"uhs": USER_HASH}]}}),
    )
    xsts = state.add(
        "/xsts", body({"Token": XSTS_TOKEN, "DisplayClaims": {"xui": [{"uhs": USER_HASH}]}})
    )
    minecraft_login = state.add("/mc-login", body({"access_token": MINECRAFT_TOKEN}))
    minecraft_profile = state.add(
        "/mc-profile", body({"id": PLAYER_UUID_UNDASHED, "name": PLAYER_NAME})
    )
    return AuthEndpoints(
        device_code_url=server.url(device_code),
        token_url=server.url(token_route),
        xbox_live_url=server.url(xbox_live),
        xsts_url=server.url(xsts),
        minecraft_login_url=server.url(minecraft_login),
        minecraft_profile_url=server.url(minecraft_profile),
    )
