"""MYLA-37: quét launcher ra rỗng trên máy có sẵn bản chơi.

Hai nguyên nhân thật, mỗi cái một test tái hiện:

1. PrismLauncher cài bằng **Flatpak** ghi vào `~/.var/app/.../data`, không phải
   `~/.local/share` — máy của Jun có ba instance mà `find_all()` trả về rỗng.
2. TLauncher dùng chung `.minecraft` với bản chính chủ nên vẫn quét ra, nhưng bị gắn nhãn
   "Vanilla"; người dùng TLauncher nhìn vào tưởng launcher của mình không được nhận ra.

Mọi test ở đây đánh `allow_home` vì scanner tra `~` là đúng thiết kế của nó — đây là code
ĐỌC dữ liệu launcher khác, không phải code ghi dữ liệu của mình. `isolated_home` đã trỏ HOME
vào thư mục tạm trước khi test chạy, nên không đụng được vào dữ liệu thật.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.launchers import find_all

pytestmark = pytest.mark.allow_home


def _prism_instance(instances_dir: Path, name: str, game_version: str) -> None:
    """Dựng một instance PrismLauncher tối thiểu nhưng đúng thật: cfg + mmc-pack + game dir."""
    inst = instances_dir / name
    (inst / ".minecraft").mkdir(parents=True)
    (inst / "instance.cfg").write_text(f"name={name}\n", encoding="utf-8")
    (inst / "mmc-pack.json").write_text(
        json.dumps(
            {
                "components": [
                    {"uid": "net.minecraft", "version": game_version},
                    {"uid": "net.fabricmc.fabric-loader", "version": "0.16.0"},
                ]
            }
        ),
        encoding="utf-8",
    )


def test_prism_flatpak_instances_are_found(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MYLA-37: Prism bản Flatpak nằm trong hộp cát vẫn phải quét ra."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    flatpak_instances = (
        isolated_home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
    )
    flatpak_instances.mkdir(parents=True)
    _prism_instance(flatpak_instances, "RLCraft", "1.12.2")

    found = find_all()

    assert [(f.launcher, f.instance_name, f.game_version) for f in found] == [
        ("PrismLauncher", "RLCraft", "1.12.2")
    ]
    assert found[0].game_dir == flatpak_instances / "RLCraft" / ".minecraft"


def test_prism_native_and_flatpak_both_found(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cài cả hai kiểu thì thấy cả hai — bản Flatpak thêm vào chứ không thay thế."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    native = isolated_home / ".local/share/PrismLauncher/instances"
    native.mkdir(parents=True)
    _prism_instance(native, "Bản thường", "1.21")
    flatpak = (
        isolated_home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
    )
    flatpak.mkdir(parents=True)
    _prism_instance(flatpak, "Bản Flatpak", "1.20.1")

    names = {f.instance_name for f in find_all()}

    assert names == {"Bản thường", "Bản Flatpak"}


def test_modrinth_flatpak_profiles_are_found(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ModrinthApp cũng phát hành dạng Flatpak, cùng một lỗi hộp cát."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    profiles = isolated_home / ".var/app/com.modrinth.ModrinthApp/data/ModrinthApp/profiles"
    profiles.mkdir(parents=True)
    (profiles / "vui-ve").mkdir()
    (profiles / "vui-ve" / "profile.json").write_text(
        json.dumps({"name": "Vui vẻ", "game_version": "1.21.1", "loader": "quilt"}),
        encoding="utf-8",
    )

    found = find_all()

    assert [(f.launcher, f.instance_name, f.loader_kind) for f in found] == [
        ("ModrinthApp", "Vui vẻ", "quilt")
    ]


def test_tlauncher_is_labelled_tlauncher(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MYLA-37: `.minecraft` có `TlauncherProfiles.json` thì nhãn phải là TLauncher."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    minecraft = isolated_home / ".minecraft"
    (minecraft / "versions").mkdir(parents=True)
    (minecraft / "TlauncherProfiles.json").write_text(
        json.dumps({"accounts": {}, "selectedAccountUUID": ""}), encoding="utf-8"
    )

    found = find_all()

    assert [f.launcher for f in found] == ["TLauncher"]
    assert found[0].game_dir == minecraft


def test_plain_minecraft_still_labelled_vanilla(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Không có file của TLauncher thì vẫn là bản chính chủ — nhãn cũ không được đổi."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    (isolated_home / ".minecraft" / "versions").mkdir(parents=True)

    assert [f.launcher for f in find_all()] == ["Vanilla"]


def test_nothing_installed_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Máy sạch thì trả rỗng, không ném lỗi — `find_all` là biên an toàn của UI."""
    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")

    assert find_all() == []
