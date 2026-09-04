"""Lập kế hoạch tải client.jar — chỗ dễ trỏ nhầm thư mục nhất."""

from __future__ import annotations

from pathlib import Path

from nostalgia.install.client import plan_client_task
from nostalgia.storage.paths import DataPaths
from nostalgia.version.inherit import resolve_inheritance
from nostalgia.version.meta import parse_version_meta
from version_fixtures import load_fixture

FABRIC_ID = "fabric-loader-0.19.3-1.21.4"


def test_vanilla_jar_lands_in_its_own_directory(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    version_meta = parse_version_meta(load_fixture("1.20.1"))
    task = plan_client_task(version_meta, paths)
    assert task is not None
    assert task.destination == paths.version_jar("1.20.1")
    assert task.sha1 and task.size


def test_a_loader_version_uses_the_parent_jar(tmp_path: Path) -> None:
    """Bản Fabric không có jar riêng. Trỏ theo `version_id` là lỗi "không tìm thấy
    client.jar" rất khó truy: thư mục của bản Fabric vẫn tồn tại, chỉ thiếu đúng một file."""
    paths = DataPaths.for_root(tmp_path)
    version_meta = parse_version_meta(resolve_inheritance(FABRIC_ID, load_fixture))
    task = plan_client_task(version_meta, paths)
    assert task is not None
    assert task.destination == paths.version_jar("1.21.4")
    assert task.destination != paths.version_jar(FABRIC_ID)


def test_a_version_without_a_client_download_plans_nothing(tmp_path: Path) -> None:
    version_meta = parse_version_meta({"id": "trong", "mainClass": "x"})
    assert plan_client_task(version_meta, DataPaths.for_root(tmp_path)) is None
