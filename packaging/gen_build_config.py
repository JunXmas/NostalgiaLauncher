"""Sinh nostalgia/_build_config.py để nhúng client ID vào bản đóng gói.

Client ID đọc từ biến môi trường (CI đặt qua secret MC_CLIENT_ID). Bản mã nguồn
không chạy script này nên trong kho không có ID nào — người fork tự cấu hình.
Chạy trước pyinstaller; nếu biến rỗng thì sinh file trống, build vẫn hợp lệ.
"""

from __future__ import annotations

import os
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "nostalgia" / "_build_config.py"

ENV_VARS = {
    "microsoft": "MC_CLIENT_ID",
}


def main() -> None:
    ids = {}
    for name, env_var in ENV_VARS.items():
        value = os.environ.get(env_var, "").strip()
        if value:
            ids[name] = value
    TARGET.write_text(
        "# Sinh tự động lúc build bởi packaging/gen_build_config.py — không commit.\n"
        f"CLIENT_IDS = {ids!r}\n"
    )
    print(f"wrote {TARGET} with keys {list(ids)}")


if __name__ == "__main__":
    main()
