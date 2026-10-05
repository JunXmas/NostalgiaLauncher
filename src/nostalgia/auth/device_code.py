"""Chặng một: lấy mã thiết bị, chờ người dùng nhập, rồi đổi lấy vé Microsoft.

Chọn device code flow chứ không phải mở trình duyệt kèm redirect: ứng dụng desktop không
cần nhúng cả một trình duyệt, không cần mở cổng nghe cục bộ, và **không cần client secret**
— thứ mà một ứng dụng chạy trên máy người dùng không thể giữ bí mật được.

Vòng chờ ở đây có **ba lối ra**, không lối nào là chờ mãi: người dùng nhập xong, mã hết hạn
theo đúng thời hạn máy chủ công bố, hoặc người dùng bấm dừng.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field

from nostalgia.auth.endpoints import DEVICE_CODE_GRANT, DEVICE_CODE_URL, SCOPE, TOKEN_URL
from nostalgia.auth.transport import post_form, response_fields
from nostalgia.errors import AuthError
from nostalgia.model.json_value import JsonValue, as_integer, as_string
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

AUTHORIZATION_PENDING = "authorization_pending"
SLOW_DOWN = "slow_down"

# Máy chủ bảo chậm lại thì phải chậm thật. Microsoft cộng thêm 5 giây mỗi lần bị nhắc.
SLOW_DOWN_EXTRA_SECONDS = 5

# Nhịp hỏi tối thiểu khi máy chủ không nói gì, và trần để một giá trị lạ không làm treo.
DEFAULT_INTERVAL_SECONDS = 5
MAX_INTERVAL_SECONDS = 60
MAX_EXPIRES_SECONDS = 30 * 60

# Vài mã lỗi của Azure AD hay gặp lúc mới dựng app. Thông báo gốc nói bằng thuật ngữ nội bộ,
# nên dịch thẳng sang VIỆC NGƯỜI DÙNG PHẢI LÀM.
AAD_HINTS = {
    "AADSTS70002": (
        "app Azure chưa bật 'Allow public client flows'. Vào portal.azure.com → "
        "App registrations → app của bạn → Authentication → Advanced settings → "
        "Allow public client flows: Yes → Save."
    ),
    "AADSTS700016": (
        "không tìm thấy app nào với mã này. Kiểm lại Application (client) ID, và "
        "Supported account types phải là 'Personal Microsoft accounts only'."
    ),
    "AADSTS50194": (
        "app đang là single-tenant nên không dùng được endpoint 'consumers'. Đổi "
        "Supported account types sang 'Personal Microsoft accounts only'."
    ),
}


@dataclass(frozen=True, slots=True)
class DeviceCode:
    """Mã để người dùng nhập, kèm mã bí mật để ta hỏi kết quả."""

    user_code: str
    verification_url: str
    device_code: str = field(repr=False)
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    expires_in_seconds: int = MAX_EXPIRES_SECONDS

    def __repr__(self) -> str:
        """Che `device_code`: ai cầm được nó có thể cướp phiên đăng nhập đang chờ."""
        return (
            f"DeviceCode(user_code={self.user_code!r}, "
            f"verification_url={self.verification_url!r}, device_code='***')"
        )


@dataclass(frozen=True, slots=True)
class MicrosoftTokens:
    """Vé Microsoft. `refresh_token` là thứ giữ cho lần chơi sau khỏi phải đăng nhập lại."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in_seconds: int = 0

    def __repr__(self) -> str:
        return (
            "MicrosoftTokens(access_token='***', refresh_token='***', "
            f"expires_in_seconds={self.expires_in_seconds})"
        )


def request_device_code(
    http_client: HttpClient,
    client_id: str,
    *,
    url: str = DEVICE_CODE_URL,
    cancel_token: CancelToken | None = None,
) -> DeviceCode:
    """Xin một mã để người dùng nhập trên microsoft.com/link."""
    response = post_form(
        http_client, url, {"client_id": client_id, "scope": SCOPE}, cancel_token=cancel_token
    )
    fields = response_fields(response, what="mã thiết bị")
    if not response.is_ok:
        raise AuthError(_explain(fields))

    device_code = as_string(fields.get("device_code"))
    user_code = as_string(fields.get("user_code"))
    verification_url = as_string(fields.get("verification_uri"))
    if not device_code or not user_code or not verification_url:
        message = "Microsoft trả về mã thiết bị thiếu trường bắt buộc"
        raise AuthError(message)

    return DeviceCode(
        user_code=user_code,
        verification_url=verification_url,
        device_code=device_code,
        interval_seconds=_bounded(
            as_integer(fields.get("interval")), DEFAULT_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS
        ),
        expires_in_seconds=_bounded(
            as_integer(fields.get("expires_in")), MAX_EXPIRES_SECONDS, MAX_EXPIRES_SECONDS
        ),
    )


def poll_for_tokens(
    http_client: HttpClient,
    client_id: str,
    device_code: DeviceCode,
    *,
    url: str = TOKEN_URL,
    sleep_seconds: float | None = None,
    cancel_token: CancelToken | None = None,
) -> MicrosoftTokens:
    """Hỏi lại cho tới khi người dùng nhập xong, hết hạn, hoặc bị bấm dừng.

    `sleep_seconds` chỉ để test rút ngắn nhịp chờ; mặc định theo đúng nhịp máy chủ yêu cầu.
    """
    interval = device_code.interval_seconds if sleep_seconds is None else sleep_seconds
    deadline = time.monotonic() + device_code.expires_in_seconds
    while time.monotonic() < deadline:
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        time.sleep(interval)
        response = post_form(
            http_client,
            url,
            {
                "client_id": client_id,
                "grant_type": DEVICE_CODE_GRANT,
                "device_code": device_code.device_code,
            },
            cancel_token=cancel_token,
        )
        fields = response_fields(response, what="vé Microsoft")
        if response.is_ok:
            return _parse_tokens(fields)
        error = as_string(fields.get("error"))
        if error == AUTHORIZATION_PENDING:
            continue
        if error == SLOW_DOWN:
            interval = min(interval + SLOW_DOWN_EXTRA_SECONDS, MAX_INTERVAL_SECONDS)
            continue
        raise AuthError(_explain(fields))

    message = "hết thời gian chờ nhập mã trên microsoft.com/link"
    raise AuthError(message)


def refresh_tokens(
    http_client: HttpClient,
    client_id: str,
    refresh_token: str,
    *,
    url: str = TOKEN_URL,
    cancel_token: CancelToken | None = None,
) -> MicrosoftTokens:
    """Đổi refresh token lấy vé mới. Hỏng nghĩa là phải đăng nhập lại từ đầu."""
    response = post_form(
        http_client,
        url,
        {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPE,
        },
        cancel_token=cancel_token,
    )
    if not response.is_ok:
        message = "vé làm mới đã hết hiệu lực — cần đăng nhập lại"
        raise AuthError(message)
    return _parse_tokens(response_fields(response, what="vé Microsoft"))


def _parse_tokens(fields: Mapping[str, JsonValue]) -> MicrosoftTokens:
    access_token = as_string(fields.get("access_token"))
    refresh_token = as_string(fields.get("refresh_token"))
    if not access_token or not refresh_token:
        message = "Microsoft trả về vé thiếu access_token hoặc refresh_token"
        raise AuthError(message)
    return MicrosoftTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=as_integer(fields.get("expires_in")) or 0,
    )


def _explain(fields: Mapping[str, JsonValue]) -> str:
    """Dịch lỗi của Azure sang việc phải làm; không khớp thì đưa nguyên văn cho người dùng."""
    description = as_string(fields.get("error_description")) or ""
    for aad_code, hint in AAD_HINTS.items():
        if aad_code in description:
            return f"{aad_code}: {hint}"
    error = as_string(fields.get("error")) or "không rõ"
    return f"Microsoft từ chối ({error}): {description[:300]}"


def _bounded(value: int | None, fallback: int, ceiling: int) -> int:
    if value is None or value <= 0:
        return fallback
    return min(value, ceiling)
