"""Existing player data survives a real pack upgrade, failed writes and cancellation."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from test_modpack_install import make_modpack_launcher

from fabric_fixture import LOADER_VERSION
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance, Launcher
from nostalgia.facade import preset_updates


def jar(mod_id: str, version_id: str = "1") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("fabric.mod.json"),
            json.dumps({"schemaVersion": 1, "id": mod_id, "version": version_id}),
        )
    return stream.getvalue()


def write_pack(path: Path, server: LocalHttpsServer, state: ServerState, version_id: str) -> None:
    contents = {"base": jar("base")}
    if version_id != "1.0.1":
        contents.update(jei=jar("jei"), mezz_config=jar("mezz_config"))
    entries = []
    for name, payload in contents.items():
        route = "/update/" + name + ".jar"
        state.add(route, payload)
        entries.append(
            {
                "path": "mods/" + name + ".jar",
                "downloads": [server.url(route)],
                "hashes": {"sha1": hashlib.sha1(payload).hexdigest()},
                "fileSize": len(payload),
            }
        )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "modrinth.index.json",
            json.dumps(
                {
                    "formatVersion": 1,
                    "versionId": version_id,
                    "name": "Forgotten Worlds",
                    "dependencies": {"minecraft": VERSION_ID, "fabric-loader": LOADER_VERSION},
                    "files": entries,
                }
            ),
        )
        archive.writestr("overrides/config/player.toml", "pack default")
        archive.writestr("overrides/config/new.toml", "new default")
        archive.writestr("overrides/options.txt", "pack controls")
        archive.writestr("overrides/servers.dat", "pack servers")
        archive.writestr(
            "overrides/README-Forgotten-Worlds.txt",
            "Forgotten Worlds — Optimized " + version_id + "\n",
        )


Upgrade = tuple[Launcher, Instance, str, ServerState]


@pytest.fixture
def upgrade(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> Upgrade:
    launcher, host = make_modpack_launcher(server, server_state, tmp_path, certificate_pair)
    old = tmp_path / "old.mrpack"
    new = tmp_path / "new.mrpack"
    write_pack(old, server, server_state, "1.0.1")
    instance = launcher.install_modpack_file(old, "industry", allowed_hosts=(host,))
    write_pack(new, server, server_state, "1.0.2")
    monkeypatch.setattr(preset_updates, "load_forgotten_worlds_pack", lambda: new)
    return launcher, instance, host, server_state
