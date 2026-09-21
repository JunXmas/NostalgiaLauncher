"""Test cho module importing/launchers.py — quét instance từ launcher khác."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing import launchers
from nostalgia.importing.launchers import (
    Found,
    _scan_modrinth_app,
    _scan_prism,
    _scan_vanilla,
    find_all,
)


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


# instance.cfg thật của Prism 9.x: có section [General], và [UI] chứa base64 có dấu '%'
# (RawConfigParser phải không nội suy '%', ConfigParser thường sẽ ném lỗi ở đây).
REAL_CFG = """[General]
name=DonutSMP Modpack

[UI]
mods_Page\\Columns="AAAA/wAAAAAAAAAB%AAAAZA=="
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


class TestScanModrinth:
    """Quét ModrinthApp từ filesystem giả.

    App-id Flatpak thật: `com.modrinth.ModrinthApp` (manifest flathub/com.modrinth.ModrinthApp).
    Đường native Linux xác nhận từ trang hỗ trợ Modrinth: `$XDG_DATA_HOME/ModrinthApp/`
    (mặc định `~/.local/share/ModrinthApp/`). Máy chủ dự án không cài ModrinthApp
    (`ls ~/.var/app/` chỉ ra `com.obsproject.Studio`, `org.prismlauncher.PrismLauncher`,
    `org.vinegarhq.Sober`) — chưa kiểm được trên một cài đặt Flatpak thật, chỉ tra từ manifest.
    """

    def test_flatpak_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bản Flatpak ở ~/.var/app/com.modrinth.ModrinthApp vẫn phải quét ra."""
        home = tmp_path / "home"
        profiles = home / ".var/app/com.modrinth.ModrinthApp/data/ModrinthApp/profiles"
        prof = profiles / "donutsmp"
        prof.mkdir(parents=True)
        (prof / "profile.json").write_text(
            json.dumps({"name": "DonutSMP", "game_version": "1.21", "loader": "forge"}),
            encoding="utf-8",
        )

        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        result = _scan_modrinth_app()
        assert len(result) == 1
        assert result[0].instance_name == "DonutSMP"
        assert result[0].game_version == "1.21"
        assert result[0].loader_kind == "forge"
        assert result[0].game_dir == profiles / "donutsmp"

    def test_no_modrinth_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Không có thư mục ModrinthApp → danh sách rỗng, không ném lỗi."""
        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(tmp_path / "trong-rong"))
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        assert _scan_modrinth_app() == []


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


class TestModuleDocstring:
    """Dòng mô tả module không được nhắc bộ quét không tồn tại."""

    def test_no_tlauncher_mention(self) -> None:
        assert launchers.__doc__ is not None
        assert "TLauncher" not in launchers.__doc__


class TestFindAll:
    """find_all() gom kết quả từ mọi scanner, bắt lỗi riêng từng scanner."""

    def test_returns_list(self) -> None:
        """find_all luôn trả list, không bao giờ ném lỗi."""
        assert isinstance(find_all(), list)
        # Trên CI có thể không có launcher nào, nhưng không được crash.

    def test_scanner_crash_logs_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Một scanner ném lỗi: nguyên launcher biến mất khỏi danh sách -> log warning."""

        def _boom() -> list[Found]:
            raise RuntimeError("scanner hỏng")

        monkeypatch.setattr("nostalgia.importing.launchers._scan_prism", _boom)
        with caplog.at_level("WARNING", logger="nostalgia.importing.launchers"):
            find_all()
        assert any(rec.levelname == "WARNING" for rec in caplog.records)

    def test_sorted_by_launcher_and_name(self) -> None:
        """Kết quả luôn sắp xếp theo launcher, rồi instance_name."""
        result = find_all()
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert (result[i].launcher, result[i].instance_name) <= (
                    result[i + 1].launcher,
                    result[i + 1].instance_name,
                )
