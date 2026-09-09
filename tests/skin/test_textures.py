"""Skin: mặc định Steve/Alex đúng luật Java; premium tải từ sessionserver giả và cache; lỗi mạng
thì giữ cache cũ; Ely.by lấy theo tên."""

from __future__ import annotations

import base64
import json
from dataclasses import replace
from pathlib import Path

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, MICROSOFT, OFFLINE, Account
from nostalgia.model.json_value import JsonValue
from nostalgia.skin.defaults import default_skin, is_alex
from nostalgia.skin.textures import parse_session_profile
from test_api import make_launcher

SKIN_PNG = b"\x89PNG skin gia"
CAPE_PNG = b"\x89PNG cape gia"
PREMIUM_UUID = "069a79f4-44e9-4726-a5be-fca90e38aaf5"  # Notch: Steve theo luật hash


def test_default_skin_follows_the_java_uuid_rule() -> None:
    assert is_alex(PREMIUM_UUID) is False
    assert is_alex("61699b2e-d327-4a01-9f1e-0ea8c3f06bc6") is True  # Dinnerbone: Alex
    skin = default_skin(PREMIUM_UUID)
    assert skin.is_default and skin.skin_path.name == "steve.png" and skin.skin_path.is_file()
    assert default_skin("61699b2e-d327-4a01-9f1e-0ea8c3f06bc6").skin_path.name == "alex.png"


def textures_property(skin_url: str, cape_url: str, slim: bool) -> JsonValue:
    textures: dict[str, JsonValue] = {"SKIN": {"url": skin_url}}
    if slim:
        textures["SKIN"] = {"url": skin_url, "metadata": {"model": "slim"}}
    if cape_url:
        textures["CAPE"] = {"url": cape_url}
    payload = base64.b64encode(json.dumps({"textures": textures}).encode()).decode()
    return {
        "id": PREMIUM_UUID.replace("-", ""),
        "properties": [{"name": "textures", "value": payload}],
    }


def test_premium_skin_is_fetched_cached_and_kept_when_the_network_dies(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(launcher.endpoints, mojang_session_profile=server.url("/session")),
    )
    skin_url = server.url(server_state.add("/textures/skin.png", SKIN_PNG))
    cape_url = server.url(server_state.add("/textures/cape.png", CAPE_PNG))
    session_document = textures_property(skin_url, cape_url, slim=True)
    assert parse_session_profile(session_document) == (skin_url, cape_url, True)
    server_state.add(
        f"/session/{PREMIUM_UUID.replace('-', '')}", json.dumps(session_document).encode()
    )
    account = Account(player_name="Notch", player_uuid=PREMIUM_UUID, account_kind=MICROSOFT)

    assert launcher.describe_skin(account).is_default
    skin = launcher.refresh_skin(account)
    assert not skin.is_default and skin.slim is True
    assert skin.skin_path.read_bytes() == SKIN_PNG
    assert skin.cape_path is not None and skin.cape_path.read_bytes() == CAPE_PNG
    assert skin.skin_path.parent == launcher.paths.skins_dir

    server_state.routes[f"/session/{PREMIUM_UUID.replace('-', '')}"].status = 503
    again = launcher.refresh_skin(account)
    assert again.skin_path.read_bytes() == SKIN_PNG and again.slim is True

    offline = Account(player_name="Khach", player_uuid=PREMIUM_UUID, account_kind=OFFLINE)
    assert launcher.refresh_skin(offline) == skin  # cùng UUID → cùng cache, không chạm mạng


def test_ely_skin_is_served_by_name(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            ely_skins=server.url("/ely/skins"),
            ely_capes=server.url("/ely/cloaks"),
        ),
    )
    server_state.add("/ely/skins/JunBob.png", SKIN_PNG)
    account = Account(player_name="JunBob", player_uuid=PREMIUM_UUID, account_kind=ELY)
    skin = launcher.refresh_skin(account)
    assert skin.skin_path.name == "ely-junbob.png" and skin.skin_path.read_bytes() == SKIN_PNG
    assert skin.cape_path is None  # /ely/cloaks/JunBob.png trả 404 → không có cape
