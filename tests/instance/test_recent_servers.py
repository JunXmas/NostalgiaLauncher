"""Server gần đây trên mọi bản chơi: bản chơi vừa sửa servers.dat (mtime) trước, trong một bản
giữ thứ tự trong game, cắt theo limit, bản không có servers.dat bị bỏ qua, icon thành URL data:."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from nbt_fixture import tiny_png, write_servers
from nostalgia.api import Instance, Launcher

NOW = 1_757_500_000.0
ICON = base64.b64encode(tiny_png()).decode()


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_servers_come_from_the_most_recently_edited_list_first(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    van = launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    rieng = launcher.create_instance(
        Instance(
            instance_id="rieng",
            version_id="1.21.4",
            display_name="Ổ riêng",
            game_dir_override=str(tmp_path / "o-khac" / "rieng"),
        )
    )
    launcher.create_instance(Instance(instance_id="trong", version_id="1.12.2"))
    old = write_servers(
        launcher.instance_game_dir(van),
        [("Cũ 1", "cu1.example", None, False), ("Cũ 2", "cu2.example", None, False)],
    )
    new = write_servers(
        launcher.instance_game_dir(rieng),
        [("Mới 1", "moi1.example", ICON, False), ("Mới 2", "moi2.example", None, False)],
    )
    os.utime(old, (NOW - 3600, NOW - 3600))
    os.utime(new, (NOW, NOW))

    servers = launcher.list_recent_servers(limit=10)
    assert [(s.server_name, s.instance_id) for s in servers] == [
        ("Mới 1", "rieng"),
        ("Mới 2", "rieng"),
        ("Cũ 1", "van"),
        ("Cũ 2", "van"),
    ]
    assert servers[0].instance_label == "Ổ riêng" and servers[0].address == "moi1.example"
    assert servers[0].icon_url.startswith("data:image/png;base64,") and servers[1].icon_url == ""
    assert [s.server_name for s in launcher.list_recent_servers()] == ["Mới 1", "Mới 2", "Cũ 1"]
    assert [s.server_name for s in launcher.list_recent_servers(limit=1)] == ["Mới 1"]


def test_no_servers_anywhere_gives_an_empty_tuple(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    assert launcher.list_recent_servers() == ()
