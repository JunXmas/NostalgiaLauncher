"""Áp sửa tại chỗ trên bản chơi thật (máy chủ giả): nâng loader đổi đúng version_id, tắt jar."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from fabric_fixture import FABRIC_VERSION_ID
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from nostalgia.modcheck.local_fix import LocalFix
from nostalgia.storage.files import atomic_write_json
from test_api import make_launcher


def test_loader_upgrade_installs_the_newest_matching_loader_and_switches_the_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    server_state.add(
        f"/fabric/versions/loader/{VERSION_ID}",
        json.dumps(
            [
                {"loader": {"version": "0.20.1", "stable": True}},
                {"loader": {"version": "0.19.5", "stable": True}},
                {"loader": {"version": "0.16.9", "stable": True}},
            ]
        ).encode(),
    )
    server_state.add(
        f"/fabric/versions/loader/{VERSION_ID}/0.20.1/profile/json",
        json.dumps(
            {
                "id": f"fabric-loader-0.20.1-{VERSION_ID}",
                "inheritsFrom": VERSION_ID,
                "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "libraries": [],
            }
        ).encode(),
    )
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )
    launcher.install_version(VERSION_ID)
    atomic_write_json(
        launcher.paths.version_json(FABRIC_VERSION_ID),
        {"id": FABRIC_VERSION_ID, "inheritsFrom": VERSION_ID, "mainClass": "x"},
    )
    launcher.create_instance(Instance(instance_id="cu", version_id=FABRIC_VERSION_ID))
    (launcher.paths.instance_dir("cu") / "mods").mkdir(parents=True)
    (launcher.paths.instance_dir("cu") / "mods/hong.jar").write_bytes(b"x")

    note = launcher.apply_local_fix("cu", LocalFix("loader", ">=0.19.5", ""))
    assert "0.20.1" in note
    saved = next(i for i in launcher.list_instances() if i.instance_id == "cu")
    assert saved.version_id == f"fabric-loader-0.20.1-{VERSION_ID}"

    launcher.apply_local_fix("cu", LocalFix("disable", "hong.jar", ""))
    assert not (launcher.paths.instance_dir("cu") / "mods/hong.jar").exists()
    assert (launcher.paths.instance_dir("cu") / "mods/hong.jar.disabled").exists()
