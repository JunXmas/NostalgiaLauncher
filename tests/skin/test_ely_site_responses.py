"""Phản hồi frontend Ely.by: URL skin, form PUT và xác nhận model trước khi mặc."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from test_ely_upload import SKIN_PNG, make_ely_web_launcher

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import AccountError
from nostalgia.net.http import HttpClient, HttpResponse


@pytest.mark.parametrize(
    "reply",
    [
        {"error": "success_upload_skin", "url": "/elysite/skins/s4242/edit"},
        {"error": "success_upload_skin", "url": "skins/s4242"},
        {"extra": {"skin": {"id": 4242}}},
    ],
)
def test_upload_response_from_site_can_be_worn_without_a_top_level_skin_id(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    reply: dict[str, object],
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "test-password")
    server_state.add("/elysite/api/legacy/skins", json.dumps(reply).encode())
    server_state.add(f"/ely/skins/{fake_ely.ELY_NAME}.png", SKIN_PNG)
    path = tmp_path / "skin.png"
    path.write_bytes(SKIN_PNG)
    launcher.upload_skin_to_ely(account, path)
    assert b"skinId=4242" in server_state.received_body("/elysite/api/legacy/users/skin")


@pytest.mark.parametrize(
    "location",
    [
        "https://untrusted.example/elysite/skins/s4242",
        "http://untrusted.example/skins/s4242",
        "/elysite/skins/s0",
        "/elysite/skins/s4242/../../admin",
        "/elysite/authorization/login",
    ],
)
def test_upload_never_uses_an_unexpected_redirect_as_a_skin(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    location: str,
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "test-password")
    server_state.add("/elysite/api/legacy/skins", json.dumps({"url": location}).encode())
    path = tmp_path / "skin.png"
    path.write_bytes(SKIN_PNG)
    with pytest.raises(AccountError, match="không trả id"):
        launcher.upload_skin_to_ely(account, path)
    assert server_state.request_count("/elysite/api/legacy/users/skin") == 0


@pytest.mark.parametrize("confirmed", [True, False])
def test_put_form_with_redirect_response_is_confirmed_before_wearing(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    confirmed: bool,
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "test-password")
    page = "/elysite/skins/s4242"
    server_state.add(page, b'alight.service.skin = {"is_slim":false};')
    server_state.add(
        page + "/edit",
        b'<form id="formEditSkin" method="POST" data-method="PUT" '
        b'action="/elysite/api/legacy/skins/4242"><input type="hidden" name="csrf" value="proof">'
        b'<select name="is_slim"></select></form>',
    )
    server_state.add(
        "/elysite/api/legacy/skins/4242",
        b'{"error":"success_skin_edit","url":"/elysite/skins/s4242"}',
    )
    server_state.add(f"/ely/skins/{fake_ely.ELY_NAME}.png", SKIN_PNG)
    path = tmp_path / "skin.png"
    path.write_bytes(SKIN_PNG)
    original = HttpClient.send
    edits = []
    reads = []

    def send(self: HttpClient, method: str, url: str, **kwargs: Any) -> HttpResponse:
        response = original(self, method, url, **kwargs)
        if method == "GET" and urlsplit(url).path == page:
            reads.append(url)
        if urlsplit(url).path == "/elysite/api/legacy/skins/4242":
            edits.append(method)
            if confirmed:
                server_state.add(page, b'alight.service.skin = {"is_slim":true};')
        return response

    monkeypatch.setattr(HttpClient, "send", send)
    if confirmed:
        launcher.upload_skin_to_ely(account, path, slim=True)
        assert server_state.request_count("/elysite/api/legacy/users/skin") == 1
    else:
        with pytest.raises(AccountError, match="chưa xác nhận dáng tay"):
            launcher.upload_skin_to_ely(account, path, slim=True)
        assert server_state.request_count("/elysite/api/legacy/users/skin") == 0
    assert edits == ["PUT"]
    assert b"csrf=proof" in server_state.received_body("/elysite/api/legacy/skins/4242")
    assert len(reads) == 2
