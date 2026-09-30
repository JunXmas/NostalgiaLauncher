"""Cape Mojang qua facade: liệt kê cái sở hữu, mặc, gỡ — chỉ tài khoản Microsoft.

Route giả dựng đúng hình dạng tài liệu Mojang (GET profile trả ``capes[]`` với
``state: ACTIVE``; PUT/DELETE ``capes/active``)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from fake_microsoft import MINECRAFT_TOKEN, REFRESH_TOKEN
from fake_microsoft import publish as publish_microsoft
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.errors import AccountError
from test_api import make_launcher

PLAYER_UUID = "069a79f4-44e9-4726-a5be-fca90e38aaf5"

PROFILE_WITH_TWO_CAPES = {
    "id": PLAYER_UUID.replace("-", ""),
    "name": "Notch",
    "capes": [
        {
            "id": "cape-migrator",
            "alias": "Migrator",
            "url": "http://textures.minecraft.net/texture/migrator",
            "state": "ACTIVE",
        },
        {
            "id": "cape-vanilla",
            "alias": "Vanilla",
            "url": "http://textures.minecraft.net/texture/vanilla",
            "state": "INACTIVE",
        },
    ],
}


def _install_extra_methods(server: LocalHttpsServer) -> None:
    handler = server._server.RequestHandlerClass
    handler.do_PUT = handler.do_POST  # type: ignore[attr-defined]
    handler.do_DELETE = handler.do_GET  # type: ignore[attr-defined]


def _cape_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> tuple[Launcher, Account]:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    _install_extra_methods(server)
    profile_path = server_state.add("/capes/profile", json.dumps(PROFILE_WITH_TWO_CAPES).encode())
    active_path = server_state.add("/capes/active", b"{}")
    launcher = replace(
        launcher,
        auth_endpoints=publish_microsoft(server, server_state),
        endpoints=replace(
            launcher.endpoints,
            profile_with_capes=server.url(profile_path),
            cape_active=server.url(active_path),
            mojang_session_profile=server.url("/session"),
        ),
    )
    account = Account(
        player_name="Notch",
        player_uuid=PLAYER_UUID,
        account_kind=MICROSOFT,
        access_token="ve-cu",
        refresh_token=REFRESH_TOKEN,
        expires_at=0.0,  # hết hạn → facade phải làm mới vé trước, như luồng upload skin
    )
    save_accounts(launcher.paths.accounts_json, (account,))
    return launcher, account


def test_list_capes_returns_owned_capes_with_the_active_flag(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, account = _cape_launcher(server, server_state, tmp_path, certificate_pair)

    capes = launcher.list_capes(account)

    assert [(c.cape_id, c.alias, c.active) for c in capes] == [
        ("cape-migrator", "Migrator", True),
        ("cape-vanilla", "Vanilla", False),
    ]
    # Vé hết hạn phải được làm mới trước khi hỏi Mojang.
    auth = server_state.received_header("/capes/profile", "Authorization")
    assert auth == f"Bearer {MINECRAFT_TOKEN}"


def test_a_profile_without_capes_is_empty_not_an_error(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Đa số người chơi không có cape nào — đó là chuyện thường, không phải lỗi."""
    launcher, account = _cape_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add(
        "/capes/profile",
        json.dumps({"id": PLAYER_UUID.replace("-", ""), "name": "Notch"}).encode(),
    )
    assert launcher.list_capes(account) == ()


def test_list_capes_for_non_microsoft_accounts_is_empty_without_network(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, _ = _cape_launcher(server, server_state, tmp_path, certificate_pair)
    ely = Account(player_name="JunBob", player_uuid=PLAYER_UUID, account_kind=ELY)

    assert launcher.list_capes(ely) == ()
    assert server_state.request_count("/capes/profile") == 0


def test_set_cape_puts_the_id_and_refreshes_the_cache(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, account = _cape_launcher(server, server_state, tmp_path, certificate_pair)

    launcher.set_cape(account, "cape-vanilla")

    body = json.loads(server_state.received_body("/capes/active"))
    assert body == {"capeId": "cape-vanilla"}
    auth = server_state.received_header("/capes/active", "Authorization")
    assert auth == f"Bearer {MINECRAFT_TOKEN}"


def test_an_empty_cape_id_removes_the_cape_with_a_delete(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, account = _cape_launcher(server, server_state, tmp_path, certificate_pair)

    launcher.set_cape(account, "")

    assert server_state.request_count("/capes/active") == 1
    assert server_state.received_body("/capes/active") == b""


def test_set_cape_refuses_non_microsoft_accounts(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, _ = _cape_launcher(server, server_state, tmp_path, certificate_pair)
    ely = Account(player_name="JunBob", player_uuid=PLAYER_UUID, account_kind=ELY)

    with pytest.raises(AccountError, match="Microsoft"):
        launcher.set_cape(ely, "cape-x")


def test_a_mojang_rejection_is_reported_with_its_body(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, account = _cape_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add("/capes/active", b'{"error":"cape not owned"}', status=400)

    with pytest.raises(AccountError, match="cape not owned"):
        launcher.set_cape(account, "cape-la")
