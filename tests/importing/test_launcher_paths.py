"""Test no duong dan cho importing/launchers.py -- moi scanner doc HOME gia dung cho.

Tach khoi test_launchers.py vi luat SS1.4 (khong expanduser()) can mot test rieng cho
moi launcher/he dieu hanh; gom chung khien file goc vuot tran 200 dong code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.launchers import (
    Found,
    _scan_curseforge,
    _scan_modrinth_app,
    _scan_prism,
    _scan_vanilla,
)


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


# instance.cfg thật của Prism 9.x: có section [General], và [UI] chứa base64 có dấu '%'
# (RawConfigParser phải không nội suy '%', ConfigParser thường sẽ ném lỗi ở đây).
REAL_CFG = """[General]
name=DonutSMP Modpack

[UI]
mods_Page\\Columns="AAAA/wAAAAAAAAAB%AAAAZA=="
"""


def _write_modrinth_profile(
    profiles: Path, dir_name: str, *, name: str = "", loader_kind: str = "fabric"
) -> Path:
    """Dựng một profile ModrinthApp giả (game_version cố định "1.21"), trả thư mục profile."""
    prof = profiles / dir_name
    prof.mkdir(parents=True)
    body = {"name": name or dir_name, "game_version": "1.21", "loader": loader_kind}
    (prof / "profile.json").write_text(json.dumps(body), encoding="utf-8")
    return prof



class TestScanModrinthApp:
    """Quét ModrinthApp từ filesystem giả."""

    def test_flatpak_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bản Flatpak (app-id com.modrinth.ModrinthApp) ở ~/.var/app vẫn phải quét ra."""
        home = tmp_path / "home"
        profiles = home / ".var/app/com.modrinth.ModrinthApp/data/ModrinthApp/profiles"
        _write_modrinth_profile(profiles, "RLCraft", name="RLCraft", loader_kind="forge")

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        assert _scan_modrinth_app() == [
            Found("ModrinthApp", "RLCraft", profiles / "RLCraft", "1.21", "forge")
        ]

    def test_xdg_and_flatpak_not_double_counted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """XDG_DATA_HOME trỏ đúng chỗ mặc định thì profile chỉ đếm một lần."""
        home = tmp_path / "home"
        profiles = home / ".local/share/ModrinthApp/profiles"
        _write_modrinth_profile(profiles, "solo", name="Solo")

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local/share"))

        assert [f.instance_name for f in _scan_modrinth_app()] == ["Solo"]



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



class TestScanCurseforge:
    """Quét CurseForge từ home giả — luật §1.4: không được dùng expanduser()."""

    def test_darwin_home_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """macOS: instance dưới ~/Documents/curseforge/minecraft/Instances phải quét ra,
        kể cả khi HOME không trỏ tới thư mục home thật của hệ điều hành (chứng minh code
        đọc biến môi trường HOME, không gọi Path.expanduser())."""
        home = tmp_path / "home-gia"
        instances = home / "Documents/curseforge/minecraft/Instances"
        inst_dir = instances / "RLCraft"
        inst_dir.mkdir(parents=True)
        body = {
            "name": "RLCraft",
            "gameVersion": "1.12.2",
            "baseModLoader": {"name": "forge-14.23"},
        }
        (inst_dir / "minecraftinstance.json").write_text(json.dumps(body), encoding="utf-8")

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Darwin")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_curseforge() == [
            Found("CurseForge", "RLCraft", inst_dir, "1.12.2", "forge")
        ]



class TestScanVanilla:
    """Quét Vanilla từ home giả — luật §1.4: không được dùng expanduser()."""

    def test_linux_home_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Linux: ~/.minecraft phải quét ra qua biến môi trường HOME, không qua
        Path.expanduser() (mà chỉ tra HOME thật của hệ điều hành, test không chặn nổi)."""
        home = tmp_path / "home-gia"
        base = home / ".minecraft"
        (base / "versions").mkdir(parents=True)

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        result = _scan_vanilla()
        assert len(result) == 1
        assert result[0].game_dir == base



@pytest.mark.allow_home
@pytest.mark.parametrize(
    ("profiles_body", "expected_version", "expect_warning"),
    [
        # Khoá đầu tiên trong dict ("cu") KHÔNG phải profile dùng gần nhất — thứ tự khoá
        # trong JSON/dict không có nghĩa, `for ... break` cũ lấy nhầm cái đầu.
        (
            json.dumps(
                {
                    "profiles": {
                        "cu": {"lastVersionId": "1.16.5", "lastUsed": "2020-01-01T00:00:00Z"},
                        "moi": {"lastVersionId": "1.21.1", "lastUsed": "2026-09-01T00:00:00Z"},
                    }
                }
            ),
            "1.21.1",
            False,
        ),
        (json.dumps({"profiles": {"x": {"lastVersionId": "1.21.1"}}}), "", False),
        # File hỏng hẳn -> mất version của cả launcher Vanilla, phải log warning.
        ("khong-phai-json", "", True),
    ],
)
def test_scan_vanilla_picks_newest_lastused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    profiles_body: str,
    expected_version: str,
    expect_warning: bool,
) -> None:
    """_scan_vanilla chọn game_version theo profile lastUsed mới nhất, không lấy bừa."""
    home = tmp_path / "home"
    base = home / ".minecraft"
    (base / "versions").mkdir(parents=True)
    (base / "launcher_profiles.json").write_text(profiles_body, encoding="utf-8")

    monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
    monkeypatch.setenv("HOME", str(home))

    with caplog.at_level("WARNING", logger="nostalgia.importing.launchers"):
        result = _scan_vanilla()
    assert len(result) == 1
    assert result[0].game_version == expected_version
    assert any(rec.levelname == "WARNING" for rec in caplog.records) == expect_warning

