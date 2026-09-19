"""SKlauncher dùng chung `launcher_profiles.json` với bản chính thức — quét phải phân biệt được."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.model import Found
from nostalgia.importing.sklauncher import load_sklauncher_profiles, scan_sklauncher


def write_profiles(base: Path, profiles: dict[str, object], *, mark: bool = True) -> Path:
    """Dựng một thư mục `.minecraft` giả của SKlauncher."""
    base.mkdir(parents=True, exist_ok=True)
    if mark:
        (base / "sklauncher").mkdir(exist_ok=True)
    (base / "launcher_profiles.json").write_text(
        json.dumps({"profiles": profiles}), encoding="utf-8"
    )
    return base


def only(found: list[Found], name: str) -> Found:
    matching = [candidate for candidate in found if candidate.instance_name == name]
    assert len(matching) == 1, f"mong đúng một profile tên {name}, thấy {found}"
    return matching[0]


class TestLoadProfiles:
    """Đọc `launcher_profiles.json`: tên, bản game, loader, thư mục game."""

    def test_reads_name_version_and_loader(self, tmp_path: Path) -> None:
        base = write_profiles(
            tmp_path,
            {
                "abc": {"name": "Fabric 1.20.1", "lastVersionId": "fabric-loader-0.15.0-1.20.1"},
                "def": {"name": "Vanilla 1.21", "lastVersionId": "1.21"},
                "ghi": {"name": "Forge", "lastVersionId": "1.20.1-forge-47.4.10"},
            },
        )

        found = load_sklauncher_profiles(base)

        assert {candidate.launcher for candidate in found} == {"SKlauncher"}
        fabric = only(found, "Fabric 1.20.1")
        assert (fabric.game_version, fabric.loader_kind) == ("1.20.1", "fabric")
        assert only(found, "Vanilla 1.21").game_version == "1.21"
        forge = only(found, "Forge")
        assert (forge.game_version, forge.loader_kind) == ("1.20.1", "forge")

    def test_game_dir_defaults_to_the_shared_folder(self, tmp_path: Path) -> None:
        """Không khai `gameDir` thì bản chơi nằm ngay trong `.minecraft` dùng chung."""
        base = write_profiles(tmp_path, {"abc": {"name": "A", "lastVersionId": "1.21"}})

        assert only(load_sklauncher_profiles(base), "A").game_dir == base

    def test_game_dir_override_is_honoured(self, tmp_path: Path) -> None:
        """Khai `gameDir` riêng thì mods/saves nằm ở đó, copy sai chỗ là mất dữ liệu người chơi."""
        elsewhere = tmp_path / "skprofiles" / "Fabric 1.20.1"
        base = write_profiles(
            tmp_path / ".minecraft",
            {"abc": {"name": "A", "lastVersionId": "1.21", "gameDir": str(elsewhere)}},
        )

        assert only(load_sklauncher_profiles(base), "A").game_dir == elsewhere

    @pytest.mark.parametrize("version_id", ["latest-release", "latest-snapshot", ""])
    def test_pointer_profiles_are_skipped(self, tmp_path: Path, version_id: str) -> None:
        """`latest-release` là con trỏ chứ không phải một bản — import theo nó sẽ hỏng."""
        base = write_profiles(tmp_path, {"abc": {"name": "A", "lastVersionId": version_id}})

        assert load_sklauncher_profiles(base) == []

    def test_profile_key_is_used_when_there_is_no_name(self, tmp_path: Path) -> None:
        base = write_profiles(tmp_path, {"abc": {"lastVersionId": "1.21"}})

        assert only(load_sklauncher_profiles(base), "abc").game_version == "1.21"

    def test_missing_file_gives_empty_list(self, tmp_path: Path) -> None:
        assert load_sklauncher_profiles(tmp_path / "nowhere") == []

    def test_broken_json_gives_empty_list(self, tmp_path: Path) -> None:
        """File hỏng thì bỏ qua, không được ném lỗi ra màn hình nhập."""
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "launcher_profiles.json").write_text("{ đây không phải JSON", encoding="utf-8")

        assert load_sklauncher_profiles(tmp_path) == []

    def test_profiles_of_the_wrong_shape_are_skipped(self, tmp_path: Path) -> None:
        """Một số bản ghi `profiles` rỗng thành list — không được vì thế mà chết cả lượt quét."""
        base = tmp_path
        base.mkdir(parents=True, exist_ok=True)
        (base / "launcher_profiles.json").write_text(json.dumps({"profiles": []}), encoding="utf-8")

        assert load_sklauncher_profiles(base) == []


class TestScanSklauncher:
    """Phân biệt SKlauncher với launcher chính thức bằng thư mục dấu `sklauncher/`."""

    def test_finds_profiles_when_the_marker_folder_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base = write_profiles(
            tmp_path / ".minecraft", {"abc": {"name": "A", "lastVersionId": "1.21"}}
        )
        monkeypatch.setattr("nostalgia.importing.sklauncher.platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "nostalgia.importing.model.platform.system",
            lambda: "Linux",
        )
        monkeypatch.setattr(
            "nostalgia.importing.model.Path.expanduser",
            lambda self: base if str(self) == "~/.minecraft" else self,
        )

        assert only(scan_sklauncher(), "A").game_dir == base

    def test_official_launcher_folder_is_not_claimed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Không có thư mục `sklauncher/` thì đó là launcher chính thức — `_scan_vanilla` lo."""
        base = write_profiles(
            tmp_path / ".minecraft", {"abc": {"name": "A", "lastVersionId": "1.21"}}, mark=False
        )
        monkeypatch.setattr("nostalgia.importing.sklauncher.platform.system", lambda: "Linux")
        monkeypatch.setattr("nostalgia.importing.model.platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "nostalgia.importing.model.Path.expanduser",
            lambda self: base if str(self) == "~/.minecraft" else self,
        )

        assert scan_sklauncher() == []

    def test_unsupported_platform_gives_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("nostalgia.importing.sklauncher.platform.system", lambda: "FreeBSD")
        monkeypatch.setattr("nostalgia.importing.model.platform.system", lambda: "FreeBSD")

        assert scan_sklauncher() == []
