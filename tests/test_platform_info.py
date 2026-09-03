"""platform_info: nhận diện máy, và cho phép giả lập máy khác để kiểm."""

from __future__ import annotations

import pytest

from mccore.platform_info import Platform, classpath_separator, current_platform


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
