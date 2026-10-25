"""Sửa tại chỗ, miễn phí: biến lỗi đọc được trong log/metadata thành việc launcher tự làm được.

Phương án Plus chỉ biết thêm hoặc tắt jar, nên ca hay gặp nhất ngoài đời — "mod cần
fabricloader >=0.19.5, đang có 0.19.3" — luôn ra "chưa giải được". Ở đây ba loại hành động:

- `loader`: nâng loader lên bản thoả yêu cầu (cài loader + đổi version_id của bản chơi).
- `disable`: tắt đúng jar bị log chỉ đích danh (mixin hỏng, jar hỏng không đọc được).
- `dependency`: cài phụ thuộc còn thiếu theo mã mod (tra Modrinth).
"""

from __future__ import annotations

from dataclasses import dataclass

from nostalgia.modcheck.archive import BROKEN_JAR
from nostalgia.modcheck.model import ModScan
from nostalgia.modcheck.predicate import matches
from nostalgia.modloader.model import loader_mod_id


@dataclass(frozen=True, slots=True)
class LocalFix:
    fix_kind: str  # "loader" | "disable" | "dependency"
    target: str  # loader: ràng buộc phiên bản; disable: tên file; dependency: mã mod
    reason: str


def suggest_local_fixes(scan: ModScan) -> tuple[LocalFix, ...]:
    fixes: dict[tuple[str, str], LocalFix] = {}
    loader_id = loader_mod_id(scan.loader_kind)
    installed = {
        descriptor.mod_id: archive.file_name
        for archive in scan.archives
        for descriptor in archive.descriptors
    }
    for diagnostic in scan.diagnostics:
        if diagnostic.code == "dependency" and diagnostic.dependency_id == loader_id:
            wanted = " ".join(diagnostic.predicates) or "mới nhất"
            fixes[("loader", wanted)] = LocalFix(
                "loader",
                wanted,
                f"{diagnostic.mod_id} cần {loader_id} {wanted}, bản chơi đang có "
                f"{scan.loader_version}.",
            )
        elif diagnostic.code == "dependency" and diagnostic.dependency_id not in installed:
            if diagnostic.dependency_id in ("minecraft", "java"):
                continue  # đổi Minecraft/Java không phải việc "sửa mod"
            fixes[("dependency", diagnostic.dependency_id)] = LocalFix(
                "dependency",
                diagnostic.dependency_id,
                f"{diagnostic.mod_id} cần {diagnostic.dependency_id}, chưa cài.",
            )
        elif diagnostic.code == "runtime" and diagnostic.mod_id in installed:
            file_name = installed[diagnostic.mod_id]
            fixes[("disable", file_name)] = LocalFix(
                "disable", file_name, f"Log ghi {diagnostic.mod_id} làm game lỗi khi nạp."
            )
    for archive in scan.archives:
        if archive.problem.startswith(BROKEN_JAR):  # zip hỏng thật; metadata lạ thì để yên
            fixes[("disable", archive.file_name)] = LocalFix(
                "disable", archive.file_name, archive.problem
            )
    return tuple(fixes.values())


def pick_loader_version(available: tuple[str, ...], predicate: str) -> str:
    """Bản loader mới nhất trong `available` (mới đứng đầu) thoả ràng buộc; rỗng nếu không có."""
    for loader_version in available:
        if predicate == "mới nhất" or matches(loader_version, predicate):
            return loader_version
    return ""
