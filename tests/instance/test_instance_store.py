"""Kho instance: mỗi bản chơi một thư mục riêng, kho tải thì dùng chung."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance, check_instance_id
from nostalgia.instance.store import (
    create_instance,
    list_instances,
    load_instance,
    save_instance,
    unregister_instance,
)
from nostalgia.storage.paths import DataPaths


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def test_a_created_instance_reads_back_identical(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    instance = Instance(
        instance_id="the-gioi-cua-jun",
        version_id="1.20.1",
        display_name="Thế giới của Jun",
        max_heap_megabytes=4096,
    )

    create_instance(paths, instance)

    assert load_instance(paths, "the-gioi-cua-jun") == instance


def test_each_instance_gets_its_own_play_directory_but_shares_the_store(
    tmp_path: Path,
) -> None:
    """Trộn chung thư mục chơi là bản mới ăn thế giới của bản cũ; chép kho là nhân 700 MB."""
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="vui-ve", version_id="1.20.1"))
    create_instance(paths, Instance(instance_id="nghiem-tuc", version_id="1.20.1"))

    assert paths.instance_dir("vui-ve") != paths.instance_dir("nghiem-tuc")
    assert paths.instance_dir("vui-ve").is_dir()
    assert paths.instance_dir("vui-ve").is_relative_to(paths.data_dir)
    assert not paths.instance_dir("vui-ve").is_relative_to(paths.versions_dir)
    assert not paths.instance_dir("vui-ve").is_relative_to(paths.assets_dir)


def test_creating_the_same_id_twice_is_refused(tmp_path: Path) -> None:
    """Ghi đè lặng lẽ ở đây là trỏ thư mục thế giới sang phiên bản khác vì một lệnh gõ nhầm."""
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="cua-toi", version_id="1.20.1"))

    with pytest.raises(InstanceError, match="đã có"):
        create_instance(paths, Instance(instance_id="cua-toi", version_id="1.8.9"))

    assert load_instance(paths, "cua-toi").version_id == "1.20.1"


@pytest.mark.parametrize(
    "instance_id",
    ["", "..", "../thoat", "a/b", ".an", "-tham-so", "a" * 65, "có dấu", "tên có cách", "a\nb"],
)
def test_a_dangerous_or_odd_id_is_refused(tmp_path: Path, instance_id: str) -> None:
    with pytest.raises(InstanceError, match="không hợp lệ"):
        check_instance_id(instance_id)
    with pytest.raises(InstanceError):
        create_instance(make_paths(tmp_path), Instance(instance_id=instance_id, version_id="1"))


@pytest.mark.parametrize("instance_id", ["a", "1", "a" * 64, "Ban.choi_1-2", "Z9"])
def test_a_reasonable_id_is_allowed(instance_id: str) -> None:
    assert check_instance_id(instance_id) == instance_id


def test_a_missing_instance_names_the_exact_path(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    with pytest.raises(InstanceError, match=r"instance\.json"):
        load_instance(paths, "khong-co")


def test_listing_is_sorted_and_skips_stray_directories(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    for instance_id in ("zulu", "alpha", "mike"):
        create_instance(paths, Instance(instance_id=instance_id, version_id="1.20.1"))
    (paths.instances_dir / "khong-phai-instance").mkdir()

    assert [instance.instance_id for instance in list_instances(paths)] == ["alpha", "mike", "zulu"]


def test_one_broken_instance_does_not_hide_the_others(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="tot", version_id="1.20.1"))
    create_instance(paths, Instance(instance_id="hong", version_id="1.20.1"))
    paths.instance_json("hong").write_text("{khong phai json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        instances = list_instances(paths)

    assert [instance.instance_id for instance in instances] == ["tot"]
    assert caplog.records, "bỏ qua thì phải nói"


def test_an_instance_without_a_version_is_not_usable(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="thieu", version_id="1.20.1"))
    paths.instance_json("thieu").write_text(json.dumps({"display_name": "x"}), encoding="utf-8")

    with pytest.raises(InstanceError, match="thiếu phiên bản"):
        load_instance(paths, "thieu")
    assert list_instances(paths) == ()


def test_the_directory_name_wins_over_the_field_inside(tmp_path: Path) -> None:
    """Đổi tên thư mục thì bản chơi đi theo; trường lệch không được làm `load` và `list`
    nói hai chuyện khác nhau."""
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="that", version_id="1.20.1"))
    paths.instance_json("that").write_text(
        json.dumps({"instance_id": "gia", "version_id": "1.20.1"}), encoding="utf-8"
    )

    assert load_instance(paths, "that").instance_id == "that"
    assert [instance.instance_id for instance in list_instances(paths)] == ["that"]


def test_removing_an_instance_keeps_the_worlds(tmp_path: Path) -> None:
    """Xoá thế giới vì một lệnh gõ nhầm là mất mát không lấy lại được."""
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="cua-toi", version_id="1.20.1"))
    world = paths.instance_dir("cua-toi") / "saves" / "The Gioi"
    world.mkdir(parents=True)
    (world / "level.dat").write_bytes(b"du lieu the gioi")

    left_behind = unregister_instance(paths, "cua-toi")

    assert list_instances(paths) == ()
    assert left_behind == paths.instance_dir("cua-toi")
    assert (world / "level.dat").read_bytes() == b"du lieu the gioi"


def test_removing_something_that_is_not_there_says_so(tmp_path: Path) -> None:
    with pytest.raises(InstanceError, match="chưa có"):
        unregister_instance(make_paths(tmp_path), "khong-co")


def test_saving_twice_updates_in_place(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    create_instance(paths, Instance(instance_id="cua-toi", version_id="1.20.1"))

    save_instance(paths, Instance(instance_id="cua-toi", version_id="1.8.9", window_width=800))

    reloaded = load_instance(paths, "cua-toi")
    assert reloaded.version_id == "1.8.9"
    assert reloaded.window_width == 800


def test_the_label_falls_back_to_the_id() -> None:
    assert Instance(instance_id="a", version_id="1").label == "a"
    assert Instance(instance_id="a", version_id="1", display_name="Tên đẹp").label == "Tên đẹp"
