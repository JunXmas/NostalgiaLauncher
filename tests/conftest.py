"""Cấu hình chung cho test.

Luật số một của kho: đường dẫn không bao giờ được dẫn xuất từ thư mục home. Một fixture chỉ
*chuyển hướng* home sang thư mục tạm là chưa đủ — code vi phạm luật vẫn chạy trơn tru, ghi
vào home giả, và không ai biết. Lưới ở đây vì thế làm hai việc:

1. Đặt lại mọi biến môi trường đường dẫn về thư mục tạm (phòng thân, và cần cho Windows).
2. **Cấm** `Path.home()` và `os.path.expanduser` — gọi tới là rớt ngay tại dòng gây lỗi.

Test nào thật sự cần home thì đánh `@pytest.mark.allow_home`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Mọi biến môi trường có thể dẫn code về dữ liệu thật của người dùng.
PATH_ENV_VARS = (
    "HOME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
)


@pytest.fixture(autouse=True)
def isolated_home(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Path:
    """Ép mọi đường dẫn vào thư mục tạm, và cấm mọi lối đi vòng qua home.

    Dùng `tmp_path_factory` chứ không phải `tmp_path`: nếu tạo home giả ngay trong `tmp_path`
    thì mọi test liệt kê nội dung `tmp_path` sẽ thấy thêm một thư mục lạ. Đã trả giá một lần.
    """
    home = tmp_path_factory.mktemp("home")

    for name in PATH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # Xoá cả biến của chính dự án, kể cả biến thêm về sau.
    for name in [n for n in os.environ if n.startswith("MCCORE_")]:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows không bao giờ tra HOME
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("MCCORE_DATA_DIR", str(home / "data"))

    if request.node.get_closest_marker("allow_home") is None:
        message = (
            "Code trong mccore không được gọi Path.home() hay expanduser(). "
            "Đường dẫn phải đến từ DataPaths được truyền vào — xem GLOSSARY.md §1.4."
        )

        def forbidden(*_args: object, **_kwargs: object) -> Path:
            raise AssertionError(message)

        monkeypatch.setattr(Path, "home", staticmethod(forbidden))
        monkeypatch.setattr(os.path, "expanduser", forbidden)

    return home
