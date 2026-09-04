"""Asset: gộp trùng theo hash, và dựng cây theo tên cho đời cũ."""

from __future__ import annotations

from pathlib import Path

import pytest

from asset_fixtures import load_asset_index
from mccore.errors import Cancelled
from mccore.install.assets import (
    ASSET_OBJECT_BASE_URL,
    RESOURCES_DIRECTORY,
    build_name_tree,
    plan_asset_index_task,
    plan_asset_tasks,
)
from mccore.model.asset_index import AssetIndex, parse_asset_index
from mccore.model.download import RemoteFile
from mccore.operations.cancellation import CancelToken
from mccore.storage.paths import DataPaths
from mccore.version.meta import AssetIndexRef

MODERN = "5"
VIRTUAL = "legacy"
RESOURCES = "pre-1.6"


def index_for(asset_index_id: str) -> AssetIndex:
    return parse_asset_index(load_asset_index(asset_index_id))


def seed_objects(asset_index: AssetIndex, paths: DataPaths) -> None:
    """Đặt sẵn object trong kho, đúng kích thước mà chỉ mục công bố."""
    for asset_object in asset_index.unique_objects():
        target = paths.asset_object(asset_object.asset_hash)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x" * asset_object.size)


@pytest.mark.parametrize("asset_index_id", [MODERN, VIRTUAL, RESOURCES])
def test_every_real_index_parses(asset_index_id: str) -> None:
    asset_index = index_for(asset_index_id)
    assert asset_index.objects_by_name
    assert all(len(o.asset_hash) == 40 for o in asset_index.objects_by_name.values())


def test_duplicate_hashes_are_downloaded_once(tmp_path: Path) -> None:
    """Chỉ mục `legacy` thật của 1.6.4 có 1120 mục nhưng chỉ 596 hash — thừa 47% nếu không gộp.

    Quan trọng hơn tiết kiệm: hai luồng cùng ghi một đích là điều kiện đua thật sự.
    """
    asset_index = index_for(VIRTUAL)
    assert len(asset_index.unique_objects()) < len(asset_index.objects_by_name)

    tasks = plan_asset_tasks(asset_index, DataPaths.for_root(tmp_path))
    assert len(tasks) == len(asset_index.unique_objects())
    assert len({task.destination for task in tasks}) == len(tasks)


def test_object_path_and_url_use_the_first_two_hash_characters(tmp_path: Path) -> None:
    asset_index = index_for(MODERN)
    paths = DataPaths.for_root(tmp_path)
    for task in plan_asset_tasks(asset_index, paths)[:5]:
        asset_hash = task.sha1
        assert asset_hash is not None
        assert task.destination == paths.asset_objects_dir / asset_hash[:2] / asset_hash
        assert task.url == f"{ASSET_OBJECT_BASE_URL}/{asset_hash[:2]}/{asset_hash}"


def test_the_index_itself_lands_in_the_indexes_directory(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    reference = AssetIndexRef(
        asset_index_id="5", remote=RemoteFile(url="https://x/5.json", sha1="ab" * 20, size=9)
    )
    task = plan_asset_index_task(reference, paths)
    assert task.destination == paths.asset_indexes_dir / "5.json"


def test_a_modern_index_needs_no_name_tree(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    assert build_name_tree(index_for(MODERN), MODERN, paths, tmp_path / "game") is None


def test_virtual_assets_go_into_the_store(tmp_path: Path) -> None:
    """Đời 1.6: cây tên nằm trong kho nên nhiều bản cài dùng chung."""
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(VIRTUAL)
    seed_objects(asset_index, paths)
    game_dir = tmp_path / "game"

    report = build_name_tree(asset_index, VIRTUAL, paths, game_dir)
    assert report is not None
    assert report.tree_root == paths.virtual_assets_dir(VIRTUAL)
    assert report.copied == len(asset_index.objects_by_name)
    assert report.missing_objects == 0
    assert not game_dir.exists(), "không được đụng vào thư mục game"

    name, asset_object = next(iter(asset_index.objects_by_name.items()))
    assert (report.tree_root / name).stat().st_size == asset_object.size


def test_map_to_resources_writes_into_the_game_directory(tmp_path: Path) -> None:
    """Đời ≤1.5: game tự đọc từ `<game_dir>/resources`, không đọc từ kho.

    Trỏ nhầm là game chạy không âm thanh, không bản dịch, mà không báo lỗi gì.
    """
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(RESOURCES)
    seed_objects(asset_index, paths)
    game_dir = tmp_path / "game"

    report = build_name_tree(asset_index, RESOURCES, paths, game_dir)
    assert report is not None
    assert report.tree_root == game_dir / RESOURCES_DIRECTORY
    assert not paths.virtual_assets_dir(RESOURCES).exists()


def test_nested_names_create_their_directories(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(VIRTUAL)
    seed_objects(asset_index, paths)
    report = build_name_tree(asset_index, VIRTUAL, paths, tmp_path / "game")
    assert report is not None
    nested = [name for name in asset_index.objects_by_name if "/" in name]
    assert nested
    assert all((report.tree_root / name).is_file() for name in nested)


def test_building_twice_copies_nothing(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(VIRTUAL)
    seed_objects(asset_index, paths)
    build_name_tree(asset_index, VIRTUAL, paths, tmp_path / "game")
    second = build_name_tree(asset_index, VIRTUAL, paths, tmp_path / "game")
    assert second is not None
    assert second.copied == 0
    assert second.skipped_unchanged == len(asset_index.objects_by_name)


def test_missing_objects_are_counted_not_fatal(tmp_path: Path) -> None:
    """Thiếu object thì báo số lượng; tầng trên mới quyết định coi đó là lỗi hay không."""
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(VIRTUAL)
    report = build_name_tree(asset_index, VIRTUAL, paths, tmp_path / "game")
    assert report is not None
    assert report.copied == 0
    assert report.missing_objects == len(asset_index.objects_by_name)


def test_cancellation_is_honoured(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    asset_index = index_for(VIRTUAL)
    seed_objects(asset_index, paths)
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        build_name_tree(asset_index, VIRTUAL, paths, tmp_path / "game", cancel_token=cancel_token)


def test_entries_missing_hash_or_size_are_skipped() -> None:
    asset_index = parse_asset_index(
        {
            "objects": {
                "tot": {"hash": "a" * 40, "size": 3},
                "thieu-size": {"hash": "b" * 40},
                "thieu-hash": {"size": 3},
                "khong-phai-dict": "x",
            }
        }
    )
    assert list(asset_index.objects_by_name) == ["tot"]


def test_the_two_legacy_flags_are_never_both_set() -> None:
    """Đã kiểm trên chỉ mục thật của 1.5.2 và 1.6.4 — mỗi bên chỉ bật một cờ."""
    for asset_index_id in (VIRTUAL, RESOURCES):
        asset_index = index_for(asset_index_id)
        assert asset_index.is_virtual != asset_index.map_to_resources
