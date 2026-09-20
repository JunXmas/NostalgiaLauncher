"""Test cho module importing/launchers.py — quét instance từ launcher khác."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.launchers import Found, _scan_prism, find_all


class TestFound:
    """Dataclass Found giữ đúng thông tin."""

    def test_frozen(self) -> None:
        found = Found(
            launcher="PrismLauncher",
            instance_name="Test",
            game_dir=Path("/tmp/test"),
            game_version="1.21",
            loader_kind="fabric",
        )
        with pytest.raises(AttributeError):
            found.launcher = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        found = Found(
            launcher="PrismLauncher",
            instance_name="My Instance",
            game_dir=Path("/home/user/.local/share/PrismLauncher/instances/test/.minecraft"),
            game_version="1.21",
            loader_kind="fabric",
        )
        assert found.launcher == "PrismLauncher"
        assert found.instance_name == "My Instance"
        assert found.game_version == "1.21"
        assert found.loader_kind == "fabric"


def _write_instance(
    instances: Path,
    dir_name: str,
    cfg_body: str,
    *,
    game_version: str = "1.21",
    loader_uid: str | None = "net.fabricmc.fabric-loader",
) -> Path:
    """Dựng một instance PrismLauncher giả, trả thư mục instance."""
    inst = instances / dir_name
    (inst / ".minecraft").mkdir(parents=True)
    (inst / "instance.cfg").write_text(cfg_body, encoding="utf-8")
    components: list[dict[str, str]] = [{"uid": "net.minecraft", "version": game_version}]
    if loader_uid is not None:
        components.append({"uid": loader_uid, "version": "0.19.2"})
    (inst / "mmc-pack.json").write_text(
        json.dumps({"components": components, "formatVersion": 1}), encoding="utf-8"
    )
    return inst


# instance.cfg thật của Prism 9.x: có section [General], và [UI] chứa base64 có dấu '%'.
REAL_CFG = """[General]
ConfigVersion=1.3
InstanceType=OneSix
JavaPath=/usr/bin/java
name=DonutSMP Modpack
totalTimePlayed=870

[UI]
mods_Page\\Columns="AAAA/wAAAAAAAAAB%AAAAZA=="
mods_Page\\ColumnsOverride=false
"""


class TestScanPrism:
    """Quét PrismLauncher từ filesystem giả."""

    def test_flatpak_path_and_general_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bản Flatpak ở ~/.var/app vẫn phải quét ra, và đọc đúng name trong [General]."""
        home = tmp_path / "home"
        instances = home / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances"
        _write_instance(instances, "DonutSMP Modpack", REAL_CFG)

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        result = _scan_prism()
        assert len(result) == 1
        assert result[0].instance_name == "DonutSMP Modpack"
        assert result[0].game_version == "1.21"
        assert result[0].loader_kind == "fabric"
        assert result[0].game_dir == instances / "DonutSMP Modpack/.minecraft"

    def test_legacy_cfg_without_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """instance.cfg bản cũ không có section header vẫn đọc được name."""
        home = tmp_path / "home"
        instances = home / ".local/share/PrismLauncher/instances"
        _write_instance(
            instances,
            "old-inst",
            "name=Forge cổ\nInstanceType=OneSix\n",
            game_version="1.12.2",
            loader_uid="net.minecraftforge",
        )

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        result = _scan_prism()
        assert [(f.instance_name, f.game_version, f.loader_kind) for f in result] == [
            ("Forge cổ", "1.12.2", "forge")
        ]

    def test_xdg_and_flatpak_not_double_counted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_DATA_HOME trỏ đúng chỗ mặc định thì instance chỉ đếm một lần."""
        home = tmp_path / "home"
        instances = home / ".local/share/PrismLauncher/instances"
        _write_instance(instances, "solo", "[General]\nname=Solo\n")

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local/share"))

        assert [f.instance_name for f in _scan_prism()] == ["Solo"]

    def test_no_prism_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Không có thư mục PrismLauncher → danh sách rỗng, không ném lỗi."""
        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(tmp_path / "trong-rong"))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        assert _scan_prism() == []


class TestFindAll:
    """find_all() gom kết quả từ mọi scanner, bắt lỗi riêng từng scanner."""

    def test_returns_list(self) -> None:
        """find_all luôn trả list, không bao giờ ném lỗi."""
        result = find_all()
        assert isinstance(result, list)
        # Trên CI có thể không có launcher nào, nhưng không được crash.

    def test_sorted_by_launcher_and_name(self) -> None:
        """Kết quả luôn sắp xếp theo launcher, rồi instance_name."""
        result = find_all()
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert (result[i].launcher, result[i].instance_name) <= (
                    result[i + 1].launcher,
                    result[i + 1].instance_name,
                )
