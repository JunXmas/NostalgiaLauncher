"""Cầu nối Cape: tải danh sách theo yêu cầu, mặc/gỡ qua luồng nền, tài khoản không phải
Microsoft trả rỗng mà không chạm mạng."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from fake_microsoft import REFRESH_TOKEN
from fake_microsoft import publish as publish_microsoft
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import MICROSOFT, Account
from nostalgia.account.store import save_accounts
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.cape_bridge import CapeBridge
from test_api import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")

PLAYER_UUID = "069a79f4-44e9-4726-a5be-fca90e38aaf5"


def _bridge_with_capes(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> tuple[CapeBridge, str, ServerState]:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    handler = server._server.RequestHandlerClass
    handler.do_PUT = handler.do_POST  # type: ignore[attr-defined]
    profile_document = {
        "id": PLAYER_UUID.replace("-", ""),
        "name": "Notch",
        "capes": [{"id": "cape-1", "alias": "Migrator", "url": "http://t/x", "state": "ACTIVE"}],
    }
    launcher = replace(
        launcher,
        auth_endpoints=publish_microsoft(server, server_state),
        endpoints=replace(
            launcher.endpoints,
            profile_with_capes=server.url(
                server_state.add("/capes/profile", json.dumps(profile_document).encode())
            ),
            cape_active=server.url(server_state.add("/capes/active", b"{}")),
            mojang_session_profile=server.url("/session"),
        ),
    )
    account = Account(
        player_name="Notch",
        player_uuid=PLAYER_UUID,
        account_kind=MICROSOFT,
        access_token="ve",
        refresh_token=REFRESH_TOKEN,
        expires_at=0.0,
    )
    save_accounts(launcher.paths.accounts_json, (account,))
    bridge = CapeBridge(launcher, LauncherBridge(launcher))
    return bridge, account.account_id, server_state


def test_load_capes_fills_the_list_for_a_microsoft_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bridge, account_id, _ = _bridge_with_capes(server, server_state, tmp_path, certificate_pair)

    bridge.loadCapes(account_id)
    wait_until(lambda: bridge.loadedFor == account_id and not bridge.busy)

    assert bridge.capes == [
        {"capeId": "cape-1", "alias": "Migrator", "textureUrl": "http://t/x", "active": True}
    ]


def test_unknown_or_offline_accounts_get_an_empty_list_without_network(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bridge, _, state = _bridge_with_capes(server, server_state, tmp_path, certificate_pair)

    bridge.loadCapes("offline:khong-co")

    assert bridge.capes == [] and bridge.loadedFor == "offline:khong-co"
    assert state.request_count("/capes/profile") == 0


def test_apply_cape_puts_the_id_then_reloads(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bridge, account_id, state = _bridge_with_capes(server, server_state, tmp_path, certificate_pair)
    applied: list[str] = []
    bridge.capeApplied.connect(applied.append)

    bridge.applyCape(account_id, "cape-1")
    wait_until(lambda: bool(applied) and state.request_count("/capes/profile") > 0)

    assert json.loads(state.received_body("/capes/active")) == {"capeId": "cape-1"}


def test_a_mojang_error_reaches_the_ui_as_a_signal(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    bridge, account_id, state = _bridge_with_capes(server, server_state, tmp_path, certificate_pair)
    state.add("/capes/active", b'{"error":"not owned"}', status=400)
    errors: list[str] = []
    bridge.capeFailed.connect(errors.append)

    bridge.applyCape(account_id, "cape-la")
    wait_until(lambda: bool(errors))

    assert "not owned" in errors[0]
