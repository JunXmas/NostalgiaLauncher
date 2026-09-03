"""Mọi địa chỉ máy chủ, gom một chỗ.

Rải URL khắp nơi là cách chắc chắn để một ngày nào đó có hai địa chỉ khác nhau cho cùng một
thứ. Mojang đã đổi host manifest từ `launchermeta` sang `piston-meta`; cả hai còn sống,
nhưng chỉ nên có một chỗ để sửa.
"""

from __future__ import annotations

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
