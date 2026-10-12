"""Gói server đi cùng launcher: nội dung client đúng bản và cài qua luồng modpack thật."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from test_modpack_install import make_modpack_launcher

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import MOD_BODY
from nostalgia.api import Launcher
from nostalgia.content.builtin_pack import load_forgotten_worlds_pack
from nostalgia.content.mrpack import apply_overrides, read_index
from nostalgia.errors import ContentError
from nostalgia.facade import presets
from nostalgia.instance.server_list import load_saved_servers


def test_shipped_pack_has_client_create_and_matching_server_mods(tmp_path: Path) -> None:
    pack_path = load_forgotten_worlds_pack()
    index = read_index(pack_path)
    assert (index.game_version, index.loader_kind, index.loader_version) == (
        "1.21.11",
        "fabric",
        "0.19.5",
    )
    paths = [modpack_file.relative_path for modpack_file in index.files]
    assert len(paths) == len(set(paths))
    assert "mods/create-fly-1.21.11-6.0.9-5.jar" in paths
    assert not any(path.endswith("-server.jar") or "Cardboard" in path for path in paths)
    assert sum("fabric-language-kotlin" in path for path in paths) == 1
    assert any("sodium-fabric" in path for path in paths)
    assert any("friendsandfoes" in path for path in paths)
    assert any("SereneSeasons" in path for path in paths)
    apply_overrides(pack_path, tmp_path)
    saved = load_saved_servers(tmp_path / "servers.dat")
    assert len(saved) == 1 and saved[0].address == "snow.pikamc.vn:25079"
    sift_path = next((tmp_path / "mods").glob("the_sift-*.jar"))
    with zipfile.ZipFile(sift_path) as archive:
        metadata = json.loads(archive.read("fabric.mod.json"))
        assert metadata["version"] == "1.1.2+port-1.21.11"
        assert "mielon/thesift/client/TheSiftClient.class" in archive.namelist()


def test_wrong_game_version_is_refused_before_installing(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    assert launcher.list_preset_game_versions("forgotten-worlds") == ("1.21.11",)
    with pytest.raises(ContentError, match=r"Forgotten Worlds.*1\.21\.1"):
        launcher.install_preset("forgotten-worlds", "server", "Server", game_version="1.21.1")
    assert launcher.list_instances() == ()


def test_builtin_preset_installs_downloads_and_overrides(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher, host = make_modpack_launcher(server, server_state, tmp_path, certificate_pair)
    pack_path = tmp_path / "forgotten-worlds.mrpack"
    # Dùng cùng resource contract, thay Minecraft/CDN bằng máy chủ HTTPS giả để kiểm offline.
    original = server_state.routes["/files/goi-vui.mrpack"].body
    with (
        zipfile.ZipFile(io.BytesIO(original)) as source,
        zipfile.ZipFile(pack_path, "w") as archive,
    ):
        for member in source.infolist():
            archive.writestr(member, source.read(member.filename))
        archive.writestr("overrides/mods/custom-content.jar", b"custom mod")
    monkeypatch.setattr(presets, "load_forgotten_worlds_pack", lambda: pack_path)
    monkeypatch.setattr(presets, "FORGOTTEN_GAME_VERSIONS", (VERSION_ID,))
    game_dir = tmp_path / "another-disk" / "server"
    instance = launcher.install_preset(
        "forgotten-worlds",
        "server",
        "Forgotten Worlds",
        game_version=VERSION_ID,
        allowed_hosts=(host,),
        game_dir_override=str(game_dir),
    )
    assert launcher.instance_game_dir(instance) == game_dir
    assert (game_dir / "mods" / "sodium.jar").read_bytes() == MOD_BODY
    assert (game_dir / "mods" / "custom-content.jar").read_bytes() == b"custom mod"
    assert (game_dir / "config" / "goi.toml").read_bytes() == b"cau hinh"
    assert launcher.describe_content_target("server").game_version == VERSION_ID
