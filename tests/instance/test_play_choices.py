"""`describe_play_choices` qua façade thật: thế giới + server của ĐÚNG bản chơi (kể cả thư mục
riêng), server sai dạng địa chỉ bị bỏ, mốc sửa servers.dat, và dò quick play từ version JSON
(chưa cài phiên bản → không vào thẳng được, không ném)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from nbt_fixture import write_servers, write_world
from nostalgia.api import Instance, Launcher
from version_fixtures import load_fixture

NOW = 1_757_500_000.0


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def install_json(launcher: Launcher, version_id: str) -> None:
    path = launcher.paths.version_json(version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(load_fixture(version_id)), encoding="utf-8")


def test_choices_belong_to_the_one_instance(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    rieng = launcher.create_instance(
        Instance(
            instance_id="rieng",
            version_id="1.21.4",
            game_dir_override=str(tmp_path / "o-khac" / "rieng"),
        )
    )
    khac = launcher.create_instance(Instance(instance_id="khac", version_id="1.21.4"))
    install_json(launcher, "1.21.4")
    game_dir = launcher.instance_game_dir(rieng)
    write_world(game_dir, "Nha", "Nhà", int(NOW * 1000))
    write_world(launcher.instance_game_dir(khac), "Lac", "Lạc", int(NOW * 1000))
    servers_path = write_servers(
        game_dir,
        [
            ("Hypixel", "mc.hypixel.net", None, False),
            ("Cờ lậu", "--demo", None, False),
            ("Cổng sai", "a.example:99999", None, False),
            ("IPv6", "[::1]:25566", None, False),
        ],
    )
    os.utime(servers_path, (NOW - 60, NOW - 60))

    choices = launcher.describe_play_choices("rieng", now=NOW)
    assert [w.world_folder for w in choices.worlds] == ["Nha"]
    assert [s.address for s in choices.servers] == ["mc.hypixel.net", "[::1]:25566"]
    assert choices.servers_changed_at == int(NOW - 60)
    assert (choices.quick_play.worlds, choices.quick_play.servers) == (True, True)


def test_nothing_on_disk_and_no_version_json_is_not_an_error(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="moi", version_id="1.21.4"))
    choices = launcher.describe_play_choices("moi", now=NOW)
    assert (choices.worlds, choices.servers, choices.servers_changed_at) == ((), (), 0)
    assert (choices.quick_play.worlds, choices.quick_play.servers) == (False, False)


def test_old_versions_reach_servers_but_not_worlds(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="cu", version_id="1.12.2"))
    install_json(launcher, "1.12.2")
    quick_play = launcher.describe_play_choices("cu", now=NOW).quick_play
    assert (quick_play.worlds, quick_play.servers) == (False, True)
