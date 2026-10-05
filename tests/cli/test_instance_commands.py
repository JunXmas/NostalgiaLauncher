"""Lệnh `instance`: tạo, liệt kê, và gỡ mà không làm mất thế giới."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli_fixture import make_paths, roots
from nostalgia.cli.main import main
from nostalgia.instance.store import list_instances


def test_creating_an_instance_reports_where_the_worlds_will_live(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "instance", "create", "vui-ve", "--version", "1.20.1"]) == 0

    printed = capsys.readouterr().out
    assert "vui-ve" in printed
    assert str(make_paths(tmp_path).instance_dir("vui-ve")) in printed
    assert make_paths(tmp_path).instance_dir("vui-ve").is_dir()


def test_an_instance_remembers_its_own_settings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            *roots(tmp_path),
            "instance",
            "create",
            "nang",
            "--version",
            "1.20.1",
            "--name",
            "Bản nặng",
            "--max-memory",
            "8192",
            "--width",
            "1600",
            "--height",
            "900",
        ]
    )
    capsys.readouterr()

    instance = list_instances(make_paths(tmp_path))[0]

    assert instance.label == "Bản nặng"
    assert instance.max_heap_megabytes == 8192
    assert (instance.window_width, instance.window_height) == (1600, 900)


def test_a_bad_instance_id_is_refused_with_exit_code_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "instance", "create", "../thoat", "--version", "1.20.1"]) == 1
    assert "không hợp lệ" in capsys.readouterr().err


def test_creating_the_same_instance_twice_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([*roots(tmp_path), "instance", "create", "cua-toi", "--version", "1.20.1"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "instance", "create", "cua-toi", "--version", "1.8.9"]) == 1
    assert "đã có" in capsys.readouterr().err


def test_listing_says_what_to_do_when_there_is_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "instance", "list"]) == 0
    assert "instance create" in capsys.readouterr().out


def test_listing_shows_the_version_of_each_instance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([*roots(tmp_path), "instance", "create", "cu", "--version", "1.8.9"])
    main([*roots(tmp_path), "instance", "create", "moi", "--version", "1.20.1"])
    capsys.readouterr()

    main([*roots(tmp_path), "instance", "list"])

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert "1.8.9" in lines[0]
    assert "1.20.1" in lines[1]


def test_removing_keeps_the_worlds_and_says_where_they_are(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mặc định phải giữ. Xoá thế giới vì một lệnh gõ nhầm là mất mát không lấy lại được."""
    main([*roots(tmp_path), "instance", "create", "cua-toi", "--version", "1.20.1"])
    world = make_paths(tmp_path).instance_dir("cua-toi") / "saves" / "The Gioi"
    world.mkdir(parents=True)
    (world / "level.dat").write_bytes(b"du lieu")
    capsys.readouterr()

    assert main([*roots(tmp_path), "instance", "remove", "cua-toi"]) == 0

    printed = capsys.readouterr().out
    assert "vẫn còn" in printed
    assert (world / "level.dat").exists()
    assert list_instances(make_paths(tmp_path)) == ()


def test_deleting_the_worlds_needs_saying_so_out_loud(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([*roots(tmp_path), "instance", "create", "bo-di", "--version", "1.20.1"])
    play_dir = make_paths(tmp_path).instance_dir("bo-di")
    (play_dir / "saves").mkdir()
    capsys.readouterr()

    assert main([*roots(tmp_path), "instance", "remove", "bo-di", "--delete-worlds"]) == 0

    assert not play_dir.exists()
    assert "đã gỡ" in capsys.readouterr().out


def test_removing_an_unknown_instance_fails_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "instance", "remove", "khong-co"]) == 1
    assert "chưa có" in capsys.readouterr().err


def test_removing_one_instance_never_touches_the_shared_store(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Kho tải dùng chung: gỡ một bản chơi không được làm bản khác phải tải lại."""
    paths = make_paths(tmp_path)
    (paths.libraries_dir / "org").mkdir(parents=True)
    (paths.libraries_dir / "org" / "thu-vien.jar").write_bytes(b"jar")
    (paths.assets_dir).mkdir(parents=True, exist_ok=True)
    main([*roots(tmp_path), "instance", "create", "bo-di", "--version", "1.20.1"])
    capsys.readouterr()

    main([*roots(tmp_path), "instance", "remove", "bo-di", "--delete-worlds"])

    assert (paths.libraries_dir / "org" / "thu-vien.jar").exists()
    assert paths.assets_dir.is_dir()
