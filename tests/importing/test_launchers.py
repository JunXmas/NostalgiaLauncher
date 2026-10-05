"""Test cho module importing/launchers.py -- quet instance tu launcher khac."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing import launchers
from nostalgia.importing.launchers import (
    Found,
    find_all,
)
from nostalgia.importing.launchers_extra import _scan_sklauncher, _scan_tlauncher


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


class TestModuleDocstring:
    """Dòng mô tả module không được nhắc bộ quét không tồn tại,
    và không được thiếu bộ quét có thật.
    """

    def test_lists_every_real_scanner(self) -> None:
        assert launchers.__doc__ is not None
        for name in (
            "PrismLauncher",
            "CurseForge",
            "ModrinthApp",
            "TLauncher",
            "SKlauncher",
            "Vanilla",
        ):
            assert name in launchers.__doc__


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


class TestScanTlauncher:
    """Quét TLauncher từ home giả -- luật §1.4: không được dùng expanduser()."""

    def test_found_via_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TlauncherProfiles.json trong .minecraft -> tìm ra đúng bản + loader."""
        home = tmp_path / "home"
        base = home / ".minecraft"
        base.mkdir(parents=True)
        (base / "TlauncherProfiles.json").write_text("{}", encoding="utf-8")
        (home / ".tlauncher").mkdir()
        cfg = "login.version.game=1.20.1-forge-47.4.10\n"
        (home / ".tlauncher/tlauncher-2.0.properties").write_text(cfg, encoding="utf-8")

        monkeypatch.setattr("nostalgia.importing.launchers_extra.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_tlauncher() == [
            Found("TLauncher", "TLauncher Minecraft", base, "1.20.1-forge-47.4.10", "forge")
        ]

    def test_empty_without_marker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Không có TlauncherProfiles.json -> rỗng (đó là bản chính chủ, không phải TLauncher)."""
        home = tmp_path / "home"
        (home / ".minecraft").mkdir(parents=True)

        monkeypatch.setattr("nostalgia.importing.launchers_extra.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_tlauncher() == []


class TestScanSklauncher:
    """Quét SKlauncher từ home giả -- luật §1.4: không được dùng expanduser()."""

    def test_found_via_marker_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Thư mục con sklauncher/ trong .minecraft -> tách nó khỏi bản chính chủ."""
        home = tmp_path / "home"
        base = home / ".minecraft"
        (base / "sklauncher").mkdir(parents=True)
        profiles = {"profiles": {"abc": {"name": "A", "lastVersionId": "1.21"}}}
        (base / "launcher_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")

        monkeypatch.setattr("nostalgia.importing.launchers_extra.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_sklauncher() == [Found("SKlauncher", "A", base, "1.21", "vanilla")]

    def test_empty_without_marker_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Không có thư mục sklauncher/ -> rỗng (đó là bản chính chủ)."""
        home = tmp_path / "home"
        base = home / ".minecraft"
        base.mkdir(parents=True)
        profiles = {"profiles": {"abc": {"name": "A", "lastVersionId": "1.21"}}}
        (base / "launcher_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")

        monkeypatch.setattr("nostalgia.importing.launchers_extra.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_sklauncher() == []

    def test_empty_when_version_is_pointer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """lastVersionId kiểu 'latest-release' là con trỏ, không phải bản chơi thật -> bỏ qua."""
        home = tmp_path / "home"
        base = home / ".minecraft"
        (base / "sklauncher").mkdir(parents=True)
        profiles = {"profiles": {"abc": {"name": "A", "lastVersionId": "latest-release"}}}
        (base / "launcher_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")

        monkeypatch.setattr("nostalgia.importing.launchers_extra.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(home))

        assert _scan_sklauncher() == []
