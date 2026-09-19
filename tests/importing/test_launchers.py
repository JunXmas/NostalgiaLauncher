"""Test cho module importing/launchers.py — quét instance từ launcher khác."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nostalgia.importing.launchers import Found, find_all


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


def _make_prism_instance(instances_dir: Path, name: str, game_version: str) -> None:
    """Dựng một instance PrismLauncher giả: instance.cfg + mmc-pack.json + .minecraft."""
    inst = instances_dir / name
    (inst / ".minecraft").mkdir(parents=True)
    # instance.cfg là INI không có dòng section — scanner phải tự chèn [DEFAULT].
    (inst / "instance.cfg").write_text(f"name={name}\n", encoding="utf-8")
    (inst / "mmc-pack.json").write_text(
        json.dumps(
            {
                "components": [
                    {"uid": "net.minecraft", "version": game_version},
                    {"uid": "net.fabricmc.fabric-loader", "version": "0.15.0"},
                ]
            }
        ),
        encoding="utf-8",
    )


class TestScanPrism:
    """Quét PrismLauncher từ filesystem giả, với HOME trỏ vào tmp_path."""

    @pytest.fixture(autouse=True)
    def _fake_linux_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Linux")
        monkeypatch.setenv("HOME", str(tmp_path))

    def test_finds_instance_installed_as_system_package(self, tmp_path: Path) -> None:
        """Bản cài bằng gói hệ thống: `~/.local/share/PrismLauncher/instances`."""
        _make_prism_instance(tmp_path / ".local/share/PrismLauncher/instances", "Vanilla+", "1.21")

        found = [f for f in find_all() if f.launcher == "PrismLauncher"]

        assert [(f.instance_name, f.game_version, f.loader_kind) for f in found] == [
            ("Vanilla+", "1.21", "fabric")
        ]

    def test_finds_instance_installed_as_flatpak(self, tmp_path: Path) -> None:
        """Bản cài Flatpak nằm trong hộp cát `~/.var/app/<app-id>/data`.

        Đây là lỗi thật gặp trên máy chủ dự án: PrismLauncher cài qua Flatpak (cách phổ biến
        nhất trên Linux) thì cả ba bản chơi đều vô hình, hộp thoại nhập báo "không tìm thấy
        launcher nào trên máy" dù launcher đang có instance.
        """
        flatpak_data = tmp_path / ".var/app/org.prismlauncher.PrismLauncher/data"
        _make_prism_instance(flatpak_data / "PrismLauncher/instances", "RLCraft", "1.12.2")

        found = [f for f in find_all() if f.launcher == "PrismLauncher"]

        assert [f.instance_name for f in found] == ["RLCraft"]
        assert found[0].game_dir == flatpak_data / "PrismLauncher/instances/RLCraft/.minecraft"

    def test_finds_instances_from_both_install_kinds_at_once(self, tmp_path: Path) -> None:
        """Cài cả hai kiểu thì gom cả hai, không phải chọn một."""
        _make_prism_instance(tmp_path / ".local/share/PrismLauncher/instances", "Gói hệ", "1.21")
        _make_prism_instance(
            tmp_path / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances",
            "Flatpak",
            "1.20.1",
        )

        names = {f.instance_name for f in find_all() if f.launcher == "PrismLauncher"}

        assert names == {"Gói hệ", "Flatpak"}

    def test_no_prism_dir(self) -> None:
        """Không có thư mục PrismLauncher nào → không có kết quả PrismLauncher, không nổ."""
        assert [f for f in find_all() if f.launcher == "PrismLauncher"] == []


class TestScanOnMacos:
    """macOS: đường dẫn phải ghép ra thư mục thật, không dính dấu `~` giữa đường.

    Vì sao đáng có: chưa test nào đặt `platform.system()` thành "Darwin", nên một lần ghép
    `_home() / "~/Library/..."` — ra `/Users/x/~/Library/...` — vẫn xanh hết bảng. Đúng kiểu
    mất mát âm thầm mà lỗi Flatpak đã dạy: scanner trả rỗng, người dùng thấy "không tìm thấy
    launcher nào", không ai biết vì sao.
    """

    @pytest.fixture(autouse=True)
    def _fake_macos_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("nostalgia.importing.launchers.platform.system", lambda: "Darwin")
        monkeypatch.setenv("HOME", str(tmp_path))

    def test_finds_prism_instance(self, tmp_path: Path) -> None:
        support = tmp_path / "Library/Application Support"
        _make_prism_instance(support / "PrismLauncher/instances", "RLCraft", "1.12.2")

        found = [f for f in find_all() if f.launcher == "PrismLauncher"]

        assert [f.instance_name for f in found] == ["RLCraft"]
        assert found[0].game_dir == support / "PrismLauncher/instances/RLCraft/.minecraft"

    def test_finds_modrinth_profile(self, tmp_path: Path) -> None:
        inst_dir = tmp_path / "Library/Application Support/ModrinthApp/profiles/Cobblemon"
        inst_dir.mkdir(parents=True)
        (inst_dir / "profile.json").write_text(
            json.dumps({"name": "Cobblemon", "game_version": "1.20.1", "loader": "fabric"}),
            encoding="utf-8",
        )

        found = [f for f in find_all() if f.launcher == "ModrinthApp"]

        assert [(f.instance_name, f.game_version, f.loader_kind) for f in found] == [
            ("Cobblemon", "1.20.1", "fabric")
        ]


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
