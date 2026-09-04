"""Lập kế hoạch tải thư viện, gồm cả hai kiểu khai natives.

Đời ≤1.18 khai `natives: {linux: "natives-linux"}` cộng `downloads.classifiers`; đời ≥1.19
khai natives thành thư viện riêng lọc bằng `rules.os`. Một launcher phải chịu được cả hai
cùng lúc, vì người chơi vẫn chạy 1.8.9.

Một lượt duyệt duy nhất sinh cả hai danh sách. Bản trước có hai hàm duyệt cùng danh sách với
cùng bộ lọc, và chúng lệch nhau ở một điểm quan trọng: hàm tải gộp trùng theo đích còn hàm
natives thì không, nên hai thư viện khác toạ độ trỏ cùng một file sẽ bị xếp giải nén hai lần.
"""

from __future__ import annotations

from dataclasses import dataclass

from mccore.model.download import Artifact, DownloadTask
from mccore.storage.paths import DataPaths
from mccore.system.platform_info import Platform
from mccore.version.meta import Library, VersionMeta
from mccore.version.rules import rules_allow


@dataclass(frozen=True, slots=True)
class LibraryPlan:
    """Kết quả một lượt duyệt: tải những gì, và trong đó cái nào còn phải giải nén.

    `natives_to_extract` luôn là tập con của `downloads`, và cả hai đều đã gộp trùng theo
    đích — hai luồng cùng ghi một file, hay giải nén một file hai lần, đều là lỗi thật.
    """

    downloads: tuple[DownloadTask, ...]
    natives_to_extract: tuple[DownloadTask, ...]


def plan_libraries(version_meta: VersionMeta, platform: Platform, paths: DataPaths) -> LibraryPlan:
    """Mọi thư viện cần cho nền tảng này, tách sẵn phần cần giải nén."""
    downloads: list[DownloadTask] = []
    natives_to_extract: list[DownloadTask] = []
    seen: set[str] = set()

    for library in version_meta.libraries:
        if not rules_allow(library.rules, platform):
            continue
        needs_extracting = library.is_native_bundle or library.is_natives_jar
        for artifact in _artifacts_for(library, platform):
            if artifact.relative_path in seen:
                continue
            seen.add(artifact.relative_path)
            task = artifact.to_task(paths.libraries_dir)
            downloads.append(task)
            if needs_extracting:
                natives_to_extract.append(task)

    return LibraryPlan(downloads=tuple(downloads), natives_to_extract=tuple(natives_to_extract))


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
