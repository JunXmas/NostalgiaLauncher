"""Chặng hai và ba: vé Microsoft → vé Xbox Live → vé XSTS.

Đây là chỗ luồng đăng nhập hay chết nhất, và luôn chết vì **hoàn cảnh tài khoản** chứ không
vì mã sai: tài khoản chưa từng mở hồ sơ Xbox, tài khoản ở nước Xbox Live không phục vụ, hay
tài khoản trẻ em chưa được thêm vào nhóm gia đình. XSTS trả 401 kèm một con số trong trường
`XErr`, và con số đó là toàn bộ thông tin để biết người dùng phải làm gì.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nostalgia.auth.endpoints import XBOX_LIVE_URL, XSTS_URL
from nostalgia.auth.transport import post_json, response_fields
from nostalgia.errors import AuthError, DataFileError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken

# RelyingParty quyết định vé dùng được ở đâu. Sai chuỗi này thì Minecraft Services từ chối
# một cách khó hiểu ở chặng sau, chứ không báo lỗi ngay tại đây.
XBOX_RELYING_PARTY = "http://auth.xboxlive.com"
MINECRAFT_RELYING_PARTY = "rp://api.minecraftservices.com/"
RETAIL_SANDBOX = "RETAIL"

XSTS_HINTS = {
    "2148916233": (
        "tài khoản Microsoft này chưa có hồ sơ Xbox. Tạo một hồ sơ ở xbox.com rồi thử lại."
    ),
    "2148916235": "Xbox Live không phục vụ ở quốc gia của tài khoản này.",
    "2148916236": "tài khoản cần xác minh thêm (thường là tài khoản Hàn Quốc).",
    "2148916237": "tài khoản cần xác minh thêm (thường là tài khoản Hàn Quốc).",
    "2148916238": (
        "đây là tài khoản trẻ em; phải được thêm vào một nhóm Family trước khi đăng nhập được."
    ),
}


@dataclass(frozen=True, slots=True)
class XboxTicket:
    """Vé Xbox kèm `user_hash` — Minecraft Services đòi cả hai, thiếu một là hỏng."""

    xbox_token: str = field(repr=False)
    user_hash: str = ""

    def __repr__(self) -> str:
        return f"XboxTicket(xbox_token='***', user_hash={self.user_hash!r})"


def authenticate_xbox_live(
    http_client: HttpClient,
    microsoft_access_token: str,
    *,
    url: str = XBOX_LIVE_URL,
    cancel_token: CancelToken | None = None,
) -> XboxTicket:
    """Đổi vé Microsoft lấy vé Xbox Live. Tiền tố `d=` là bắt buộc, không phải trang trí."""
    document: JsonValue = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={microsoft_access_token}",
        },
        "RelyingParty": XBOX_RELYING_PARTY,
        "TokenType": "JWT",
    }
    response = post_json(http_client, url, document, cancel_token=cancel_token)
    if not response.is_ok:
        message = f"Xbox Live từ chối vé Microsoft (HTTP {response.status})"
        raise AuthError(message)
    return _parse_ticket(response_fields(response, what="vé Xbox Live"))


def authorize_xsts(
    http_client: HttpClient,
    xbox_token: str,
    *,
    url: str = XSTS_URL,
    cancel_token: CancelToken | None = None,
) -> XboxTicket:
    """Xin quyền dùng vé Xbox cho riêng Minecraft."""
    document: JsonValue = {
        "Properties": {"SandboxId": RETAIL_SANDBOX, "UserTokens": [xbox_token]},
        "RelyingParty": MINECRAFT_RELYING_PARTY,
        "TokenType": "JWT",
    }
    response = post_json(http_client, url, document, cancel_token=cancel_token)
    if not response.is_ok:
        raise AuthError(_explain_xsts(response.status, response.body))
    return _parse_ticket(response_fields(response, what="vé XSTS"))


def _parse_ticket(fields: dict[str, JsonValue]) -> XboxTicket:
    xbox_token = as_string(fields.get("Token"))
    claims = as_list(as_mapping(fields.get("DisplayClaims")).get("xui"))
    user_hash = as_string(as_mapping(next(iter(claims), None)).get("uhs")) if claims else None
    if not xbox_token or not user_hash:
        message = "Xbox trả về vé thiếu Token hoặc user hash"
        raise AuthError(message)
    return XboxTicket(xbox_token=xbox_token, user_hash=user_hash)


def _explain_xsts(status: int, body: bytes) -> str:
    """Con số trong `XErr` là toàn bộ thông tin về việc người dùng phải làm."""
    try:
        fields = as_mapping(decode_json(body, what="lỗi XSTS"))
    except DataFileError:
        # Thân lỗi hỏng thì vẫn phải nói được điều gì đó — im lặng là tệ nhất.
        return f"XSTS từ chối (HTTP {status})"
    error_code = fields.get("XErr")
    key = str(error_code) if error_code is not None else ""
    hint = XSTS_HINTS.get(key)
    return (
        f"XErr {key}: {hint}" if hint else f"XSTS từ chối (HTTP {status}, XErr={key or 'không rõ'})"
    )
