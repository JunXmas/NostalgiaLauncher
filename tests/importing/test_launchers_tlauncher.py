"""Quét bản chơi TLauncher — MYLA-37.4.

TLauncher là launcher duy nhất giữ đường dẫn thư mục game ở NGOÀI thư mục game: trong
`~/.tlauncher/tlauncher-2.0.properties`. Đoán `.minecraft` là quét ra rỗng đúng với người
đã đổi thư mục — mà đổi thư mục là chuyện thường ở TLauncher vì nó chơi chung `.minecraft`
với bản chính chủ.

Mọi test ở đây đánh `allow_home` vì scanner tra `~` là đúng thiết kế của nó — `isolated_home`
đã trỏ `HOME` vào thư mục tạm nên không đụng dữ liệu thật.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.launchers import find_all

pytestmark = pytest.mark.allow_home


def _write_profiles(game_dir: Path) -> None:
    """Dấu nhận dạng TLauncher: `TlauncherProfiles.json` — chỉ chứa tài khoản, không có bản game."""
    game_dir.mkdir(parents=True, exist_ok=True)
    (game_dir / "TlauncherProfiles.json").write_text(
        json.dumps({"accounts": {}, "clientToken": "x", "selectedAccountUUID": ""}),
        encoding="utf-8",
    )


def _write_settings(home: Path, body: str) -> None:
    """`tlauncher-2.0.properties`: .properties phẳng, không có section header."""
    config_dir = home / ".tlauncher"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "tlauncher-2.0.properties").write_text(body, encoding="utf-8")


def test_finds_game_dir_moved_away_from_minecraft(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Người dùng đổi thư mục game thì vẫn phải quét ra — bản cũ đoán `.minecraft` nên rỗng."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    moved = isolated_home / "Games" / "tl-minecraft"
    _write_profiles(moved)
    _write_settings(isolated_home, f"minecraft.gamedir={moved}\nlogin.version.game=1.20.1\n")

    found = find_all()

    assert [f.launcher for f in found] == ["TLauncher"]
    assert found[0].game_dir == moved
    assert found[0].game_version == "1.20.1"


def test_reads_selected_version_and_loader_from_settings(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`login.version.game` là bản đang chọn — suy ra loader, không mặc định "vanilla"."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    minecraft = isolated_home / ".minecraft"
    _write_profiles(minecraft)
    (minecraft / "versions").mkdir()
    _write_settings(isolated_home, "login.version.game=1.20.1-forge-47.4.10\n")

    found = find_all()

    assert [(f.launcher, f.game_version, f.loader_kind) for f in found] == [
        ("TLauncher", "1.20.1-forge-47.4.10", "forge")
    ]


def test_default_dir_without_settings_file(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chưa có file cấu hình thì `.minecraft` vẫn là nhà mặc định — chỉ thiếu tên bản game."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    minecraft = isolated_home / ".minecraft"
    _write_profiles(minecraft)
    (minecraft / "versions").mkdir()
    (minecraft / "launcher_profiles.json").write_text(
        json.dumps({"profiles": {"a": {"lastVersionId": "1.19.4"}}}), encoding="utf-8"
    )

    found = find_all()

    assert [(f.launcher, f.game_version) for f in found] == [("TLauncher", "1.19.4")]


def test_not_listed_twice_as_vanilla(isolated_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chung `.minecraft` với bản chính chủ không được thành hai dòng cho một thư mục."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    minecraft = isolated_home / ".minecraft"
    _write_profiles(minecraft)
    (minecraft / "versions").mkdir()

    assert len(find_all()) == 1


def test_settings_alone_is_not_an_install(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Còn file cấu hình mà thư mục game đã xoá thì không được bịa ra một bản chơi."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    _write_settings(isolated_home, f"minecraft.gamedir={isolated_home / 'đã-xoá'}\n")

    assert find_all() == []


def test_broken_settings_file_does_not_raise(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """File cấu hình hỏng thì lùi về `.minecraft`, không ném lỗi lên giao diện."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setattr("nostalgia.importing.tlauncher.platform.system", lambda: "Linux")
    minecraft = isolated_home / ".minecraft"
    _write_profiles(minecraft)
    (minecraft / "versions").mkdir()
    _write_settings(isolated_home, "= dòng này không phải .properties\n\x00")

    assert [f.launcher for f in find_all()] == ["TLauncher"]
