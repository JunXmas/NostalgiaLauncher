"""Chọn bản Java nào, và tìm nó ở đâu. THUẦN: không mạng, không đọc/ghi file.

Phải tra theo `javaVersion.component`, **không** theo `majorVersion`: Mojang phát hành
nhiều bản cùng major (`java-runtime-gamma` và `java-runtime-beta` đều là 17) và chỉ bản
được chỉ định mới được kiểm với phiên bản game đó.

Điểm dễ sai nhất là ARM. Đo trên manifest thật: `mac-os-arm64` và `windows-arm64` **không
có** `jre-legacy`, nên máy Apple Silicon không chạy được 1.8.9 nếu không lùi về bản x64
(chạy qua Rosetta). `linux-i386` thì chỉ có `jre-legacy` và không có đường lùi — máy 32 bit
không chạy được mã 64 bit.
"""

from __future__ import annotations

from pathlib import Path

from mccore.system.platform_info import Platform
from mccore.version.meta import VersionMeta

# Bản mặc định cho phiên bản không khai `javaVersion` — mọi bản trước 1.17 đều vậy.
DEFAULT_JAVA_COMPONENT = "jre-legacy"

# Khoá hệ điều hành trong manifest, theo thứ tự ƯU TIÊN rồi mới tới đường lùi.
RUNTIME_OS_KEYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("linux", "x64"): ("linux",),
    ("linux", "x86"): ("linux-i386",),
    ("linux", "arm64"): ("linux",),
    ("osx", "x64"): ("mac-os",),
    ("osx", "arm64"): ("mac-os-arm64", "mac-os"),
    ("windows", "x64"): ("windows-x64",),
    ("windows", "x86"): ("windows-x86",),
    ("windows", "arm64"): ("windows-arm64", "windows-x64"),
}

# Nơi `bin/java` nằm bên trong bản đã bung. macOS gói nó trong một bundle.
JAVA_BINARY_PATHS = {
    "linux": "bin/java",
    "osx": "jre.bundle/Contents/Home/bin/java",
    "windows": "bin/java.exe",
}


def resolve_java_component(version_meta: VersionMeta) -> str:
    """Bản Java mà phiên bản này cần. Không khai thì là `jre-legacy`."""
    if version_meta.java_runtime is None:
        return DEFAULT_JAVA_COMPONENT
    return version_meta.java_runtime.java_component


def resolve_runtime_os_keys(platform: Platform) -> tuple[str, ...]:
    """Khoá ưu tiên rồi tới các đường lùi. Rỗng nghĩa là nền tảng không được hỗ trợ."""
    return RUNTIME_OS_KEYS.get((platform.os_name, platform.os_arch), ())


def resolve_java_binary(runtime_root: Path, os_name: str) -> Path:
    """Đường dẫn `java` bên trong một bản đã bung."""
    return runtime_root / JAVA_BINARY_PATHS.get(os_name, "bin/java")
