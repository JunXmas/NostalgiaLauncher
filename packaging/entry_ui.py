"""Điểm vào cho gói PyInstaller: chỉ gọi `nostalgia.ui.app.main`.

PyInstaller cần một file script làm gốc; giữ nó mỏng để mọi logic vẫn nằm trong gói và được
test như khi chạy từ mã nguồn.
"""

from __future__ import annotations

import sys

from nostalgia.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
