"""Biến một lần đăng nhập Microsoft thành tài khoản lưu được, và giữ nó còn hiệu lực.

Ranh giới ở đây có chủ ý: `auth/` biết **giao thức**, còn module này biết **kho tài khoản**.
Nhờ vậy `auth/` không cần biết tài khoản được lưu ở đâu, và đổi cách lưu không phải đụng vào
bốn chặng đăng nhập.

Thời gian được **truyền vào** chứ không đọc từ đồng hồ hệ thống. Một hàm tự gọi `time.time()`
chỉ kiểm được bằng cách vá đồng hồ toàn cục — thứ để lại trạng thái cho mọi test chạy sau.
"""

from __future__ import annotations

from nostalgia.account.model import MICROSOFT, Account
from nostalgia.account.offline import offline_uuid
from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.auth.microsoft import MicrosoftLogin, sign_in_again
from nostalgia.errors import AuthError
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

# Làm mới sớm hơn hạn một chút. Vé hết hạn giữa lúc game đang khởi động thì người chơi nhận
# một màn hình lỗi chẳng liên quan gì tới đăng nhập.
REFRESH_MARGIN_SECONDS = 300.0

DEMO_PLAYER_NAME = "Demo"


def build_microsoft_account(login: MicrosoftLogin, *, now: float) -> Account:
    """Dựng tài khoản từ kết quả đăng nhập.

    Tài khoản chưa mua game vẫn lưu được: người chơi vẫn vào được bản dùng thử, và lần sau
    họ không phải đăng nhập lại chỉ để biết mình vẫn chưa mua.

    Tài khoản demo **không có hồ sơ Minecraft**, tức không có UUID. Nhưng lệnh khởi động vẫn
    cần một UUID, và kho tài khoản từ chối bản ghi không có — lưu được mà đọc lại thì mất.
    Nên ở đây sinh UUID theo đúng công thức offline: ổn định qua các lần chạy, và hợp lệ.
    Hệ quả đã biết: hai tài khoản demo khác nhau trên cùng một máy sẽ trùng chỗ; chuyện đó
    chờ tới khi có ai thật sự cần.
    """
    minecraft_session = login.minecraft_session
    player_name = minecraft_session.player_name or DEMO_PLAYER_NAME
    return Account(
        player_name=player_name,
        player_uuid=minecraft_session.player_uuid or offline_uuid(player_name),
        account_kind=MICROSOFT,
        access_token=minecraft_session.access_token,
        refresh_token=login.tokens.refresh_token,
        expires_at=now + login.tokens.expires_in_seconds,
    )


def needs_refresh(account: Account, *, now: float, margin: float = REFRESH_MARGIN_SECONDS) -> bool:
    """Tài khoản Microsoft đã tới lúc làm mới chưa.

    Tài khoản offline không bao giờ cần; tài khoản không rõ hạn (`expires_at == 0`) thì coi
    như cần — thà tốn một vòng gọi còn hơn khởi động game với vé đã chết.
    """
    if account.account_kind != MICROSOFT or not account.refresh_token:
        return False
    return account.expires_at <= now + margin


def refresh_account(
    http_client: HttpClient,
    client_id: str,
    account: Account,
    *,
    now: float,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> Account:
    """Làm mới vé và trả về tài khoản đã cập nhật. Giữ nguyên tên người chơi đang lưu.

    Ném `AuthError` khi vé làm mới đã chết — người gọi phải mời người dùng đăng nhập lại chứ
    không được lặng lẽ chạy tiếp với vé cũ.
    """
    if not account.refresh_token:
        message = f"tài khoản {account.player_name!r} không có vé làm mới — cần đăng nhập lại"
        raise AuthError(message)
    login = sign_in_again(
        http_client,
        client_id,
        account.refresh_token,
        endpoints=endpoints,
        cancel_token=cancel_token,
    )
    refreshed = build_microsoft_account(login, now=now)
    # Mojang có thể đổi tên hiển thị; lấy theo bản vừa nhận, nhưng nếu bản mới không có tên
    # (tài khoản demo) thì giữ tên cũ để danh sách tài khoản không đột nhiên đổi.
    if login.minecraft_session.player_name:
        return refreshed
    return Account(
        player_name=account.player_name,
        player_uuid=refreshed.player_uuid or account.player_uuid,
        account_kind=MICROSOFT,
        access_token=refreshed.access_token,
        refresh_token=refreshed.refresh_token,
        expires_at=refreshed.expires_at,
    )
