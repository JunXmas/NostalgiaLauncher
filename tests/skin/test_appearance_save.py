"""Lưu bản xem trước gửi đúng bytes/dáng tay qua Mojang và phiên web Ely.by thật."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_ely_upload import make_ely_web_launcher

import fake_ely
from fake_microsoft import MINECRAFT_TOKEN, REFRESH_TOKEN
from fake_microsoft import publish as publish_microsoft
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import MICROSOFT, Account
from nostalgia.account.store import save_accounts
from nostalgia.errors import AccountError
from nostalgia.skin.editor import save_texture
from test_api import make_launcher


def skin_png(tmp_path: Path) -> Path:
    path = tmp_path / "preview.png"
    save_texture([[(50, 100, 200, 255)] * 64 for _ in range(64)], path)
    return path


@pytest.mark.parametrize("slim", [False, True])
def test_microsoft_saves_preview_with_requested_variant_and_correct_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    slim: bool,
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.add_offline_account("SameName")
    account = Account(
        "SameName", "069a79f4-44e9-4726-a5be-fca90e38aaf5", MICROSOFT, refresh_token=REFRESH_TOKEN
    )
    save_accounts(launcher.paths.accounts_json, (*launcher.list_accounts(), account))
    launcher = replace(
        launcher,
        auth_endpoints=publish_microsoft(server, server_state),
        endpoints=replace(
            launcher.endpoints,
            skin_upload=server.url("/skins/upload"),
            mojang_session_profile=server.url("/session"),
        ),
    )
    handler = server._server.RequestHandlerClass
    # HTTPServer chú kiểu factory; fixture dùng lớp handler với route POST làm PUT.
    handler.do_PUT = handler.do_POST  # type: ignore[attr-defined]
    server_state.add("/skins/upload", b"", status=204)
    path = skin_png(tmp_path)
    launcher.save_skin_selection(account, path, slim=slim)
    body = server_state.received_body("/skins/upload")
    assert path.read_bytes() in body
    assert (b"slim" if slim else b"classic") in body
    assert (
        server_state.received_header("/skins/upload", "Authorization")
        == "Bearer " + MINECRAFT_TOKEN
    )


@pytest.mark.parametrize("edit", [False, True])
def test_ely_save_confirms_model_before_wearing_uploaded_skin(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    edit: bool,
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau")
    server_state.add(
        "/elysite/skins/s4242",
        (
            "alight.service.skin = "
            + json.dumps({"is_slim": not edit, "color": "935614", "tags": ["Original"]})
            + ";"
        ).encode(),
    )
    server_state.add(
        "/elysite/skins/s4242/edit",
        b'<form id="formEditSkin" method="POST" action="/elysite/api/legacy/skins/4242">'
        b'<input type="hidden" name="csrf" value="proof">'
        b'<input name="color" value="{{skin.color}}"><input name="tags[]" value="{{tag}}">'
        b'<select name="is_slim"></select></form>',
    )
    server_state.add("/elysite/api/legacy/skins/4242", b'{"skin":{"is_slim":true}}')
    path = skin_png(tmp_path)
    server_state.add(f"/ely/skins/{fake_ely.ELY_NAME}.png", path.read_bytes())
    launcher.save_skin_selection(account, path, slim=True)
    assert path.read_bytes() in server_state.received_body("/elysite/api/legacy/skins")
    assert b"skinId=4242" in server_state.received_body("/elysite/api/legacy/users/skin")
    if edit:
        assert b"is_slim=1" in server_state.received_body("/elysite/api/legacy/skins/4242")
        assert b"csrf=proof" in server_state.received_body("/elysite/api/legacy/skins/4242")
        assert b"color=935614" in server_state.received_body("/elysite/api/legacy/skins/4242")
        assert b"tags%5B%5D=Original" in server_state.received_body(
            "/elysite/api/legacy/skins/4242"
        )
    else:
        assert server_state.request_count("/elysite/skins/s4242/edit") == 0


@pytest.mark.parametrize(
    "action", ["", "https://untrusted.example/steal", "/elysite/api/legacy/skins/4242"]
)
def test_ely_model_failure_keeps_the_current_worn_skin(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    action: str,
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau")
    server_state.add("/elysite/skins/s4242", b'alight.service.skin = {"is_slim":false};')
    server_state.add(
        "/elysite/skins/s4242/edit",
        (
            '<form id="formEditSkin" method="POST" action="'
            + action
            + '"><select name="is_slim"></select></form>'
        ).encode(),
    )
    server_state.add("/elysite/api/legacy/skins/4242", b'{"skin":{"is_slim":false}}')
    with pytest.raises(AccountError):
        launcher.save_skin_selection(account, skin_png(tmp_path), slim=True)
    assert server_state.request_count("/elysite/api/legacy/users/skin") == 0


def test_offline_save_uses_selected_model_even_if_library_entry_has_another_model(
    tmp_path: Path,
) -> None:
    from nostalgia.api import Launcher

    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    account = launcher.add_offline_account("ModelPreview")
    path = skin_png(tmp_path)
    launcher.import_skin(path, slim=False)
    assert launcher.save_skin_selection(account, path, slim=True).slim
    assert not launcher.save_skin_selection(account, path, slim=False).slim
