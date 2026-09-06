"""Mọi địa chỉ máy chủ, gom một chỗ.

Rải URL khắp nơi là cách chắc chắn để một ngày nào đó có hai địa chỉ khác nhau cho cùng một
thứ. Mojang đã đổi host manifest từ `launchermeta` sang `piston-meta`; cả hai còn sống,
nhưng chỉ nên có một chỗ để sửa.
"""

from __future__ import annotations

from dataclasses import dataclass

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# Danh mục bản Java. Đoạn băm trong đường dẫn là của chính danh mục, không phải của phiên
# bản game — Mojang đổi nó khi phát hành bản Java mới, và trình khởi động chính thức cũng
# ghi cứng đúng đường dẫn này.
JAVA_RUNTIME_MANIFEST_URL = (
    "https://piston-meta.mojang.com/v1/products/java-runtime/"
    "2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"
)

# Object asset nằm trên một host khác hẳn manifest, và chỉ mục KHÔNG khai URL — địa chỉ được
# suy ra từ chính hash. Vì thế nó phải nằm ở đây chứ không nằm cạnh chỗ suy ra.
ASSET_OBJECT_BASE_URL = "https://resources.download.minecraft.net"

# Meta của Fabric: một request trả về đúng file version JSON có `inheritsFrom`, phần còn lại
# đi qua kho `repo/` và bộ cài `install/` y như một bản Mojang.
FABRIC_META_URL = "https://meta.fabricmc.net/v2"

# Modrinth: nguồn mod / gói tài nguyên / shader. Không cần khoá API; chỉ cần User-Agent tử tế.
MODRINTH_API_URL = "https://api.modrinth.com/v2"


@dataclass(frozen=True, slots=True)
class Endpoints:
    """Các địa chỉ gốc, gói lại để truyền xuống một lần.

    Truyền ba tham số URL rời qua từng tầng là cách chắc chắn để một ngày có tầng quên
    chuyển tiếp một cái, và test "offline" lặng lẽ đi ra Internet thật. Đã xảy ra: URL asset
    từng bị ghi cứng, và một bộ test tưởng là offline mất 46 giây vì gọi ra Mojang.
    """

    version_manifest: str = VERSION_MANIFEST_URL
    java_catalog: str = JAVA_RUNTIME_MANIFEST_URL
    asset_objects: str = ASSET_OBJECT_BASE_URL
    fabric_meta: str = FABRIC_META_URL
    modrinth_api: str = MODRINTH_API_URL


DEFAULT_ENDPOINTS = Endpoints()
