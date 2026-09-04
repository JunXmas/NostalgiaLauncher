"""`HttpClient.send`: gửi được thân request, và KHÔNG ném lỗi khi máy chủ trả 4xx."""

from __future__ import annotations

import json

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import Cancelled, DataFileError, NetworkError
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken

FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


def test_a_post_body_reaches_the_server_untouched(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/token", b'{"access_token":"abc"}')

    response = http_client.send(
        "POST",
        server.url(path),
        body=b"client_id=x&scope=y",
        headers={"Content-Type": FORM_CONTENT_TYPE},
    )

    assert response.is_ok
    assert response.body == b'{"access_token":"abc"}'
    assert server_state.received_body(path) == b"client_id=x&scope=y"
    assert server_state.received_header(path, "Content-Type") == FORM_CONTENT_TYPE


def test_a_four_hundred_is_returned_not_raised(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Với đăng nhập, thân của phản hồi lỗi MỚI là dữ liệu — ném lỗi là vứt nó đi.

    Đây đúng hình dạng Microsoft trả khi app Azure chưa bật "Allow public client flows".
    """
    body = json.dumps({"error": "invalid_client", "error_description": "AADSTS70002: ..."}).encode()
    path = server_state.add("/token", body, status=400)

    response = http_client.send("POST", server.url(path), body=b"x=1")

    assert response.status == 400
    assert not response.is_ok
    assert b"AADSTS70002" in response.body


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_every_error_status_comes_back_with_its_body(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, status: int
) -> None:
    path = server_state.add(f"/loi-{status}", b'{"XErr":"2148916233"}', status=status)

    response = http_client.send("POST", server.url(path), body=b"")

    assert response.status == status
    assert b"2148916233" in response.body


def test_headers_from_the_caller_are_sent(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/profile", b"{}")

    http_client.send("GET", server.url(path), headers={"Authorization": "Bearer ve-cua-toi"})

    assert server_state.received_header(path, "Authorization") == "Bearer ve-cua-toi"


def test_the_connection_stays_usable_after_an_error_response(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Bỏ sót thân phản hồi lỗi thì request kế tiếp đọc nhầm phần còn sót của nó."""
    bad = server_state.add("/hong", b'{"error":"pending"}', status=400)
    good = server_state.add("/tot", b'{"ok":true}')

    for _ in range(3):
        assert http_client.send("POST", server.url(bad), body=b"").status == 400
        assert http_client.send("POST", server.url(good), body=b"").body == b'{"ok":true}'


def test_an_oversized_response_is_refused_and_does_not_poison_the_connection(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Trần là bắt buộc: một máy chủ hỏng không được phép làm ta hết bộ nhớ.

    Và phần thân chưa đọc hết phải khiến kết nối bị bỏ đi: dùng lại nó thì request kế tiếp
    đọc nhầm phần còn sót của phản hồi trước, hỏng theo cách rất khó truy.
    """
    oversized = server_state.add("/to", b"x" * 5000)
    normal = server_state.add("/binh-thuong", b'{"ok":true}')

    with pytest.raises(NetworkError, match="vượt"):
        http_client.send("GET", server.url(oversized), max_bytes=1000)

    assert http_client.send("GET", server.url(normal)).body == b'{"ok":true}'


def test_a_response_exactly_at_the_limit_is_allowed(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/vua", b"x" * 1000)
    assert len(http_client.send("GET", server.url(path), max_bytes=1000).body) == 1000


def test_a_transport_failure_still_raises(http_client: HttpClient) -> None:
    """Không nối được máy chủ là hỏng THẬT, khác hẳn với việc máy chủ trả mã lỗi."""
    with pytest.raises(NetworkError, match="không gọi được"):
        http_client.send("GET", "https://localhost:1/khong-co-ai")


def test_a_cancelled_request_never_leaves(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/bat-ky", b"{}")
    cancel_token = CancelToken()
    cancel_token.cancel()

    with pytest.raises(Cancelled):
        http_client.send("GET", server.url(path), cancel_token=cancel_token)

    assert server_state.request_count(path) == 0


def test_decoding_names_the_document_that_is_broken() -> None:
    assert decode_json(b'{"a":1}', what="thu") == {"a": 1}
    with pytest.raises(DataFileError, match="phiên đăng nhập"):
        decode_json(b"{khong phai json", what="phiên đăng nhập")
