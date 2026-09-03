"""DataPaths: mọi đường dẫn đến từ đối tượng được tiêm vào, không từ trạng thái toàn cục."""

from __future__ import annotations

from pathlib import Path

import pytest

from mccore.paths import CONFIG_DIR_ENV, DATA_DIR_ENV, DataPaths

LINUX_ENV = {"HOME": "/nha/jun"}


def test_for_root_puts_both_roots_under_one_directory(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    assert paths.data_dir == tmp_path / "data"
    assert paths.config_dir == tmp_path / "config"


def test_data_and_config_are_independent(tmp_path: Path) -> None:
    """Bài học đắt nhất của launcher tiền nhiệm: cấu hình không được nằm dưới thư mục dữ liệu.

    Đổi chỗ dữ liệu game sang thư mục tạm mà kéo theo cấu hình là mất sạch danh sách bản cài.
    """
    paths = DataPaths(data_dir=tmp_path / "kho", config_dir=tmp_path / "cau-hinh")
    assert paths.config_dir not in paths.data_dir.parents
    assert paths.data_dir not in paths.config_dir.parents


@pytest.mark.parametrize(
    ("platform_name", "env", "expected_data"),
    [
        ("linux", LINUX_ENV, Path("/nha/jun/.local/share/mc-core")),
        ("linux", {**LINUX_ENV, "XDG_DATA_HOME": "/xdg"}, Path("/xdg/mc-core")),
        ("osx", LINUX_ENV, Path("/nha/jun/Library/Application Support/mc-core/data")),
        (
            "windows",
            {"USERPROFILE": r"C:\Users\jun", "APPDATA": r"C:\Users\jun\AppData\Roaming"},
            Path(r"C:\Users\jun\AppData\Roaming") / "mc-core" / "data",
        ),
    ],
)
def test_default_location_follows_os_convention(
    platform_name: str, env: dict[str, str], expected_data: Path
) -> None:
    assert DataPaths.from_env(platform_name, env).data_dir == expected_data


def test_env_override_wins() -> None:
    env = {**LINUX_ENV, DATA_DIR_ENV: "/tuy/chon/data", CONFIG_DIR_ENV: "/tuy/chon/config"}
    paths = DataPaths.from_env("linux", env)
    assert paths.data_dir == Path("/tuy/chon/data")
    assert paths.config_dir == Path("/tuy/chon/config")


def test_from_env_reads_the_mapping_it_is_given_not_the_process() -> None:
    """Nhận `environ` làm đối số nên test không phải vá biến môi trường toàn cục."""
    paths = DataPaths.from_env("linux", {"HOME": "/khong/co/that"})
    assert paths.data_dir == Path("/khong/co/that/.local/share/mc-core")


def test_derived_paths(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    data = tmp_path / "data"
    assert paths.versions_dir == data / "versions"
    assert paths.libraries_dir == data / "libraries"
    assert paths.runtime_dir == data / "runtime"
    assert paths.asset_indexes_dir == data / "assets" / "indexes"
    assert paths.version_json("1.20.1") == data / "versions" / "1.20.1" / "1.20.1.json"
    assert paths.version_jar("1.20.1") == data / "versions" / "1.20.1" / "1.20.1.jar"
    assert paths.natives_dir("1.20.1") == data / "versions" / "1.20.1" / "natives"


def test_asset_object_uses_first_two_hash_characters(tmp_path: Path) -> None:
    """Luật thư mục hai ký tự của Mojang chỉ được viết ở đúng một chỗ."""
    paths = DataPaths.for_root(tmp_path)
    asset_hash = "abcdef1234567890abcdef1234567890abcdef12"
    assert paths.asset_object(asset_hash) == paths.asset_objects_dir / "ab" / asset_hash


def test_paths_are_frozen(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    with pytest.raises(AttributeError):
        paths.data_dir = tmp_path  # type: ignore[misc]
