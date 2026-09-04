"""Lập kế hoạch tải thư viện, gồm cả hai kiểu khai natives.

Đời ≤1.18 khai `natives: {linux: "natives-linux"}` cộng `downloads.classifiers`; đời ≥1.19
khai natives thành thư viện riêng lọc bằng `rules.os`. Một launcher phải chịu được cả hai
cùng lúc, vì người chơi vẫn chạy 1.8.9.
"""

from __future__ import annotations

from mccore.model.download import Artifact, DownloadTask
from mccore.storage.paths import DataPaths
from mccore.system.platform_info import Platform
from mccore.version.meta import Library, VersionMeta
from mccore.version.rules import rules_allow


def plan_library_tasks(
    version_meta: VersionMeta, platform: Platform, paths: DataPaths
) -> list[DownloadTask]:
    """Mọi thư viện cần cho nền tảng này, đã gộp trùng theo đích.

    Gộp theo ĐÍCH chứ không theo toạ độ: hai mục khác toạ độ vẫn có thể trỏ cùng một file,
    và hai luồng cùng ghi một đích là điều kiện đua thật sự.
    """
    tasks: list[DownloadTask] = []
    seen: set[str] = set()
    for library in version_meta.libraries:
        if not rules_allow(library.rules, platform):
            continue
        for artifact in _artifacts_for(library, platform):
            if artifact.relative_path in seen:
                continue
            seen.add(artifact.relative_path)
            tasks.append(artifact.to_task(paths.libraries_dir))
    return tasks


def plan_native_extractions(
    version_meta: VersionMeta, platform: Platform, paths: DataPaths
) -> list[DownloadTask]:
    """Chỉ những jar cần GIẢI NÉN vào thư mục natives, không phải mọi thư viện.

    Bước 7 sẽ giải nén đúng danh sách này. Tách ra ở đây vì chỉ tầng này biết cách chọn
    natives cho từng kiểu khai.
    """
    tasks: list[DownloadTask] = []
    for library in version_meta.libraries:
        if not rules_allow(library.rules, platform):
            continue
        if not (library.is_native_bundle or library.is_natives_jar):
            continue
        tasks.extend(
            artifact.to_task(paths.libraries_dir) for artifact in _artifacts_for(library, platform)
        )
    return tasks


def _artifacts_for(library: Library, platform: Platform) -> list[Artifact]:
    """File nào của thư viện này cần tải, theo kiểu khai natives của nó."""
    if library.is_native_bundle:
        classifier = library.natives_classifier_by_os.get(platform.os_name)
        if classifier is None:
            return []
        # `${arch}` trong classifier: Mojang dùng cho natives 32/64 bit của đời cũ.
        classifier = classifier.replace("${arch}", "64" if platform.os_arch == "x64" else "32")
        artifact = library.classifier_artifacts.get(classifier)
        return [artifact] if artifact is not None else []
    return [library.artifact] if library.artifact is not None else []
