"""platform_info: nhận diện máy, và cho phép giả lập máy khác để kiểm."""

from __future__ import annotations

import sys

import pytest

from nostalgia.errors import UnsupportedPlatformError
from nostalgia.system.platform_info import Platform, classpath_separator, current_platform


def test_current_platform_uses_mojang_vocabulary() -> None:
    platform = current_platform()
    assert platform.os_name in {"linux", "osx", "windows"}
    assert platform.os_arch in {"x64", "x86", "arm64", "arm32"}
    assert platform.os_version


@pytest.mark.parametrize(("os_name", "expected"), [("windows", ";"), ("linux", ":"), ("osx", ":")])
def test_classpath_separator(os_name: str, expected: str) -> None:
    assert classpath_separator(os_name) == expected


def test_platform_can_be_faked_for_other_operating_systems() -> None:
    """Cả kho phụ thuộc vào điều này: kiểm hành vi Windows khi đang ngồi trên Linux."""
    windows = Platform(os_name="windows", os_arch="x64", os_version="10")
    assert classpath_separator(windows.os_name) == ";"


def test_unsupported_platform_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hệ điều hành lạ phải hỏng ngay với tên thật trong thông điệp.

    Nếu trả về nguyên `sys.platform`, `rules` của Mojang không khớp gì, MỌI library bị lọc
    sạch, và người dùng nhận một lỗi "thiếu file" không gợi ra nguyên nhân.
    """
    monkeypatch.setattr(sys, "platform", "freebsd14")
    with pytest.raises(UnsupportedPlatformError, match="freebsd14"):
        current_platform()
