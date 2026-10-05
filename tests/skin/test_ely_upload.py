"""Đổi skin Ely.by THẬT qua facade: đăng nhập giữ vé phiên web, apply_library_skin upload
lên ely.by + mặc skin + đồng bộ cache — người chơi không phải mở trang web nữa."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, Account
from nostalgia.api import Launcher
from nostalgia.errors import AccountError
from test_api import make_launcher

SKIN_PNG = b"\x89PNG\r\n\x1a\nskin-moi"


def make_ely_web_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> Launcher:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    web = fake_ely.publish_web(server, server_state)
    auth = replace(
        fake_ely.publish(server, server_state),
        ely_web_account_root=web.account_root,
        ely_web_site_root=web.site_root,
    )
    endpoints = replace(
        launcher.endpoints,
        ely_skins=server.url("/ely/skins"),
        ely_capes=server.url("/ely/cloaks"),
        ely_textures=fake_ely.publish_textures(server, server_state, fake_ely.ELY_NAME),
    )
    return replace(launcher, auth_endpoints=auth, endpoints=endpoints)


def test_signing_in_also_keeps_the_web_refresh_token(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)

    account = launcher.add_ely_account("jun@example.com", "mat-khau")

    assert account.refresh_token == fake_ely.WEB_REFRESH_TOKEN
    # Vé nằm trên đĩa để lần đổi skin sau không hỏi lại mật khẩu; mật khẩu thì không.
    stored = launcher.paths.accounts_json.read_text()
    assert fake_ely.WEB_REFRESH_TOKEN in stored and "mat-khau" not in stored


def test_a_broken_web_login_still_signs_the_account_in(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Phiên web chỉ phục vụ đổi skin — nó chết thì vẫn phải vào game được."""
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add("/elyweb/api/authentication/login", b"loi", status=500)

    account = launcher.add_ely_account("jun@example.com", "mat-khau")

    assert account.account_kind == ELY
    assert account.refresh_token == ""


def test_apply_library_skin_uploads_wears_and_syncs_the_cache(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau")
    server_state.add(f"/ely/skins/{fake_ely.ELY_NAME}.png", SKIN_PNG)

    skin_file = tmp_path / "cool.png"
    skin_file.write_bytes(SKIN_PNG)
    skin_entry = launcher.import_skin(skin_file, name="cool")

    applied = launcher.apply_library_skin(account, skin_entry.entry_id)

    # Server giả đã NHẬN đúng file (upload) và đúng id (mặc) — đây là chỗ khác bản cũ:
    # không còn "chỉ đổi ảnh trong launcher".
    upload_body = server_state.received_body("/elysite/api/legacy/skins")
    assert SKIN_PNG in upload_body
    wear_body = server_state.received_body("/elysite/api/legacy/users/skin").decode()
    assert f"skinId={fake_ely.WEB_SKIN_ID}" in wear_body
    # Cache launcher tải lại từ skinsystem sau khi server đổi.
    assert applied.skin_path.read_bytes() == SKIN_PNG


def test_apply_without_a_web_session_asks_for_a_new_login(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Tài khoản đăng nhập từ bản cũ không có vé phiên web: nói thẳng phải đăng nhập lại,
    KHÔNG lặng lẽ rơi về "chỉ đổi ảnh trong launcher"."""
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = Account(
        player_name=fake_ely.ELY_NAME, player_uuid=fake_ely.ELY_UUID, account_kind=ELY
    )
    skin_file = tmp_path / "cool.png"
    skin_file.write_bytes(SKIN_PNG)
    skin_entry = launcher.import_skin(skin_file, name="cool")

    with pytest.raises(AccountError, match="đăng nhập lại"):
        launcher.apply_library_skin(account, skin_entry.entry_id)
    assert server_state.request_count("/elysite/api/legacy/skins") == 0


def test_an_expired_web_session_fails_loud_not_silent(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau")
    server_state.add(
        "/elyweb/api/authentication/refresh-token",
        json.dumps({"success": False, "errors": {"refresh_token": "err"}}).encode(),
    )
    skin_file = tmp_path / "cool.png"
    skin_file.write_bytes(SKIN_PNG)
    skin_entry = launcher.import_skin(skin_file, name="cool")

    with pytest.raises(AccountError, match="đăng nhập lại"):
        launcher.apply_library_skin(account, skin_entry.entry_id)


def test_refreshing_the_game_ticket_keeps_the_web_refresh_token(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """`refresh_ely_account` chạy mỗi lần chơi; nó mà đánh rơi vé phiên web thì tính năng
    đổi skin chỉ sống được tới lần chơi đầu tiên."""
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau")
    assert account.refresh_token == fake_ely.WEB_REFRESH_TOKEN

    refreshed = launcher._require_account(account.account_id, "", None)

    assert refreshed.access_token == fake_ely.REFRESHED_TOKEN
    assert refreshed.refresh_token == fake_ely.WEB_REFRESH_TOKEN
