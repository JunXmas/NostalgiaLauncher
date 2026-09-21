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
