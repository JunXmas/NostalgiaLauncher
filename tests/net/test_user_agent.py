"""Mọi request của HttpClient tự xưng `NostalgiaLauncher/<phiên bản>`: GitHub API trả 403 cho
request không có User-Agent (bộ tự cập nhật từng báo "Không kiểm được" vì vậy), Modrinth cũng
chặn. Người gọi vẫn đè được."""

from __future__ import annotations

from local_https_server import LocalHttpsServer, ServerState

from nostalgia import __version__
from nostalgia.net.http import HttpClient

EXPECTED_AGENT = f"NostalgiaLauncher/{__version__}"


def test_send_and_stream_identify_the_launcher(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    sent = server_state.add("/releases/latest", b"{}")
    streamed = server_state.add("/files/goi.zip", b"PK")

    http_client.send("GET", server.url(sent))
    http_client.fetch_bytes(server.url(streamed))

    assert server_state.received_header(sent, "User-Agent") == EXPECTED_AGENT
    assert server_state.received_header(streamed, "User-Agent") == EXPECTED_AGENT


def test_a_caller_can_still_override_the_agent(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/v2/search", b"{}")
    http_client.send("GET", server.url(path), headers={"User-Agent": "Rieng/1"})
    assert server_state.received_header(path, "User-Agent") == "Rieng/1"
