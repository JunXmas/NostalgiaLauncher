"""Chỉ mục asset: bảng tên-file-trong-game ứng với object trên CDN.

Nhiều tên có thể trỏ **cùng một** object. Với đời cũ thì tỉ lệ trùng rất cao — chỉ mục
`legacy` của 1.6.4 có 1120 mục nhưng chỉ 596 hash duy nhất, tức không gộp là tải thừa 47%.
Quan trọng hơn tiết kiệm: hai luồng cùng ghi một file đích là điều kiện đua thật sự.

Thuần: chỉ phân tích, không chạm đĩa. Đường dẫn lưu object do `DataPaths` quyết định — một
chỗ duy nhất biết luật thư mục hai ký tự.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from mccore.model.json_value import JsonValue, as_integer, as_mapping, as_string


@dataclass(frozen=True, slots=True)
class AssetObject:
    """Một object trên CDN: hash sha1 và kích thước."""

    asset_hash: str
    size: int


@dataclass(frozen=True, slots=True)
class AssetIndex:
    """Chỉ mục đã phân tích, cùng hai cờ bố trí của đời cũ.

    - `is_virtual` (đời 1.6): game đọc asset theo TÊN, nên phải dựng một cây tên thật.
    - `map_to_resources` (đời ≤1.5): cây đó nằm trong thư mục game, không nằm trong kho.

    Hai cờ không bao giờ cùng bật; đã kiểm trên chỉ mục thật của 1.5.2 và 1.6.4.
    """

    objects_by_name: Mapping[str, AssetObject]
    is_virtual: bool = False
    map_to_resources: bool = False

    @property
    def needs_name_tree(self) -> bool:
        """Đời cũ cần một cây theo tên; đời mới đọc thẳng từ kho object."""
        return self.is_virtual or self.map_to_resources

    def unique_objects(self) -> tuple[AssetObject, ...]:
        """Mỗi hash đúng một lần, giữ thứ tự xuất hiện đầu tiên."""
        seen: set[str] = set()
        unique: list[AssetObject] = []
        for asset_object in self.objects_by_name.values():
            if asset_object.asset_hash in seen:
                continue
            seen.add(asset_object.asset_hash)
            unique.append(asset_object)
        return tuple(unique)


def parse_asset_index(document: JsonValue) -> AssetIndex:
    """Phân tích chỉ mục. Mục thiếu `hash` hoặc `size` bị bỏ qua thay vì làm hỏng cả chỉ mục."""
    fields = as_mapping(document)
    objects_by_name: dict[str, AssetObject] = {}
    for name, raw in as_mapping(fields.get("objects")).items():
        entry_fields = as_mapping(raw)
        asset_hash = as_string(entry_fields.get("hash"))
        size = as_integer(entry_fields.get("size"))
        if asset_hash is None or size is None:
            continue
        objects_by_name[name] = AssetObject(asset_hash=asset_hash, size=size)
    return AssetIndex(
        objects_by_name=objects_by_name,
        is_virtual=fields.get("virtual") is True,
        map_to_resources=fields.get("map_to_resources") is True,
    )
