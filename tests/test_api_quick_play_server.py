"""Quick play máy chủ qua façade thật: java giả in lại argv → `--quickPlayMultiplayer <host>`
chỉ xuất hiện khi `launch_instance` được đưa `server_address`."""

from __future__ import annotations

from pathlib import Path

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from test_api import make_launcher

ECHO_JAVA = b'#!/bin/sh\necho "$@"\n'


def test_server_address_becomes_the_multiplayer_argument(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair, java_body=ECHO_JAVA)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")

    lines: list[str] = []
    game = launcher.launch_instance(
        "thu", "Jun", server_address="play.example:25565", on_output=lines.append
    )
    assert game.wait(timeout=30) == 0
    assert any("--quickPlayMultiplayer play.example:25565" in line for line in lines), lines
    assert not any("quickPlaySingleplayer" in line for line in lines)
