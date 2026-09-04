"""Lập kế hoạch tải thư viện: chỉ sinh danh sách việc, không tải — nên test được offline."""

from __future__ import annotations

from pathlib import Path

from mccore.install.library import plan_library_tasks, plan_native_extractions
from mccore.model.download import DownloadTask
from mccore.model.json_value import JsonValue
from mccore.storage.paths import DataPaths
from mccore.system.platform_info import Platform
from mccore.version.meta import parse_version_meta
from version_fixtures import load_fixture

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")
WINDOWS = Platform(os_name="windows", os_arch="x64", os_version="10.0.22631")
MACOS = Platform(os_name="osx", os_arch="arm64", os_version="23.5.0")


def plan_for(version_id: str, platform: Platform, tmp_path: Path) -> list[DownloadTask]:
    version_meta = parse_version_meta(load_fixture(version_id))
    return plan_library_tasks(version_meta, platform, DataPaths.for_root(tmp_path))


def test_every_task_lands_under_the_libraries_directory(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    for task in plan_for("1.20.1", LINUX, tmp_path):
        assert task.destination.is_relative_to(paths.libraries_dir)
        assert task.url.startswith("https://")
        assert task.sha1 and task.size


def test_the_plan_differs_between_operating_systems(tmp_path: Path) -> None:
    linux = {task.destination.name for task in plan_for("1.20.1", LINUX, tmp_path)}
    windows = {task.destination.name for task in plan_for("1.20.1", WINDOWS, tmp_path)}
    assert linux != windows
    assert any("natives-linux" in name for name in linux)
    assert not any("natives-windows" in name for name in linux)


def test_no_destination_appears_twice(tmp_path: Path) -> None:
    """Hai luồng cùng ghi một đích là điều kiện đua thật sự, không chỉ là lãng phí."""
    for version_id in ("1.8.9", "1.12.2", "1.20.1", "1.21.4"):
        destinations = [task.destination for task in plan_for(version_id, LINUX, tmp_path)]
        assert len(destinations) == len(set(destinations)), version_id


def test_legacy_natives_pick_the_classifier_for_this_operating_system(tmp_path: Path) -> None:
    """Đời ≤1.18: chọn từ `downloads.classifiers` theo bảng `natives`."""
    linux = {task.destination.name for task in plan_for("1.8.9", LINUX, tmp_path)}
    macos = {task.destination.name for task in plan_for("1.8.9", MACOS, tmp_path)}
    assert any("natives-linux" in name for name in linux)
    assert not any("natives-linux" in name for name in macos)


def test_natives_extraction_list_is_a_subset_of_the_download_plan(tmp_path: Path) -> None:
    """Không được yêu cầu giải nén một file mà kế hoạch không tải về."""
    paths = DataPaths.for_root(tmp_path)
    for version_id in ("1.8.9", "1.20.1"):
        version_meta = parse_version_meta(load_fixture(version_id))
        downloads = {task.destination for task in plan_library_tasks(version_meta, LINUX, paths)}
        native_destinations = {
            task.destination for task in plan_native_extractions(version_meta, LINUX, paths)
        }
        assert native_destinations, version_id
        assert native_destinations <= downloads, version_id


def test_only_native_libraries_are_extracted(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    version_meta = parse_version_meta(load_fixture("1.20.1"))
    for task in plan_native_extractions(version_meta, LINUX, paths):
        assert "natives" in task.destination.name


def test_a_version_with_no_libraries_plans_nothing(tmp_path: Path) -> None:
    version_meta = parse_version_meta({"id": "trong", "mainClass": "x"})
    assert plan_library_tasks(version_meta, LINUX, DataPaths.for_root(tmp_path)) == []


def test_two_libraries_pointing_at_the_same_file_are_downloaded_once(tmp_path: Path) -> None:
    """Hai mục khác toạ độ vẫn có thể trỏ cùng một file đích.

    Fixture thật không có ca này nên phải dựng thẳng — đã kiểm bằng đột biến: bỏ hẳn phần
    gộp trùng đích mà không test nào rớt. Hai luồng cùng ghi một đích là điều kiện đua.
    """
    shared: dict[str, JsonValue] = {
        "path": "a/b/c-1.0.jar",
        "url": "https://x/c-1.0.jar",
        "sha1": "ab" * 20,
        "size": 10,
    }
    version_meta = parse_version_meta(
        {
            "id": "x",
            "mainClass": "y",
            "libraries": [
                {"name": "a.b:c:1.0", "downloads": {"artifact": dict(shared)}},
                {"name": "a.b:c:2.0", "downloads": {"artifact": dict(shared)}},
            ],
        }
    )
    tasks = plan_library_tasks(version_meta, LINUX, DataPaths.for_root(tmp_path))
    assert len(tasks) == 1
