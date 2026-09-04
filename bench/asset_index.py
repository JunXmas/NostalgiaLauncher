"""Đọc chỉ mục asset của Minecraft — phần dùng chung của ba script đo.

Cả ba script đều cần đúng một thứ: danh sách hash duy nhất kèm kích thước, lấy từ một file
chỉ mục thật trên đĩa. Trước đây mỗi script tự parse lấy, tự dựng bảng dedupe, tự hard-code
đường dẫn — ba bản sao của cùng một đoạn, và hai cách gọi khác nhau cho cùng một khái niệm.

Module đặt tên theo thứ nó chứa, không phải `utils`/`common` (GLOSSARY.md §1.5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Kho dữ liệu của launcher tiền nhiệm, dùng làm nguồn chỉ mục thật để đo. Chỉ đọc.
DEFAULT_ASSETS_DIR = Path.home() / ".nostalgia-launcher" / "assets"
DEFAULT_INDEX_ID = "5"  # chỉ mục của Minecraft 1.20.1

# Hai ngưỡng tách ba dải kích thước. Khoảng 16-64 KB không bị bỏ qua: đó là dải đông nhất
# theo số file, nên ước tính thời gian cài mà thiếu nó là ngoại suy chứ không phải đo.
SMALL_LIMIT = 16 * 1024
LARGE_LIMIT = 64 * 1024

BANDS: dict[str, tuple[int, int]] = {
    "nhỏ (<16 KB)": (0, SMALL_LIMIT),
    "vừa (16-64 KB)": (SMALL_LIMIT, LARGE_LIMIT),
    "lớn (>=64 KB)": (LARGE_LIMIT, 1 << 40),
}


@dataclass(frozen=True, slots=True)
class AssetObject:
    """Một object asset: hash sha1 và kích thước theo chỉ mục."""

    asset_hash: str
    size: int

    @property
    def object_path(self) -> Path:
        """Đường dẫn tương đối trong `objects/`: hai ký tự đầu của hash làm thư mục."""
        return Path(self.asset_hash[:2]) / self.asset_hash


def index_path_for(assets_dir: Path, index_id: str) -> Path:
    return assets_dir / "indexes" / f"{index_id}.json"


def load_objects(index_path: Path) -> tuple[list[AssetObject], int]:
    """Trả về (danh sách hash duy nhất, số mục thô trong chỉ mục).

    Chỉ mục liệt kê theo *tên file trong game*, nên nhiều tên có thể trỏ cùng một hash.
    Dedupe không chỉ để tiết kiệm: không dedupe thì hai luồng sẽ cùng ghi vào một đích.
    """
    objects = json.loads(index_path.read_text(encoding="utf-8"))["objects"]
    by_hash = {asset_object["hash"]: asset_object["size"] for asset_object in objects.values()}
    objects = [AssetObject(asset_hash, size) for asset_hash, size in sorted(by_hash.items())]
    return objects, len(objects)


def in_band(objects: list[AssetObject], band: str) -> list[AssetObject]:
    low, high = BANDS[band]
    return [asset_object for asset_object in objects if low <= asset_object.size < high]


def total_bytes(objects: list[AssetObject]) -> int:
    return sum(asset_object.size for asset_object in objects)
