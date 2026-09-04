"""Nhận diện hệ điều hành và kiến trúc, theo đúng từ vựng mà Mojang dùng.

Mojang khai `rules` trong version JSON bằng các tên `linux` / `osx` / `windows`, nên lõi
phải nói cùng thứ tiếng đó thay vì dùng tên của Python.

Điểm quan trọng về thiết kế: các hàm ở tầng trên **nhận `Platform` làm đối số**, không tự
hỏi máy đang chạy là gì. Nhờ vậy có thể kiểm hành vi trên Windows và macOS ngay khi đang
ngồi trên Linux — chỉ cần dựng một `Platform` khác rồi truyền vào.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from nostalgia.errors import UnsupportedPlatformError

# Tên hệ điều hành theo cách Mojang gọi, ánh xạ từ tiền tố của `sys.platform`.
MOJANG_OS_NAMES = {"linux": "linux", "darwin": "osx", "win32": "windows", "cygwin": "windows"}

# Tên kiến trúc theo cách Mojang gọi trong `rules` và trong manifest JRE.
MOJANG_ARCH_NAMES = {
    "x86_64": "x64",
    "amd64": "x64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv7l": "arm32",
    "i386": "x86",
    "i686": "x86",
    "x86": "x86",
}

CLASSPATH_SEPARATORS = {"windows": ";", "linux": ":", "osx": ":"}


@dataclass(frozen=True, slots=True)
class Platform:
    """Nền tảng đang chạy, hoặc một nền tảng giả lập để kiểm."""

    os_name: str
    os_arch: str
    os_version: str


def current_platform() -> Platform:
    """Nhận diện máy đang chạy.

    `platform` được nạp lười vì nó tốn khoảng 9 ms — đáng kể so với ngân sách khởi động, và
    những lệnh chỉ in trợ giúp thì không cần biết máy là gì.

    Ném `UnsupportedPlatformError` nếu máy không phải linux/osx/windows.
    """
    # Nạp lười có chủ ý — xem docstring. `sys` thì luôn có sẵn nên nạp ở đầu file.
    import platform

    os_name = next(
        (name for prefix, name in MOJANG_OS_NAMES.items() if sys.platform.startswith(prefix)),
        None,
    )
    if os_name is None:
        # Hỏng ngay ở đây, với tên hệ điều hành thật trong thông điệp. Nếu trả về nguyên
        # `sys.platform`, `rules` của Mojang sẽ không khớp gì, MỌI library bị lọc sạch, và
        # người dùng nhận một lỗi "thiếu file" hoàn toàn không gợi ra nguyên nhân.
        message = (
            f"hệ điều hành không được hỗ trợ: {sys.platform!r}. "
            f"Mojang chỉ phát hành cho {', '.join(sorted(set(MOJANG_OS_NAMES.values())))}."
        )
        raise UnsupportedPlatformError(message)
    machine = platform.machine().lower()
    return Platform(
        os_name=os_name,
        os_arch=MOJANG_ARCH_NAMES.get(machine, machine),
        os_version=platform.release(),
    )


def classpath_separator(os_name: str) -> str:
    """Dấu ngăn cách classpath của java: `;` trên Windows, `:` ở nơi khác."""
    return CLASSPATH_SEPARATORS.get(os_name, ":")
