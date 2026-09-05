"""Chặng mã thiết bị: chờ có hạn, chậm lại khi được bảo, và làm mới vé không cần nhập lại."""

from __future__ import annotations

import threading
import time
import uuid

import pytest

from fake_microsoft import (
    DEVICE_CODE,
    PLAYER_NAME,
    REFRESH_TOKEN,
    USER_CODE,
    VERIFICATION_URL,
    body,
    publish,
)
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.device_code import (
    DeviceCode,
    MicrosoftTokens,
    poll_for_tokens,
    request_device_code,
)
from nostalgia.auth.endpoints import CLIENT_ID_ENV, DEFAULT_CLIENT_ID
from nostalgia.auth.microsoft import resolve_client_id, sign_in, sign_in_again
from nostalgia.errors import AuthError, Cancelled
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

CLIENT_ID = "ma-ung-dung-gia"
DASHED_UUID = "b50ad385-829d-3141-a216-7e7d7539ba7f"


def test_a_misconfigured_azure_app_is_translated_into_the_fix(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Thông báo gốc của Microsoft nói bằng thuật ngữ nội bộ; người dùng cần biết PHẢI LÀM GÌ."""
    endpoints = publish(server, server_state)
    server_state.add(
        "/devicecode",
        body({"error": "invalid_client", "error_description": "AADSTS70002: bla bla"}),
        status=400,
    )

    with pytest.raises(AuthError, match="Allow public client flows"):
        sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)


def test_waiting_for_the_user_keeps_polling_until_they_finish(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """`authorization_pending` là câu trả lời BÌNH THƯỜNG khi người dùng chưa nhập xong.

    Hỏi trong một luồng riêng rồi đổi câu trả lời của máy chủ giữa chừng — đúng như người
    dùng nhập mã xong ở giữa hai lần hỏi.
    """
    endpoints = publish(server, server_state)
    device_code = request_device_code(http_client, CLIENT_ID, url=endpoints.device_code_url)
    server_state.add("/token", body({"error": "authorization_pending"}), status=400)

    result: list[MicrosoftTokens] = []

    def poll() -> None:
        result.append(
            poll_for_tokens(
                http_client, CLIENT_ID, device_code, url=endpoints.token_url, sleep_seconds=0.01
            )
        )

    worker = threading.Thread(target=poll, daemon=True)
    worker.start()
    deadline = time.monotonic() + 5
    while server_state.request_count("/token") < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server_state.request_count("/token") >= 2, "phải hỏi lại chứ không bỏ cuộc"

    server_state.add("/token", body({"access_token": "a", "refresh_token": "b", "expires_in": 10}))
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert result and result[0].access_token == "a"


def test_being_told_to_slow_down_makes_the_next_wait_longer(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Máy chủ bảo chậm lại mà vẫn hỏi dồn là bị chặn — nhưng vẫn phải có hạn dừng."""
    endpoints = publish(server, server_state)
    device_code = DeviceCode(
        user_code=USER_CODE,
        verification_url=VERIFICATION_URL,
        device_code=DEVICE_CODE,
        interval_seconds=1,
        expires_in_seconds=0,
    )
    server_state.add("/token", body({"error": "slow_down"}), status=400)

    with pytest.raises(AuthError, match="hết thời gian"):
        poll_for_tokens(
            http_client, CLIENT_ID, device_code, url=endpoints.token_url, sleep_seconds=0.0
        )


def test_polling_gives_up_when_the_code_expires(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Vòng chờ phải có hạn: không bao giờ được quay mãi."""
    endpoints = publish(server, server_state)
    server_state.add("/token", body({"error": "authorization_pending"}), status=400)
    expiring = DeviceCode(
        user_code=USER_CODE,
        verification_url=VERIFICATION_URL,
        device_code=DEVICE_CODE,
        interval_seconds=1,
        expires_in_seconds=0,
    )

    with pytest.raises(AuthError, match="hết thời gian"):
        poll_for_tokens(
            http_client, CLIENT_ID, expiring, url=endpoints.token_url, sleep_seconds=0.0
        )


def test_cancelling_does_not_wait_out_the_polling_interval(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Nhịp hỏi thật là 5 giây. Kiểm cờ huỷ SAU khi ngủ nghĩa là người dùng bấm dừng rồi
    vẫn phải ngồi đợi hết nhịp — trái đúng điều kiện "dừng trong vài giây" của M1."""
    endpoints = publish(server, server_state)
    device_code = DeviceCode(
        user_code=USER_CODE,
        verification_url=VERIFICATION_URL,
        device_code=DEVICE_CODE,
        interval_seconds=30,
        expires_in_seconds=900,
    )
    cancel_token = CancelToken()
    cancel_token.cancel()

    started = time.monotonic()
    with pytest.raises(Cancelled):
        poll_for_tokens(
            http_client, CLIENT_ID, device_code, url=endpoints.token_url, cancel_token=cancel_token
        )

    assert time.monotonic() - started < 5, "phải thoát ngay, không đợi hết nhịp 30 giây"


def test_being_told_to_slow_down_actually_lengthens_the_wait(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Máy chủ bảo chậm lại mà vẫn hỏi dồn là bị chặn. Đo bằng chính các lần ngủ.

    Vá `time.sleep` của thư viện chuẩn: `device_code.py` gọi `time.sleep`, và cả hai chỗ
    trỏ tới cùng một đối tượng module.
    """
    endpoints = publish(server, server_state)
    device_code = DeviceCode(
        user_code=USER_CODE,
        verification_url=VERIFICATION_URL,
        device_code=DEVICE_CODE,
        interval_seconds=1,
        expires_in_seconds=900,
    )
    server_state.add("/token", body({"error": "slow_down"}), status=400)
    naps: list[float] = []

    def record_nap(seconds: float) -> None:
        naps.append(seconds)
        if len(naps) >= 3:
            server_state.add(
                "/token", body({"access_token": "a", "refresh_token": "b", "expires_in": 10})
            )

    monkeypatch.setattr(time, "sleep", record_nap)
    poll_for_tokens(http_client, CLIENT_ID, device_code, url=endpoints.token_url)

    assert naps[0] == 1
    assert naps[1] > naps[0], "bị bảo chậm lại thì lần sau phải đợi lâu hơn"
    assert naps[2] > naps[1]


def test_polling_stops_when_the_user_cancels(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    device_code = request_device_code(http_client, CLIENT_ID, url=endpoints.device_code_url)
    cancel_token = CancelToken()
    cancel_token.cancel()

    with pytest.raises(Cancelled):
        poll_for_tokens(
            http_client,
            CLIENT_ID,
            device_code,
            url=endpoints.token_url,
            sleep_seconds=0.0,
            cancel_token=cancel_token,
        )


def test_refreshing_skips_the_code_entirely(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Lần chơi sau không được bắt người dùng nhập lại mã."""
    endpoints = publish(server, server_state)
    before = server_state.request_count("/devicecode")

    login = sign_in_again(http_client, CLIENT_ID, REFRESH_TOKEN, endpoints=endpoints)

    assert login.minecraft_session.player_name == PLAYER_NAME
    assert server_state.request_count("/devicecode") == before
    sent = server_state.received_body("/token").decode()
    assert "grant_type=refresh_token" in sent
    assert "refresh_token=ve-lam-moi" in sent
    assert "offline_access" in sent, "thiếu scope này là lần sau lại phải nhập mã"


def test_an_expired_refresh_token_asks_for_a_new_sign_in(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    server_state.add("/token", body({"error": "invalid_grant"}), status=400)

    with pytest.raises(AuthError, match="đăng nhập lại"):
        sign_in_again(http_client, CLIENT_ID, "ve-cu", endpoints=endpoints)


def test_the_device_code_never_shows_up_in_repr() -> None:
    """Ai cầm được mã thiết bị có thể cướp phiên đăng nhập đang chờ."""
    code = DeviceCode(
        user_code=USER_CODE,
        verification_url=VERIFICATION_URL,
        device_code="bi-mat-that",
    )
    assert "bi-mat-that" not in repr(code)
    assert USER_CODE in repr(code), "mã người dùng phải đọc được — đó là thứ họ gõ vào"


def test_the_launcher_ships_with_its_own_approved_app() -> None:
    """Người chơi không phải đăng ký gì cả — đó là điểm của việc nhúng mã ứng dụng.

    Bắt mỗi người tự đăng ký app nghĩa là họ phải chờ Microsoft duyệt tới 24 giờ mới đăng
    nhập được lần đầu.
    """
    assert resolve_client_id({}) == DEFAULT_CLIENT_ID
    assert uuid.UUID(DEFAULT_CLIENT_ID), "mã ứng dụng phải là UUID hợp lệ"


def test_a_fork_can_point_at_its_own_azure_app() -> None:
    assert resolve_client_id({CLIENT_ID_ENV: "ma-cua-fork"}) == "ma-cua-fork"
    assert resolve_client_id({CLIENT_ID_ENV: "  ma-co-khoang-trang  "}) == "ma-co-khoang-trang"


def test_an_empty_override_falls_back_to_the_built_in_app() -> None:
    """Biến môi trường đặt rỗng (hay chỉ có khoảng trắng) không được làm hỏng đăng nhập."""
    assert resolve_client_id({CLIENT_ID_ENV: ""}) == DEFAULT_CLIENT_ID
    assert resolve_client_id({CLIENT_ID_ENV: "   "}) == DEFAULT_CLIENT_ID
