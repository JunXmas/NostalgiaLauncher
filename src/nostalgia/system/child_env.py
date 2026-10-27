"""Môi trường cho tiến trình con của launcher đóng gói (PyInstaller)."""

from __future__ import annotations

import os

# PyInstaller trỏ các biến này vào thư mục thư viện riêng của launcher (glib, Qt…). Tiến trình
# con nào kế thừa chúng sẽ nạp nhầm thư viện đó: updater mới trỏ vào thư mục bản cũ đã bị xoá,
# game gọi gdbus thì chết "undefined symbol" (lời nhạc Nos Client tắt im lặng).
_LIBRARY_PATH_VARIABLES = ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH")


def clean_child_env() -> dict[str, str]:
    """Bản sao ``os.environ`` đã trả các biến đường dẫn thư viện về giá trị gốc của người dùng.

    PyInstaller cất giá trị gốc vào ``<biến>_ORIG``; có thì khôi phục, không có thì xoá hẳn.
    """
    env = os.environ.copy()
    for variable in _LIBRARY_PATH_VARIABLES:
        original = env.pop(variable + "_ORIG", None)
        if original is not None:
            env[variable] = original
        else:
            env.pop(variable, None)
    return env
