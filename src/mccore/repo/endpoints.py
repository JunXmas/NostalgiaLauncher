"""Mọi địa chỉ máy chủ, gom một chỗ.

Rải URL khắp nơi là cách chắc chắn để một ngày nào đó có hai địa chỉ khác nhau cho cùng một
thứ. Mojang đã đổi host manifest từ `launchermeta` sang `piston-meta`; cả hai còn sống,
nhưng chỉ nên có một chỗ để sửa.
"""

from __future__ import annotations

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# Danh mục bản Java. Đoạn băm trong đường dẫn là của chính danh mục, không phải của phiên
# bản game — Mojang đổi nó khi phát hành bản Java mới, và trình khởi động chính thức cũng
# ghi cứng đúng đường dẫn này.
JAVA_RUNTIME_MANIFEST_URL = (
    "https://piston-meta.mojang.com/v1/products/java-runtime/"
    "2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"
)
