#!/usr/bin/env python3
"""Chạy scanner nhập bản chơi trên máy thật, in ra thấy gì.

Vì sao cần: test dựng `HOME` giả — đúng, test không được đụng config thật. Nhưng nghĩa là
test chỉ nghiệm lại đúng giả định của người viết. Lỗi Flatpak sống sót vì thế: cây thư mục
giả dựng ở `~/.local/share/`, scanner tìm ra, xanh — trong khi máy thật để bản chơi ở
`~/.var/app/<app-id>/data/`. Script này đọc `HOME` thật, chỉ đọc, không ghi gì.

    ./scripts/quet-may-that.py
"""

from __future__ import annotations

import sys

from nostalgia.importing.launchers import find_all

found = find_all()
for f in found:
    print(f"{f.launcher:15} {f.instance_name:25} {f.game_version:10} {f.loader_kind:9}")
    print(f"{'':15} {f.game_dir}")
print(f"\n{len(found)} bản chơi.")
if not found:
    print("Không thấy gì. Nếu máy đang có launcher khác thì đây là lỗi, không phải 'máy sạch'.")
    sys.exit(1)
