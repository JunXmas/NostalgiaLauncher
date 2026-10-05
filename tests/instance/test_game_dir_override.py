"""Thư mục chơi riêng: bản chơi có thể đặt mods/saves ở ổ khác, kho đăng ký vẫn ở instances/.
Luật: đường dẫn tuyệt đối, không đè kho launcher, không hai bản chơi cùng một thư mục; gỡ bản
chơi trả về đúng thư mục riêng; CÀI ĐẶT "thư mục lưu bản chơi" áp cho bản mới không chọn riêng."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.api import Launcher
from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance
from nostalgia.instance.store import (
    check_game_dir_override,
    create_instance,
    game_dir_of,
    list_instances,
    load_instance,
    unregister_instance,
)
from nostalgia.settings.store import Settings, save_settings
from nostalgia.storage.paths import DataPaths


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def test_override_round_trips_and_moves_only_the_play_directory(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    other_disk = tmp_path / "o-D" / "Minecraft" / "sinh-ton"
    created = create_instance(
        paths,
        Instance(instance_id="sinh-ton", version_id="1.20.1", game_dir_override=str(other_disk)),
    )

    assert other_disk.is_dir(), "thư mục riêng được tạo sẵn để mod/saves ghi vào"
    assert paths.instance_json("sinh-ton").is_file(), "kho đăng ký vẫn ở instances/"
    loaded = load_instance(paths, "sinh-ton")
    assert loaded == created and game_dir_of(paths, loaded) == other_disk
    assert game_dir_of(
        paths, Instance(instance_id="mac-dinh", version_id="1.20.1")
    ) == paths.instance_dir("mac-dinh")
    assert unregister_instance(paths, "sinh-ton") == other_disk, "gỡ thì chỉ đúng thư mục riêng"
    assert list_instances(paths) == () and other_disk.is_dir()


def test_bad_directories_are_refused_with_a_reason(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    assert check_game_dir_override(paths, "   ") == ""
    with pytest.raises(InstanceError, match="tuyệt đối"):
        check_game_dir_override(paths, "the-gioi")
    for taken in (paths.data_dir, paths.instances_dir, paths.versions_dir, tmp_path):
        with pytest.raises(InstanceError, match="đè lên kho"):
            check_game_dir_override(paths, str(taken))
    assert check_game_dir_override(paths, str(tmp_path / "o-D" / "x")) == str(
        tmp_path / "o-D" / "x"
    )

    shared = tmp_path / "o-D" / "chung"
    create_instance(
        paths, Instance(instance_id="a", version_id="1.20.1", game_dir_override=str(shared))
    )
    with pytest.raises(InstanceError, match="đã là thư mục chơi"):
        create_instance(
            paths, Instance(instance_id="b", version_id="1.20.1", game_dir_override=str(shared))
        )


def test_default_root_from_settings_applies_to_new_instances(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    default_root = tmp_path / "o-D" / "Nostalgia"
    save_settings(tmp_path / "config", Settings(default_game_dir_root=str(default_root)))

    plain = launcher.create_instance(Instance(instance_id="vui-ve", version_id="1.20.1"))
    assert plain.game_dir_override == str(default_root / "vui-ve")
    assert (
        launcher.instance_game_dir(plain) == default_root / "vui-ve"
        and (default_root / "vui-ve").is_dir()
    )

    chosen = tmp_path / "o-E" / "rieng"
    explicit = launcher.create_instance(
        Instance(instance_id="rieng", version_id="1.20.1", game_dir_override=str(chosen))
    )
    assert launcher.instance_game_dir(explicit) == chosen, "chọn riêng thì thắng cài đặt"

    (default_root / "vui-ve" / "saves" / "Nhà").mkdir(parents=True)
    (default_root / "vui-ve" / "saves" / "Nhà" / "level.dat").write_bytes(b"\x00")
    assert launcher.describe_instance_stats("vui-ve").world_count == 1, (
        "thống kê đếm ở thư mục riêng"
    )
    with pytest.raises(InstanceError):
        launcher.check_game_dir(str(tmp_path / "data"))
