"""Quick play qua façade thật: máy chủ Mojang giả + java giả in lại argv → `--quickPlaySingleplayer`
chỉ xuất hiện khi `launch_instance` được đưa `world_folder`."""

from __future__ import annotations

from pathlib import Path

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from test_api import make_launcher

ECHO_JAVA = b'#!/bin/sh\necho "$@"\n'


def test_world_folder_becomes_the_quick_play_argument(
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
    game = launcher.launch_instance("thu", "Jun", world_folder="Nhà", on_output=lines.append)
    assert game.wait(timeout=30) == 0
    assert any("--quickPlaySingleplayer Nhà" in line for line in lines), lines

    lines.clear()
    game = launcher.launch_instance("thu", "Jun", on_output=lines.append)
    assert game.wait(timeout=30) == 0
    assert not any("quickPlay" in line for line in lines), (
        "không chọn thế giới thì không có tham số"
    )
