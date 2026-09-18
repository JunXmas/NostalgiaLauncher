"""Test cho importing/lunar.py — quét bản chơi Lunar Client từ cây thư mục giả.

Mọi test dựng qua nhánh Windows: ở đó thư mục gốc là `%USERPROFILE%\\.lunarclient`, tra được
bằng biến môi trường nên không phải gọi `expanduser()` — thứ mà conftest.py cấm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.importing.lunar import scan_lunar_client


@pytest.fixture
def lunar_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("nostalgia.importing.lunar.platform.system", lambda: "Windows")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path / ".lunarclient"


def make_instance(lunar_dir: Path, name: str) -> Path:
    """Tạo một bản chơi Lunar giả dưới `<lunar_dir>/profiles/<name>`."""
    inst_dir = lunar_dir / "profiles" / name
    inst_dir.mkdir(parents=True)
    return inst_dir


def test_no_lunar_dir(lunar_dir: Path) -> None:
    """Chưa cài Lunar → rỗng, không ném lỗi."""
    assert not lunar_dir.exists()
    assert scan_lunar_client() == []


def test_isolated_instance(lunar_dir: Path) -> None:
    """Bản chơi cô lập: saves/ nằm ngay tại gốc, bản game lấy từ versions/."""
    inst_dir = make_instance(lunar_dir, "Sky Factory")
    (inst_dir / "saves").mkdir()
    (inst_dir / "versions" / "1.20.1").mkdir(parents=True)

    found = scan_lunar_client()

    assert len(found) == 1
    assert found[0].launcher == "Lunar Client"
    assert found[0].instance_name == "Sky Factory"
    assert found[0].game_dir == inst_dir
    assert found[0].game_version == "1.20.1"
    assert found[0].loader_kind == "vanilla"


def test_nested_minecraft_dir(lunar_dir: Path) -> None:
    """Bản cũ bọc thêm lớp `.minecraft` → game_dir phải trỏ vào lớp đó."""
    inst_dir = make_instance(lunar_dir, "1.8.9")
    (inst_dir / ".minecraft" / "mods").mkdir(parents=True)

    found = scan_lunar_client()

    assert [one.game_dir for one in found] == [inst_dir / ".minecraft"]
    # Không có versions/ → rơi về tên bản chơi.
    assert found[0].game_version == "1.8.9"


def test_loader_from_version_dir(lunar_dir: Path) -> None:
    """Tên thư mục version cho biết loader — neoforge phải thắng forge."""
    inst_dir = make_instance(lunar_dir, "Modded")
    (inst_dir / "versions" / "neoforge-21.1.9-1.21.1").mkdir(parents=True)
    (inst_dir / "options.txt").write_text("fov:0.0\n")

    found = scan_lunar_client()

    assert found[0].loader_kind == "neoforge"
    # "21.1.9" là số hiệu NeoForge, không phải bản game — phải lấy "1.21.1".
    assert found[0].game_version == "1.21.1"


def test_fabric_version_dir(lunar_dir: Path) -> None:
    """Bản chơi Fabric 1.16+ của Lunar: loader suy từ tên thư mục version."""
    inst_dir = make_instance(lunar_dir, "Fabric pack")
    (inst_dir / "versions" / "fabric-loader-0.16.5-1.21").mkdir(parents=True)

    found = scan_lunar_client()

    assert found[0].loader_kind == "fabric"
    assert found[0].game_version == "1.21"


def test_unknown_version_stays_empty(lunar_dir: Path) -> None:
    """Tên bản chơi không chứa số bản → game_version rỗng, không đoán bừa."""
    make_instance(lunar_dir, "Profile74810572142")

    found = scan_lunar_client()

    assert found[0].game_version == ""


def test_skips_stray_files(lunar_dir: Path) -> None:
    """File lạc trong profiles/ bị bỏ qua."""
    (lunar_dir / "profiles").mkdir(parents=True)
    (lunar_dir / "profiles" / "profile_manager.json").write_text("{}")

    assert scan_lunar_client() == []


def test_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hệ điều hành lạ → rỗng, không dò đường dẫn nào."""
    monkeypatch.setattr("nostalgia.importing.lunar.platform.system", lambda: "Java")
    assert scan_lunar_client() == []


def test_found_in_find_all(lunar_dir: Path) -> None:
    """find_all() phải gom được bản chơi Lunar chứ không chỉ scan_lunar_client()."""
    from nostalgia.importing.launchers import find_all

    inst_dir = make_instance(lunar_dir, "Lunar 1.21")
    (inst_dir / "saves").mkdir()

    assert any(one.launcher == "Lunar Client" for one in find_all())
