"""Quan sát request tại máy chủ HTTPS thật, tách thống kê khỏi tải nội dung chức năng."""

import json
import ssl
from pathlib import Path

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.net.http import HttpClient
from nostalgia.settings.store import Settings, save_settings
from nostalgia.usage.collector import UsageCollector
from nostalgia.usage.configuration import UsageConfiguration


def test_real_https_is_silent_until_consent_and_after_revocation(
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    server: LocalHttpsServer,
    server_state: ServerState,
) -> None:
    certificate, _key = certificate_pair
    context = ssl.create_default_context(cafile=str(certificate))
    server_state.add("/v1/usage", b"{}")
    server_state.add("/content", b"requested content")

    def make_http_client() -> HttpClient:
        return HttpClient(tls_context=context, timeout_seconds=3)

    collector = UsageCollector(
        tmp_path,
        UsageConfiguration(server.url("/v1/usage"), True),
        "1.2.2",
        "linux",
        make_http_client=make_http_client,
        today=lambda: "2026-11-05",
    )
    for choice in ("unselected", "declined"):
        save_settings(tmp_path, Settings(usage_choice_v1=choice))
        collector.resume()
        assert collector.new_attempt() is None
        with make_http_client() as functional:
            assert functional.send("GET", server.url("/content")).body == b"requested content"
    assert server_state.request_count("/v1/usage") == 0
    assert server_state.request_count("/content") == 2
    save_settings(tmp_path, Settings(usage_choice_v1="accepted"))
    collector.resume()
    attempt = collector.new_attempt()
    assert attempt is not None
    collector.send_active(attempt)
    assert server_state.request_count("/v1/usage") == 1
    assert json.loads(server_state.received_body("/v1/usage"))["event"] == "installation_active"
    assert not server_state.received_header("/v1/usage", "Authorization")
    assert not server_state.received_header("/v1/usage", "Cookie")
    save_settings(tmp_path, Settings(usage_choice_v1="declined"))
    collector.revoke()
    collector.send_active(attempt)
    assert collector.new_attempt() is None
    assert server_state.request_count("/v1/usage") == 1
    assert not (tmp_path / "usage-day.json").exists()
