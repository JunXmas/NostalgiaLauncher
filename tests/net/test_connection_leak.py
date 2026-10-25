"""Treo launcher vài giờ thì Thư viện chết: mỗi job nền chạy trên một luồng mới, và HttpClient
dùng chung giữ tham chiếu mạnh tới kết nối của từng luồng đã chết — socket không bao giờ đóng,
các vòng poll 5-15 giây rò tới cạn file descriptor."""

from __future__ import annotations

import gc
import threading

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.net.http import HttpClient


def test_connections_of_finished_threads_are_released(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    path = server_state.add("/v1/poll", b"{}")
    for _ in range(50):
        worker = threading.Thread(target=lambda: http_client.send("GET", server.url(path)))
        worker.start()
        worker.join()
    gc.collect()
    assert len(http_client._connections) == 0
    # Kết nối của luồng còn sống vẫn được giữ và dùng lại như cũ.
    http_client.send("GET", server.url(path))
    assert len(http_client._connections) == 1
