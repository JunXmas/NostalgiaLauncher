"""Chọn bản Java: theo component chứ không theo major, và đường lùi cho ARM."""

from __future__ import annotations

from pathlib import Path

from nostalgia.java.component import (
    DEFAULT_JAVA_COMPONENT,
    resolve_java_binary,
    resolve_java_component,
    resolve_runtime_os_keys,
)
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import JavaRuntimeRef, VersionMeta


def make_version_meta(java_runtime: JavaRuntimeRef | None) -> VersionMeta:
    return VersionMeta(
        version_id="test", main_class="net.minecraft.client.main.Main", java_runtime=java_runtime
    )


def test_component_comes_from_the_version_not_from_the_major_number() -> None:
    """`gamma` và `beta` đều là Java 17; chỉ tên component mới phân biệt được hai bản."""
    version_meta = make_version_meta(
        JavaRuntimeRef(java_component="java-runtime-gamma", major_version=17)
    )
    assert resolve_java_component(version_meta) == "java-runtime-gamma"


def test_versions_without_a_declaration_get_the_legacy_runtime() -> None:
    """Mọi bản trước 1.17 không khai `javaVersion` — mặc định phải là bản Java 8."""
    assert resolve_java_component(make_version_meta(None)) == DEFAULT_JAVA_COMPONENT
    assert DEFAULT_JAVA_COMPONENT == "jre-legacy"


def test_apple_silicon_falls_back_to_the_intel_build() -> None:
    """`mac-os-arm64` không có `jre-legacy`, nên phải còn đường lùi sang `mac-os`."""
    keys = resolve_runtime_os_keys(Platform(os_name="osx", os_arch="arm64", os_version="14.0"))
    assert keys == ("mac-os-arm64", "mac-os")
    assert len(set(keys)) == 2, "khoá ưu tiên phải khác đường lùi, nếu không lùi cũng vô ích"


def test_thirty_two_bit_linux_has_no_fallback() -> None:
    """Máy 32 bit không chạy được mã 64 bit: chỉ một khoá, không đường lùi."""
    keys = resolve_runtime_os_keys(Platform(os_name="linux", os_arch="x86", os_version="6.0"))
    assert keys == ("linux-i386",)


def test_unknown_platform_yields_no_keys() -> None:
    unknown = Platform(os_name="freebsd", os_arch="x64", os_version="14")
    assert resolve_runtime_os_keys(unknown) == ()


def test_java_binary_location_differs_per_operating_system() -> None:
    """macOS chôn `java` trong một bundle; đoán sai là báo 'không tìm thấy Java'."""
    runtime_root = Path("/kho/runtime/jre-legacy/mac-os")
    assert (
        resolve_java_binary(runtime_root, "osx")
        == runtime_root / "jre.bundle/Contents/Home/bin/java"
    )
    assert resolve_java_binary(runtime_root, "windows").name == "java.exe"
    assert resolve_java_binary(runtime_root, "linux") == runtime_root / "bin" / "java"
