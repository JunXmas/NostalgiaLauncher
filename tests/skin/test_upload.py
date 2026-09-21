"""Upload skin lên Mojang: PUT thật qua server giả, vé hết hạn tự làm mới, và kiểm kích
thước PNG trước khi gửi — Mojang từ chối muộn với thông báo khó hiểu."""

from __future__ import annotations

import struct
from dataclasses import replace
from pathlib import Path

import pytest

from fake_microsoft import MINECRAFT_TOKEN, REFRESH_TOKEN
from fake_microsoft import publish as publish_microsoft
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import MICROSOFT, Account
from nostalgia.account.store import save_accounts
from nostalgia.errors import AccountError
from nostalgia.skin.upload import MAX_SKIN_SIZE, upload_skin_to_mojang
from test_api import make_launcher

PLAYER_UUID = "069a79f4-44e9-4726-a5be-fca90e38aaf5"


def png_bytes(width: int, height: int) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data


def _install_put_support(server: LocalHttpsServer) -> None:
    handler = server._server.RequestHandlerClass
    handler.do_PUT = handler.do_POST  # type: ignore[attr-defined]


def test_upload_succeeds_and_server_receives_the_bytes(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    _install_put_support(server)
    upload_path = server_state.add("/minecraft/profile/skins", b"", status=204)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, skin_upload=server.url(upload_path))
    )
    skin_path = tmp_path / "skin.png"
    skin_path.write_bytes(png_bytes(64, 64))

    with launcher.make_http_client() as http_client:
        upload_skin_to_mojang(
            http_client, "ve-hop-le", skin_path, slim=True, endpoints=launcher.endpoints
        )

    assert server_state.request_count(upload_path) == 1
    assert server_state.received_header(upload_path, "Authorization") == "Bearer ve-hop-le"
    assert b"variant" in server_state.received_body(upload_path)
    assert b"slim" in server_state.received_body(upload_path)


def test_a_401_from_mojang_is_reported_in_vietnamese(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    _install_put_support(server)
    upload_path = server_state.add(
        "/minecraft/profile/skins", b'{"error":"Unauthorized"}', status=401
    )
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, skin_upload=server.url(upload_path))
    )
    skin_path = tmp_path / "skin.png"
    skin_path.write_bytes(png_bytes(64, 64))

    with launcher.make_http_client() as http_client, pytest.raises(AccountError, match="401"):
        upload_skin_to_mojang(http_client, "ve-het-han", skin_path, endpoints=launcher.endpoints)


def test_wrong_dimensions_are_rejected_before_touching_the_network(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    upload_path = server_state.add("/minecraft/profile/skins", b"", status=204)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, skin_upload=server.url(upload_path))
    )
    skin_path = tmp_path / "skin.png"
    skin_path.write_bytes(png_bytes(100, 50))

    with launcher.make_http_client() as http_client, pytest.raises(AccountError, match="100x50"):
        upload_skin_to_mojang(http_client, "ve", skin_path, endpoints=launcher.endpoints)

    assert server_state.request_count(upload_path) == 0, "sai kích thước thì không được gọi mạng"


def test_an_oversized_file_is_rejected_before_touching_the_network(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    upload_path = server_state.add("/minecraft/profile/skins", b"", status=204)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, skin_upload=server.url(upload_path))
    )
    skin_path = tmp_path / "skin.png"
    skin_path.write_bytes(png_bytes(64, 64) + b"zero" * (MAX_SKIN_SIZE // 4 + 1))

    with launcher.make_http_client() as http_client, pytest.raises(AccountError, match="quá lớn"):
        upload_skin_to_mojang(http_client, "ve", skin_path, endpoints=launcher.endpoints)

    assert server_state.request_count(upload_path) == 0


def test_upload_skin_refreshes_an_expired_microsoft_ticket_first(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    _install_put_support(server)
    auth_endpoints = publish_microsoft(server, server_state)
    upload_path = server_state.add("/minecraft/profile/skins", b"", status=204)
    launcher = replace(
        launcher,
        auth_endpoints=auth_endpoints,
        endpoints=replace(
            launcher.endpoints,
            skin_upload=server.url(upload_path),
            mojang_session_profile=server.url("/session"),
        ),
    )
    stale = Account(
        player_name="Notch",
        player_uuid=PLAYER_UUID,
        account_kind=MICROSOFT,
        access_token="ve-cu-het-han",
        refresh_token=REFRESH_TOKEN,
        expires_at=0.0,
    )
    save_accounts(launcher.paths.accounts_json, (stale,))
    skin_path = tmp_path / "skin.png"
    skin_path.write_bytes(png_bytes(64, 64))

    launcher.upload_skin(stale, skin_path)

    expected = "Bearer " + MINECRAFT_TOKEN
    assert server_state.received_header(upload_path, "Authorization") == expected
