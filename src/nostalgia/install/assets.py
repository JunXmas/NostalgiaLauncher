"""Lập kế hoạch tải asset, và dựng cây theo tên cho đời cũ.

Ba việc, tách rõ vì chúng chạy ở những lúc khác nhau:

1. Tải **chỉ mục** — cần trước, vì nó nói phải tải những gì.
2. Tải **object** vào kho `assets/objects/<hai ký tự>/<hash>`, đã gộp trùng theo hash.
3. Dựng **cây theo tên** cho đời ≤1.6, thứ mà đời mới không cần.

Về chỗ đặt cây tên: `virtual` (1.6) nằm trong kho nên nhiều bản cài dùng chung; còn
`map_to_resources` (≤1.5) nằm trong **thư mục game**, vì bản thân game đọc từ đó. Trỏ nhầm
hai chỗ này là game chạy không có âm thanh và không có bản dịch, mà không báo lỗi gì.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from nostalgia.model.asset_index import AssetIndex
from nostalgia.model.download import DownloadTask, RemoteFile
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import ensure_dir, resolve_within
from nostalgia.storage.paths import DataPaths
from nostalgia.version.meta import AssetIndexRef

# CDN riêng cho object asset — khác host với thư viện và với manifest.
ASSET_OBJECT_BASE_URL = "https://resources.download.minecraft.net"

# Thư mục mà game đời <=1.5 tự đọc, nằm trong thư mục game chứ không trong kho.
RESOURCES_DIRECTORY = "resources"


@dataclass(frozen=True, slots=True)
class NameTreeReport:
    """Đã chép ra bao nhiêu file theo tên, và bỏ qua bao nhiêu vì đã đúng."""

    tree_root: Path
    copied: int
    skipped_unchanged: int
    missing_objects: int


def plan_asset_index_task(reference: AssetIndexRef, paths: DataPaths) -> DownloadTask:
    """Chỉ mục lưu ở `assets/indexes/<id>.json` — đường dẫn do `DataPaths` quyết định."""
    return reference.remote.to_task(paths.asset_index_json(reference.asset_index_id))


def plan_asset_tasks(asset_index: AssetIndex, paths: DataPaths) -> list[DownloadTask]:
    """Mỗi hash đúng một việc tải.

    URL suy ra từ chính hash: `<hai ký tự đầu>/<hash>`. Chỉ mục không khai URL, nên đây là
    một trong hai chỗ ta phải tự dựng — chỗ kia là đường dẫn lưu, và cả hai dùng cùng quy
    tắc hai ký tự.
    """
    return [
        RemoteFile(
            url=f"{ASSET_OBJECT_BASE_URL}/{asset_object.asset_hash[:2]}/{asset_object.asset_hash}",
            sha1=asset_object.asset_hash,
            size=asset_object.size,
        ).to_task(paths.asset_object(asset_object.asset_hash))
        for asset_object in asset_index.unique_objects()
    ]


def build_name_tree(
    asset_index: AssetIndex,
    asset_index_id: str,
    paths: DataPaths,
    game_dir: Path,
    *,
    cancel_token: CancelToken | None = None,
) -> NameTreeReport | None:
    """Dựng cây asset theo tên cho đời cũ. Trả `None` nếu phiên bản không cần.

    Chép chứ không tạo liên kết cứng: liên kết cứng tiết kiệm chỗ nhưng khiến việc thay một
    object hỏng lan sang cả cây, và cây này chỉ vài megabyte (`legacy` của 1.6.4 có 596
    object duy nhất).
    """
    if not asset_index.needs_name_tree:
        return None

    tree_root = (
        resolve_within(game_dir, RESOURCES_DIRECTORY)
        if asset_index.map_to_resources
        else paths.virtual_assets_dir(asset_index_id)
    )
    ensure_dir(tree_root)

    copied = skipped = missing = 0
    for name, asset_object in asset_index.objects_by_name.items():
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        source = paths.asset_object(asset_object.asset_hash)
        if not source.is_file():
            missing += 1
            continue
        target = resolve_within(tree_root, name)
        if _already_copied(target, asset_object.size):
            skipped += 1
            continue
        ensure_dir(target.parent)
        shutil.copyfile(source, target)
        copied += 1

    return NameTreeReport(
        tree_root=tree_root, copied=copied, skipped_unchanged=skipped, missing_objects=missing
    )


def _already_copied(target: Path, size: int) -> bool:
    try:
        return target.stat().st_size == size
    except FileNotFoundError:
        return False
